"""Product workflow tests. Native SDKs are not impersonated as real executions."""
from pathlib import Path
import json
import sys
import zipfile
import hashlib
import base64
import pytest
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import read_json,write_json,file_digest,digest
from cvsubstrate.product.contracts import ManagedEnvironmentSpec
from cvsubstrate.product.environments import EnvironmentManager,probe,observation_diff
from cvsubstrate.product.interchange import (RichInterchange,RichFrame,RichObject,to_fiftyone_payload,from_fiftyone_payload,
                                            to_supervision_payload,from_supervision_payload,audit_roundtrip)
from cvsubstrate.product.methodology import review_methodology


def wheel_fixture(root):
    """A local owned pure-Python wheel for actual offline pip installation."""
    path=root/'cvrs_fixture_package-0.0.1-py3-none-any.whl';dist='cvrs_fixture_package-0.0.1.dist-info'
    records={'cvrs_fixture_package.py':b'VALUE = 17\n',dist+'/METADATA':b'Metadata-Version: 2.1\nName: cvrs-fixture-package\nVersion: 0.0.1\n',
             dist+'/WHEEL':b'Wheel-Version: 1.0\nGenerator: cvrs-tests\nRoot-Is-Purelib: true\nTag: py3-none-any\n'}
    rows=[]
    for name,data in records.items():
        sha=base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
        rows.append(f'{name},sha256={sha},{len(data)}')
    records[dist+'/RECORD']=('\n'.join(rows)+f'\n{dist}/RECORD,,\n').encode()
    with zipfile.ZipFile(path,'w') as z:
        for name,data in records.items():z.writestr(name,data)
    return path


def test_environment_real_offline_lifecycle(tmp_path):
    wheel=wheel_fixture(tmp_path);store=tmp_path/'environments';manager=EnvironmentManager(store)
    spec=ManagedEnvironmentSpec(name='cpu',python=sys.executable,artifacts=[{'path':str(wheel),'sha256':file_digest(wheel)}],expected_modules=['cvrs_fixture_package'])
    plan=manager.plan(spec)
    assert not store.exists()
    with pytest.raises(CVRSError):manager.apply(plan,approve_digest='wrong')
    assert not store.exists()
    first=manager.apply(plan,approve_digest=plan.plan_digest)
    assert first['status']=='READY'
    first_python=manager.interpreter('cpu')
    assert probe(first_python,['cvrs_fixture_package'])['packages']['cvrs-fixture-package']=='0.0.1'
    repair=manager.repair_plan('cpu')
    second=manager.apply(repair,approve_digest=repair.plan_digest)
    assert first['revision']!=second['revision'] and Path(first_python).exists()
    assert manager.doctor('cpu')['health']['status']=='HEALTHY_METADATA'
    rollback=manager.activate('cpu',first['revision'],confirm=True)
    assert rollback['applied'] and manager.interpreter('cpu')==first_python
    bad=spec.model_dump(mode='json');bad['expected_modules']=['deliberately_missing_native_module']
    failed=manager.repair_plan('cpu',replacement_spec=bad)
    with pytest.raises(CVRSError):manager.apply(failed,approve_digest=failed.plan_digest)
    assert manager.interpreter('cpu')==first_python
    assert manager.list()[0]['revisions'][-1]['status']=='FAILED'


@pytest.mark.parametrize('line',['torch>=2','torch','-r something','torch==2\nattack','torch @ https://example.com/file.whl','torch==2.*'])
def test_unpinned_environment_rejected(line):
    with pytest.raises(ValueError):ManagedEnvironmentSpec(name='x',python=sys.executable,requirements=[line])


def test_environment_changed_plan_and_unsafe_roots(tmp_path, symlink_or_skip):
    manager=EnvironmentManager(tmp_path/'envs')
    p=manager.plan({'name':'x','python':sys.executable})
    d=p.model_dump(mode='json');d['spec']['expected_modules']=['os']
    with pytest.raises(CVRSError,match='changed'):manager.apply(d,approve_digest=p.plan_digest)
    with pytest.raises(CVRSError):EnvironmentManager(Path.home())
    symlink_or_skip(tmp_path/'link', tmp_path/'other', target_is_directory=True)
    with pytest.raises(CVRSError):EnvironmentManager(tmp_path/'link')


