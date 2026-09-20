import math
from pathlib import Path
import pytest
from cvsubstrate.contracts.models import DetectionPrediction,Category,Box,GenerationMetadata
from cvsubstrate.contracts.research import (TilingPolicy,TinyEvaluationPolicy,SidecarMapping,FieldMapping,
    SyntheticRecord,Quantity,OrientedPrediction,GeoReference)
from cvsubstrate.data.tiled import axis_offsets,plan_tiles,materialize_tiles,merge_tile_predictions
from cvsubstrate.data.synthetic import map_sidecar,pointer,MISSING
from cvsubstrate.data.dota import import_dota,parse_dota_labels,export_task1,validate_oriented_dataset
from cvsubstrate.evaluation.tiny import tiny_diagnostics,size_bin
from cvsubstrate.evaluation.oriented import oriented_diagnostics
from cvsubstrate.evaluation.prediction_parity import audit_predictions
from cvsubstrate.analysis.domain import describe_dataset,compare_domains
from cvsubstrate.provenance.io import digest,read_json,write_json,file_digest
from cvsubstrate.provenance.artifact_set import verify_directory
from cvsubstrate.contracts.migrations import migrate_generation
from cvsubstrate.errors import CVRSError


def predrows(m,split='dev',perfect=False):
    samples={s.id:s for s in m.samples};out=[]
    for sid in m.splits[split].sample_ids:
        s=samples[sid];boxes=[b for b in s.boxes if not b.iscrowd and not b.ignore] if perfect else []
        out.append(DetectionPrediction(sample_id=sid,width=s.width,height=s.height,boxes=[b.xyxy for b in boxes],
            scores=[.9]*len(boxes),category_ids=[b.category_id for b in boxes]))
    return out


@pytest.mark.parametrize('n,tile,overlap',[(10,20,2),(20,20,0),(21,20,5),(100,32,5),(17,8,7)])
def test_tile_every_source_pixel_covered(n,tile,overlap):
    offsets=axis_offsets(n,tile,overlap)
    assert offsets[0]==0 and offsets[-1]+tile>=n
    assert all(any(x<=i<min(n,x+tile) for x in offsets) for i in range(n))
    assert len(offsets)==len(set(offsets))


@pytest.mark.parametrize('args',[(0,10,0),(10,10,10),(10,10,-1)])
def test_axis_invalid(args):
    with pytest.raises(ValueError):axis_offsets(*args)


def test_tile_merge_duplicate_identity_and_order(dataset,tmp_path):
    pytest.importorskip("PIL")
    m,root=dataset
    p=TilingPolicy(width=48,height=48,overlap_x=16,overlap_y=16)
    tm,plan=materialize_tiles(m,'dev',root,tmp_path/'tiles',p)
    assert len(tm.samples)==len(plan['tiles'])
    rows=[DetectionPrediction(sample_id=s.id,width=s.width,height=s.height,boxes=[],scores=[],category_ids=[]) for s in tm.samples]
    merged,audit=merge_tile_predictions(m,'dev',plan,list(reversed(rows)),p)
    assert len(merged)==len(m.splits['dev'].sample_ids)
    assert all(not x.boxes for x in merged)
    with pytest.raises(CVRSError):merge_tile_predictions(m,'dev',plan,rows[:-1],p)
    bad=dict(plan);bad['dataset_digest']='f'*64
    with pytest.raises(CVRSError):merge_tile_predictions(m,'dev',bad,rows,p)


def test_padding_predictions_not_counted_as_source(dataset,tmp_path):
    pytest.importorskip("PIL")
    m,root=dataset;p=TilingPolicy(width=128,height=128,overlap_x=0,overlap_y=0)
    tm,plan=materialize_tiles(m,'dev',root,tmp_path/'tile',p)
    rows=[DetectionPrediction(sample_id=s.id,width=128,height=128,boxes=[[120.,120.,125.,125.]],scores=[.9],category_ids=[m.categories[0].id]) for s in tm.samples]
    merged,audit=merge_tile_predictions(m,'dev',plan,rows,p)
    assert all(not x.boxes for x in merged)
    assert len(audit['events'])==len(rows)


def test_tiling_limits_before_allocating(dataset):
    m,_=dataset
    with pytest.raises(CVRSError):plan_tiles(m,'dev',TilingPolicy(max_source_pixels=1))
    with pytest.raises(CVRSError):plan_tiles(m,'dev',TilingPolicy(width=16,height=16,overlap_x=0,overlap_y=0,max_tiles=1))


