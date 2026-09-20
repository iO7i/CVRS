from pathlib import Path
import pytest
from cvsubstrate.heritage.importer import config_graph,import_project,import_predictions
from cvsubstrate.heritage.capsule import write_capsule
from cvsubstrate.heritage.catalogue import compatibility_matrix
from cvsubstrate.provenance.artifact_set import verify_directory
from cvsubstrate.provenance.io import write_jsonl,read_json,file_digest
from cvsubstrate.errors import CVRSError


def test_graph_preserves_relative_closure_without_execution(tmp_path):
    root=tmp_path/'source';(root/'configs').mkdir(parents=True)
    (root/'base.py').write_text('epochs=12\n')
    marker=tmp_path/'should_not_exist'
    config=root/'configs'/'model.py'
    config.write_text(f"_base_=['../base.py']\nmodel=dict(type='TOOD')\nopen({str(marker)!r},'w').write('bad')\n")
    graph=config_graph(config,root)
    assert len(graph['files'])==2 and not marker.exists()
    assert graph['unresolved'] and graph['executed'] is False
    report=import_project(config,root,tmp_path/'import',upstream='open-mmlab/mmdetection',revision='declared-not-resolved')
    assert report['execution_verified'] is False
    assert verify_directory(tmp_path/'import')['status']=='VERIFIED'
    ref=read_json(tmp_path/'import'/'reference.json');assert ref['trust_executable_config'] is False


def test_graph_rejects_cycle_and_escape(tmp_path):
    a=tmp_path/'a.py';b=tmp_path/'b.py'
    a.write_text("_base_='b.py'\n");b.write_text("_base_='a.py'\n")
    with pytest.raises(CVRSError,match='cyclic'):config_graph(a,tmp_path)
    a.write_text("_base_='../outside.py'\n")
    with pytest.raises(CVRSError,match='root'):config_graph(a,tmp_path)

@pytest.mark.parametrize('fmt',['mmdet2_bbox','mmdet3_instances'])
def test_safe_native_json_import(dataset,tmp_path,fmt):
    m,root=dataset;ids=m.splits['dev'].sample_ids
    rows=[]
    for sid in ids:
        row={'sample_id':sid}
        if fmt=='mmdet2_bbox':row['result']=[[[0.,0.,3.,3.,.9]]]
        else:row.update(boxes=[[0.,0.,3.,3.]],scores=[.9],labels=[0])
        rows.append(row)
    native=tmp_path/'native.jsonl';write_jsonl(native,rows)
    result=import_predictions(native,root/'dataset.json','dev',{'0':m.categories[0].id},tmp_path/'imported',native_format=fmt)
    assert result['native_detections']==len(ids) and result['native_execution_verified'] is False
    assert verify_directory(tmp_path/'imported')['status']=='VERIFIED'


def test_import_rejects_unmapped_and_noninjective(dataset,tmp_path):
    m,root=dataset
    rows=[{'sample_id':sid,'boxes':[[0.,0.,3.,3.]],'scores':[.9],'labels':[9]} for sid in m.splits['dev'].sample_ids]
    p=tmp_path/'p.jsonl';write_jsonl(p,rows)
    with pytest.raises(CVRSError,match='dropped'):
        import_predictions(p,root/'dataset.json','dev',{'0':m.categories[0].id},tmp_path/'out',native_format='mmdet3_instances')
    with pytest.raises(ValueError,match='noninjective'):
        import_predictions(p,root/'dataset.json','dev',{'0':m.categories[0].id,'1':m.categories[0].id},tmp_path/'out',native_format='mmdet3_instances')


def test_capsule_is_explicit_not_fake_certification(tmp_path):
    result=write_capsule(tmp_path/'capsule','3.11.9',{'torch':'2.1.2+cpu'})
    assert result['execution_verified'] is False
    assert (tmp_path/'capsule'/'Dockerfile.template').exists()
    assert not (tmp_path/'capsule'/'Dockerfile').exists()
    assert verify_directory(tmp_path/'capsule')['status']=='VERIFIED'
    with pytest.raises(ValueError):write_capsule(tmp_path/'bad','3.11',{})
    with pytest.raises(ValueError):write_capsule(tmp_path/'bad','3.11.9',{},base_image='python:latest')


def test_catalogue_reports_metadata_not_execution():
    path=Path(__file__).parents[1]/'heritage/catalogue.json'
    report=compatibility_matrix(path)
    assert len(report['rows'])==7
    assert all(r['inference']=='NOT_RUN' for r in report['rows'])