def test_target_markers_not_controller_assumptions():
    spec=ManagedEnvironmentSpec(name='x',python='python',requirements=['missing==1.0; sys_platform == "win32"'])
    obs={'python':'3.13.5','packages':{},'modules':{},'marker_environment':{'sys_platform':'linux'}}
    assert observation_diff(spec,obs)['status']=='HEALTHY_METADATA'


def bundle(task='hbb_detection'):
    obj={'id':'a','score':0.8,'category_id':7,'box':[1.0,2.0,5.0,6.0],'attributes':{'origin':'fixture'}}
    if task=='obb_detection':obj['polygon']=[[2.,1.],[6.,2.],[5.,6.],[1.,5.]];obj['box']=None
    if task=='instance_segmentation':
        np=pytest.importorskip('numpy')
        from cvsubstrate.vision.masks import encode_mask
        mask=np.zeros((8,9),dtype=bool);mask[2:6,1:5]=True
        obj['mask']=encode_mask(mask);obj['box']=[0.5,1.5,5.5,6.5]
    if task=='grounded_detection':obj['category_id']=None;obj['phrase']='white pickup';obj['prompt_digest']='a'*64
    return RichInterchange(dataset_digest='b'*64,categories={7:'vehicle'},frames=[RichFrame(sample_id='image1',width=9,height=8,
                           task=task,objects=[RichObject(**obj)],metadata={'purpose':'software_fixture'})])


@pytest.mark.parametrize('task',['hbb_detection','obb_detection','instance_segmentation','grounded_detection'])
@pytest.mark.parametrize('target',['supervision','fiftyone'])
def test_rich_roundtrip(task,target):
    pytest.importorskip('numpy')
    b=bundle(task)
    f,g=(to_fiftyone_payload,from_fiftyone_payload) if target=='fiftyone' else (to_supervision_payload,from_supervision_payload)
    result=g(f(b))
    assert audit_roundtrip(b,result)['status']=='PRESERVED'


def test_mask_pixel_and_budget_failures():
    pytest.importorskip('numpy')
    b=bundle('instance_segmentation')
    with pytest.raises(CVRSError):to_supervision_payload(b,max_mask_pixels=4)
    payload=to_fiftyone_payload(b);payload['records'][0]['labels'][0]['mask'][0][0]=0
    assert audit_roundtrip(b,from_fiftyone_payload(payload))['status']=='CHANGED'
    payload=to_fiftyone_payload(b);payload['records'][0]['labels'][0]['bounding_box'][0]+=.001
    with pytest.raises(CVRSError):from_fiftyone_payload(payload)


def test_invalid_polygon_and_unknown_class():
    with pytest.raises(ValueError):RichObject(id='a',score=.9,polygon=[[0,0],[2,2],[0,2],[2,0]])
    b=bundle().model_dump(mode='json');b['frames'][0]['objects'][0]['category_id']=123
    with pytest.raises(ValueError):RichInterchange.model_validate(b)


def test_prompt_vocabulary_is_not_automatically_leakage():
    r=review_methodology({'prompts':[{'source':'dataset_class_vocabulary','phrases':['car','truck']}]})
    assert not any(f['severity']=='BLOCK' for f in r['findings'])
    r=review_methodology({'prompts':[{'source':'ground_truth_box','track':'fully_automatic'}]})
    assert any(f['severity']=='BLOCK' and f['rule_id']=='ORACLE_ASSISTANCE' for f in r['findings'])
    r=review_methodology({'prompts':[{'source':'ground_truth_box','track':'oracle'}]})
    assert not any(f['severity']=='BLOCK' for f in r['findings'])


def test_lineage_policy_not_all_shared_meshes_are_invalid():
    l=[{'sample_id':'a','split':'train','parents':{'mesh':'x'}},{'sample_id':'b','split':'test','parents':{'mesh':'x'}}]
    r=review_methodology({'lineage':l});assert next(f for f in r['findings'] if f['rule_id']=='SHARED_LINEAGE')['severity']=='WARN'
    r=review_methodology({'lineage':l,'split_policy':{'must_not_cross':['mesh']}})
    assert next(f for f in r['findings'] if f['rule_id']=='SHARED_LINEAGE')['severity']=='BLOCK'


def test_linter_missing_evidence_and_seed_omission():
    assert review_methodology({})['status']=='INSUFFICIENT_EVIDENCE'
    r=review_methodology({'seeds':{'declared':[1,2,3],'included':[1,3]}})
    assert any(f['rule_id']=='UNEXPLAINED_SEED_OMISSION' for f in r['findings'])