@pytest.mark.parametrize('area,want',[(0.,'[0,16)'),(255.,'[0,16)'),(256.,'[16,32)'),(1024.,'[32,64)'),(4096.,'[64,inf)')])
def test_size_boundaries(area,want):assert size_bin(area,[0.,16.,32.,64.])==want


def test_perfect_and_empty_tiny_predictions(dataset):
    m,_=dataset;p=TinyEvaluationPolicy()
    result=tiny_diagnostics(m,'dev',predrows(m,perfect=True),p)
    assert result['aggregate']['fixed_threshold']['recall']==1.
    assert result['aggregate']['fixed_threshold']['false_positives']==0
    result=tiny_diagnostics(m,'dev',predrows(m),p)
    assert result['aggregate']['fixed_threshold']['recall']==0.
    assert 'NOT_OFFICIAL_AP' in result['kind']


def test_tiny_score_ties_are_whole_groups(dataset):
    m,_=dataset;rows=predrows(m,perfect=True)
    r=rows[0]
    r.boxes.append([0.,0.,1.,1.]);r.scores.append(.9);r.category_ids.append(m.categories[0].id)
    value=tiny_diagnostics(m,'dev',rows,TinyEvaluationPolicy(fppi_budgets=[0.]))
    assert value['aggregate']['recall_at_fppi']['0.0']['true_positives']==0
    assert len(value['aggregate']['curve'])==2


def test_tiny_no_ground_truth_null_and_locked_refused(dataset):
    m,_=dataset
    for sample in m.samples:sample.boxes=[]
    report=tiny_diagnostics(m,'dev',predrows(m),TinyEvaluationPolicy())
    assert report['aggregate']['fixed_threshold']['recall'] is None
    m.splits['dev'].role='locked_test'
    with pytest.raises(CVRSError):tiny_diagnostics(m,'dev',predrows(m),TinyEvaluationPolicy())


def test_tiny_crowd_uses_prediction_area(dataset):
    m,_=dataset
    for sample in m.samples:sample.boxes=[]
    sid=m.splits['dev'].sample_ids[0];s=next(x for x in m.samples if x.id==sid)
    s.boxes=[Box(xyxy=[0.,0.,float(s.width),float(s.height)],category_id=m.categories[0].id,iscrowd=True)]
    rows=predrows(m);r=next(x for x in rows if x.sample_id==sid)
    rows[rows.index(r)]=DetectionPrediction(sample_id=sid,width=r.width,height=r.height,boxes=[[1.,1.,3.,3.]],scores=[.9],category_ids=[m.categories[0].id])
    report=tiny_diagnostics(m,'dev',rows,TinyEvaluationPolicy())
    assert report['aggregate']['fixed_threshold']['ignored_detections']==1
    assert report['aggregate']['fixed_threshold']['false_positives']==0


def test_domain_units_statuses_and_unknown_not_merged(dataset):
    m,_=dataset;sid=m.splits['dev'].sample_ids[0]
    rec=SyntheticRecord(sample_id=sid,generator='test',observed={'altitude':Quantity(status='simulator_reported',value=10.,unit='m'),'fog':Quantity(status='unknown')})
    report=describe_dataset(m,'dev',[rec])
    assert report['observations']['altitude|unit=m|status=simulator_reported']['mean']==10.
    assert report['unknown_observations']['fog']==1
    assert report['sidecar_coverage']['present']==1
    assert compare_domains(report,report)['taxonomy_counts_comparable'] is True
    second=dict(report);second['taxonomy']=[]
    assert compare_domains(report,second)['taxonomy_counts_comparable'] is False
    with pytest.raises(ValueError):describe_dataset(m,'dev',[rec,rec])


@pytest.mark.parametrize('raw,expected',[( {'a/b':{'~':4}},4)])
def test_json_pointer_escapes(raw,expected):assert pointer(raw,'/a~1b/~0')==expected


def test_pointer_invalid_and_missing():
    assert pointer({'a':[]},'/a/0') is MISSING
    with pytest.raises(ValueError):pointer({},'/a~2')
    with pytest.raises(ValueError):pointer({},'eval(x)')


def test_sidecar_unit_conversion_missing_and_identity():
    m=SidecarMapping(name='map',generator='user',fields=[FieldMapping(pointer='/cm',target='altitude',unit='m',scale=.01),FieldMapping(pointer='/missing',target='fog',unit='m')],identity_pointers={'seed':'/seed'})
    r=map_sidecar({'sample_id':'x','cm':12500.,'seed':7},m)
    assert r.observed['altitude'].value==125.
    assert r.observed['fog'].status=='unknown' and r.observed['fog'].value is None
    assert r.seed==7
    with pytest.raises(ValueError):map_sidecar({'sample_id':'x','cm':'bad'},m)
    m.fields[0].required=True
    with pytest.raises(CVRSError):map_sidecar({'sample_id':'x'},m)