def test_recipe_library_contribution(tmp_path):
    from cvsubstrate.product.recipes import search_recipes,check_recipe,contribute_recipe
    r=search_recipes();assert r['count']>=10
    value=r['matches'][0];value.pop('readiness')
    file=tmp_path/'recipe.json';write_json(file,value)
    assert contribute_recipe(file,tmp_path/'contribution')['status']=='PREPARED_FOR_REVIEW'
    value['status']='EXECUTED'
    with pytest.raises(ValueError):check_recipe(value,contributor=True)


def test_paper_approval_real_stdlib_execution(tmp_path):
    from cvsubstrate.product.onboarding import prepare_paper,approve_paper,execute_approved
    repo=tmp_path/'native';repo.mkdir()
    (repo/'infer.py').write_text('import sys,json\nfrom pathlib import Path\nPath(sys.argv[1]).write_text(json.dumps({"value":17}))\n')
    decisions={'operations':{'predict':{'argv':['${python}','${repo}/infer.py','${output}/result.json'],
                'outputs':{'result':{'path':'result.json','kind':'json'}}}}}
    out=tmp_path/'wrapped';prepare_paper(repo,out,python=sys.executable,decisions=decisions)
    original=read_json(out/'paper.json');assert original['trust_code'] is False
    approval=tmp_path/'approval.json';approve_paper(out/'paper.json','local-test-operator',approval)
    assert read_json(out/'paper.json')==original
    result=execute_approved(out/'paper.json',approval,'predict',tmp_path/'executed',trust=True)
    assert result['status']=='SUCCEEDED'
    (repo/'infer.py').write_text('print("changed")')
    with pytest.raises(Exception):execute_approved(out/'paper.json',approval,'predict',tmp_path/'changed',trust=True)


def test_uv_real_offline_environment(tmp_path):
    import shutil
    if not shutil.which('uv'):pytest.skip('uv executable unavailable')
    m=EnvironmentManager(tmp_path/'uv-envs')
    plan=m.plan({'name':'uvcore','backend':'uv','python':sys.executable,'expected_modules':['json']})
    r=m.apply(plan,approve_digest=plan.plan_digest)
    assert r['status']=='READY'
    assert m.doctor('uvcore')['health']['status']=='HEALTHY_METADATA'
    assert plan.network_effects==[]


def test_environment_rejects_symlink_pointer_and_artifact(tmp_path, symlink_or_skip):
    m=EnvironmentManager(tmp_path/'managed')
    target=tmp_path/'outside.json';write_json(target,{'revision':'r000001-'+'a'*12})
    (tmp_path/'managed/cpu').mkdir(parents=True)
    symlink_or_skip(tmp_path/'managed/cpu/current.json', target)
    with pytest.raises(CVRSError,match='symlink'):m.doctor('cpu')
    w=wheel_fixture(tmp_path);link=tmp_path/'linked.whl';symlink_or_skip(link, w)
    m=EnvironmentManager(tmp_path/'safe')
    with pytest.raises(CVRSError):m.plan({'name':'x','python':sys.executable,'artifacts':[{'path':str(link),'sha256':file_digest(w)}]})


@pytest.mark.parametrize('target',['fiftyone','supervision'])
def test_rich_payload_is_canonical_json_roundtrippable(tmp_path,target):
    pytest.importorskip('numpy')
    from cvsubstrate.product.interchange import exchange
    source=bundle('instance_segmentation')
    out=exchange(source.model_dump(mode='json'),target,'export')
    write_json(tmp_path/'payload.json',out)
    restored=exchange(read_json(tmp_path/'payload.json'),target,'import')
    assert audit_roundtrip(source,restored)['status']=='PRESERVED'


def test_fiftyone_hbb_import_does_not_require_numpy(monkeypatch):
    """Box-only interchange stays usable in the minimal controller environment."""
    import builtins
    payload=to_fiftyone_payload(bundle('hbb_detection'))
    original_import=builtins.__import__
    def guarded_import(name,*args,**kwargs):
        if name=='numpy':raise ModuleNotFoundError('NumPy is mask-only for this path')
        return original_import(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',guarded_import)
    restored=from_fiftyone_payload(payload)
    assert audit_roundtrip(bundle('hbb_detection'),restored)['status']=='PRESERVED'