def test_explicit_schema_migration_is_derived_not_mutation(tmp_path):
    old=GenerationMetadata(simulator='fixture',observed={'altitude':10.},units={'altitude':'m'})
    path=tmp_path/'source.json';write_json(path,old);before=file_digest(path)
    result=migrate_generation(path,tmp_path/'migrated',sample_id='x')
    assert file_digest(path)==before and result['source_mutated'] is False
    new=SyntheticRecord.model_validate(read_json(tmp_path/'migrated/record.json'))
    assert new.observed['altitude'].status=='declared'
    assert verify_directory(tmp_path/'migrated')['status']=='VERIFIED'
    write_json(tmp_path/'bad.json',{'schema_version':'99'})
    with pytest.raises(CVRSError):migrate_generation(tmp_path/'bad.json',tmp_path/'badout',sample_id='x')


def test_prediction_parity_declared_tolerances(dataset):
    m,_=dataset;a=predrows(m,perfect=True);b=[x.model_copy(deep=True) for x in a]
    assert audit_predictions(a,b)['status']=='PASS'
    b[0].scores[0]-=.01
    assert audit_predictions(a,b)['status']=='FAIL'
    assert audit_predictions(a,b,score_atol=.02)['status']=='PASS'
    with pytest.raises(ValueError):audit_predictions(a,b,box_atol=float('nan'))
    with pytest.raises(CVRSError):audit_predictions(a+a,b)


def test_dota_import_export_difficult_and_no_false_official_claim(tmp_path):
    from cvsubstrate.data.research_fixtures import generate_research_fixtures
    generate_research_fixtures(tmp_path/'demo');d=tmp_path/'demo'
    m=import_dota(d/'dota-images',d/'dota-labels',categories=[Category(id=1,name='small-vehicle')],name='test',version='fixture',role='dev',purpose='software_fixture')
    assert validate_oriented_dataset(m,d/'dota-images')['difficult']==1
    s=m.samples[0]
    rows=[OrientedPrediction(sample_id=s.id,polygons=[s.annotations[0].polygon],scores=[.9],category_ids=[1])]
    r=oriented_diagnostics(m,rows)
    assert r['recall']==1. and r['precision']==1.
    out=export_task1(m,rows,tmp_path/'export')
    assert out['official_evaluator_executed'] is False
    assert verify_directory(tmp_path/'export')['status']=='VERIFIED'
    assert (tmp_path/'export/Task1_small-vehicle.txt').read_text().split()[0]==s.id


def test_dota_parser_rejects_unknown_or_bad_difficulty(tmp_path):
    p=tmp_path/'x.txt'
    p.write_text('0 0 10 0 10 10 0 10 vehicle 9\n')
    with pytest.raises(ValueError):parse_dota_labels(p,{'vehicle':1})
    p.write_text('0 0 10 0 10 10 0 10 other 0\n')
    with pytest.raises(CVRSError):parse_dota_labels(p,{'vehicle':1})


def test_geotiff_actual_window_preserves_affine_and_nodata(tmp_path):
    pytest.importorskip('PIL')
    rasterio=pytest.importorskip('rasterio');np=pytest.importorskip('numpy')
    from rasterio.transform import Affine
    from PIL import Image
    from cvsubstrate.data.geotiff import inspect_geotiff,export_window
    path=tmp_path/'sensor.tif';values=np.full((3,20,30),100,dtype='uint16');values[:,5,4]=0
    with rasterio.open(path,'w',driver='GTiff',width=30,height=20,count=3,dtype='uint16',crs='EPSG:32637',transform=Affine(2.,.25,500000.,.1,-2.,2400000.),nodata=0) as ds:ds.write(values)
    r=export_window(path,tmp_path/'window',window=[3,4,8,7],bands=[3,2,1],value_range=[0.,200.])
    assert r['valid_pixels']==55
    assert r['output_reference']['affine'][2]==500007.
    assert r['output_reference']['affine'][5]==2399992.3
    im=np.asarray(Image.open(tmp_path/'window/image.png'));assert list(im[1,1])==[0,0,0]
    assert list(im[0,0])==[128,128,128]
    assert verify_directory(tmp_path/'window')['status']=='VERIFIED'
    with pytest.raises(ValueError):export_window(path,tmp_path/'bad',window=[25,0,8,4],bands=[1,2,3],value_range=[0.,200.])


def test_geotiff_raw_window_preserves_samples_dtype_bands_and_mask(tmp_path):
    rasterio=pytest.importorskip('rasterio');np=pytest.importorskip('numpy')
    from rasterio.transform import Affine
    from cvsubstrate.data.geotiff import export_raw_window
    path=tmp_path/'sensor.tif';values=np.arange(3*10*12,dtype='uint16').reshape(3,10,12);values[:,3,4]=0
    with rasterio.open(path,'w',driver='GTiff',width=12,height=10,count=3,dtype='uint16',crs='EPSG:32637',transform=Affine(2.,0.,500000.,0.,-2.,2400000.),nodata=0) as ds:ds.write(values)
    result=export_raw_window(path,tmp_path/'raw',window=[3,2,5,4],bands=[3,1])
    data=np.load(tmp_path/'raw/data.npy',allow_pickle=False);valid=np.load(tmp_path/'raw/valid_mask.npy',allow_pickle=False)
    assert data.dtype==np.uint16 and data.shape==(2,4,5)
    assert np.array_equal(data,values[[2,0],2:6,3:8])
    assert not valid[:,1,1].any()
    assert result['bands']==[3,1] and result['dtype']=='uint16'
    assert result['output_reference']['affine']==[2.,0.,500006.,0.,-2.,2399996.]
    assert result['conversion'].startswith('NONE')
    assert verify_directory(tmp_path/'raw')['status']=='VERIFIED'


def test_native_geotiff_window_artifact_preserves_tensor_semantics(tmp_path):
    np=pytest.importorskip('numpy')
    from cvsubstrate.data.geotiff import export_native_window_artifact
    source=GeoReference(crs='EPSG:32618',affine=[2.,0.,100.,0.,-3.,500.])
    output=GeoReference(crs='EPSG:32618',affine=[2.,0.,108.,0.,-3.,491.])
    values=np.arange(2*3*4,dtype='float32').reshape(2,3,4);values[:,1,2]=0
    result=export_native_window_artifact(values,tmp_path/'native',source_sha256='a'*64,
        source_reference=source,output_reference=output,window=[4,3,4,3],bands=[3,1],nodata=0.)
    restored=np.load(tmp_path/'native/data.npy',allow_pickle=False)
    valid=np.load(tmp_path/'native/valid_mask.npy',allow_pickle=False)
    assert restored.dtype==np.float32 and np.array_equal(restored,values)
    assert not valid[:,1,2].any()
    assert result['window']==[4,3,4,3] and result['bands']==[3,1]
    assert result['source_reference']==source.model_dump(mode='json')
    assert result['output_reference']==output.model_dump(mode='json')
    assert verify_directory(tmp_path/'native')['status']=='VERIFIED'


def test_nested_contract_canonicalization_preserves_json_identity():
    assert digest([Category(id=1,name='x')])==digest([Category(id=1,name='x').model_dump(mode='json')])


def test_density_and_border_recall_are_declared_diagnostics(dataset):
    m,_=dataset
    report=tiny_diagnostics(m,'dev',predrows(m,perfect=True),TinyEvaluationPolicy())
    assert sum(v['fixed_threshold']['images'] for v in report['density_slices'].values())==len(m.splits['dev'].sample_ids)
    for value in report['aggregate']['border_recall_at_fixed_threshold'].values():
        assert value['recall'] in (None,1.)
    with pytest.raises(ValueError):TinyEvaluationPolicy(density_edges=[1,5])
    with pytest.raises(ValueError):TinyEvaluationPolicy(border_distances_px=[-1.])


def test_selection_is_not_training_or_threshold_tuning(dataset,real_spec):
    from cvsubstrate.data.manifest import validate_experiment
    m,_=dataset;m.splits['dev'].role='selection';real_spec.dataset_sha256=digest(m)
    validate_experiment(real_spec,m)
    with pytest.raises(CVRSError):tiny_diagnostics(m,'dev',predrows(m),TinyEvaluationPolicy())
    real_spec.train_split='dev'
    with pytest.raises(CVRSError):validate_experiment(real_spec,m)


def test_derived_report_cannot_mutate_sealed_run(tmp_path):
    from cvsubstrate.provenance.bundle import RunBundle,verify_bundle
    from cvsubstrate.reporting.research import publish_report
    b=RunBundle(tmp_path,'a'*64,'b'*64);b.finish('SUCCEEDED')
    with pytest.raises(CVRSError):publish_report({'kind':'test'},b.path/'new-report')
    with pytest.raises(CVRSError):RunBundle(b.path/'nested','c'*64,'d'*64)
    assert verify_bundle(b.path)['status']=='VERIFIED'
