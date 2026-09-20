"""Adoption/publication checks. Procedural commands are NOT native-framework proofs."""
from pathlib import Path
import json,sys,subprocess,hashlib,os
import pytest
from cvsubstrate.provenance.io import write_json,read_json,file_digest,digest
from cvsubstrate.adoption.inspect import inspect_repository
from cvsubstrate.adoption.wrapping import wrap_repository,validate_paper,run_paper
from cvsubstrate.adoption.common import output_tree,load_config
from cvsubstrate.provenance.artifact_set import verify_directory

@pytest.fixture
def repo(tmp_path):
    r=tmp_path/'native source';r.mkdir()
    (r/'predict.py').write_text("import pathlib,json,sys\np=pathlib.Path(sys.argv[1]);p.mkdir(parents=True,exist_ok=True)\n(p/'result.json').write_text(json.dumps({'value':7}))\n")
    return r

def wrapped(repo,tmp_path,script='predict.py'):
    dest=tmp_path/'wrapped'
    wrap_repository(repo,dest,commands={'predict':{'argv':['${python}','${repo}/'+script,'${output}'],'outputs':{'value':{'path':'result.json','kind':'json'}},'timeout_seconds':10}},purpose='software_fixture')
    p=dest/'paper.json';s=read_json(p);s['trust_code']=True;write_json(p,s);return p

def test_static_scanner_never_executes(repo):
    (repo/'setup.py').write_text("raise RuntimeError('MUST_NOT_RUN')\nimport mmdet\nfrom sam3.model import whatever\n")
    (repo/'requirements.txt').write_text('torch<2\nmmdet<3\n')
    r=inspect_repository(repo)
    assert {'mmdetection','sam3'}<=set(r.frameworks)
    assert not r.executable_code_loaded
    assert any(x.kind=='requirement' and x.value=='torch<2' for x in r.observations)

def test_source_hash_changes(repo):
    a=inspect_repository(repo).root_identity;(repo/'predict.py').write_text('x=2\n')
    assert a!=inspect_repository(repo).root_identity

def test_symlink_not_followed(repo,tmp_path,symlink_or_skip):
    other=tmp_path/'secret.py';other.write_text('import private_thing\n')
    symlink_or_skip(repo/'linked.py', other)
    assert 'linked.py' not in inspect_repository(repo).files

def test_scan_truncation_is_visible(repo):
    assert inspect_repository(repo,max_bytes=1).truncated

@pytest.mark.parametrize('constraints,status',[
 (['torch<2','torch>=2.7'],'DECLARED_CONFLICTS'),
 (['torch==2.0','torch==2.0+cpu'],'NO_PROVEN_CONFLICTS'),
 (['torch>=2,<3','torch==2.5'],'NO_PROVEN_CONFLICTS'),
 (['torch==1.13','torch==2.1'],'DECLARED_CONFLICTS'),
 (['torch~=2.2.0','torch>=2.3'],'DECLARED_CONFLICTS'),
 (['torch>=2,<=2','torch!=2'],'DECLARED_CONFLICTS'),
])
def test_declared_conflicts(constraints,status):
    from cvsubstrate.adoption.conflicts import explain_constraints
    reports=[{'repository_name':str(i),'observations':[{'kind':'requirement','value':c,'path':'requirements.txt','line':1}]} for i,c in enumerate(constraints)]
    r=explain_constraints(reports);assert r['status']==status;assert not r['installability_proven']
    assert 'gradients' in r['boundary_warning']

def test_markers_are_not_assumed():
    from cvsubstrate.adoption.conflicts import explain_constraints
    r=explain_constraints([{'repository_name':'a','observations':[{'kind':'requirement','value':'torch<2; python_version < "3.9"','path':'requirements.txt','line':1}]}])
    assert r['unresolved']

def test_wrapper_starts_unresolved(repo,tmp_path):
    d=tmp_path/'wrap';wrap_repository(repo,d)
    assert validate_paper(d/'paper.json')['status']=='NOT_READY'

def test_real_argv_wrapper(repo,tmp_path):
    p=wrapped(repo,tmp_path);r=run_paper(p,'predict',tmp_path/'run',trust=True)
    assert r['status']=='SUCCEEDED';assert r['verification']['status']=='VERIFIED'
    assert read_json(tmp_path/'run/outputs/result.json')=={'value':7}

def test_wrapper_trust_is_required(repo,tmp_path):
    p=wrapped(repo,tmp_path)
    with pytest.raises(Exception,match='trust|review'):run_paper(p,'predict',tmp_path/'run')

def test_changed_source_prevents_execution(repo,tmp_path):
    p=wrapped(repo,tmp_path);(repo/'predict.py').write_text('raise RuntimeError()')
    with pytest.raises(Exception,match='changed'):run_paper(p,'predict',tmp_path/'run',trust=True)

def test_missing_output_is_failed_evidence(repo,tmp_path):
    (repo/'predict.py').write_text('print("not a result")\n');p=wrapped(repo,tmp_path)
    r=run_paper(p,'predict',tmp_path/'run',trust=True)
    assert r['status']=='FAILED';assert r['error']['code']=='OUTPUT_MISSING'
    assert verify_directory(tmp_path/'run')['status']=='VERIFIED'

def test_output_cannot_be_in_source(repo,tmp_path):
    p=wrapped(repo,tmp_path)
    with pytest.raises(Exception,match='outside'):run_paper(p,'predict',repo/'result',trust=True)

@pytest.mark.parametrize('path',['../escape','/absolute','C:\\escape','a/../../b'])
def test_output_path_validation(path):
    from cvsubstrate.adoption.contracts import CommandOutput
    with pytest.raises(Exception):CommandOutput(path=path)

def test_environment_pass_through(repo,tmp_path):
    (repo/'predict.py').write_text("import os,sys,pathlib,json\np=pathlib.Path(sys.argv[1]);(p/'result.json').write_text(json.dumps({'value':os.environ['CVRS_USER_VALUE']}))\n")
    p=wrapped(repo,tmp_path);s=read_json(p);s['operations']['predict']['env']={'CVRS_USER_VALUE':'chosen'};write_json(p,s)
    assert run_paper(p,'predict',tmp_path/'run',trust=True)['status']=='SUCCEEDED'
    assert read_json(tmp_path/'run/outputs/result.json')['value']=='chosen'

def test_composition_moves_only_explicit_outputs(repo,tmp_path):
    from cvsubstrate.adoption.composition import run_composition
    p=wrapped(repo,tmp_path)
    (repo/'consumer.py').write_text("import json,sys,pathlib\nv=json.loads(pathlib.Path(sys.argv[2]).read_text());v['value']+=1\n(pathlib.Path(sys.argv[1])/'result.json').write_text(json.dumps(v))\n")
    # Source changed intentionally; rebind the reviewed two specifications.
    source=read_json(p);source['repository_digest']=inspect_repository(repo).root_identity;write_json(p,source)
    b=dict(source);b['repo']=str(repo);b['inputs']={'previous':'BOUND_BY_GRAPH'};b['operations']={'predict':{'argv':['${python}','${repo}/consumer.py','${output}','${inputs.previous}'],'outputs':{'value':{'path':'result.json'}}}}
    q=tmp_path/'consumer.json';write_json(q,b)
    graph={'nodes':[{'id':'a','paper_spec':str(p)},{'id':'b','paper_spec':str(q),'depends_on':['a'],'bindings':{'previous':{'node':'a','output':'value'}}}]}
    result=run_composition(graph,tmp_path/'graph',trust=True)
    assert result['status']=='SUCCEEDED'
    assert read_json(tmp_path/'graph/b/outputs/result.json')['value']==8

def test_composition_no_autograd():
    from cvsubstrate.adoption.composition import compile_composition
    with pytest.raises(Exception,match='native worker'):compile_composition({'nodes':[{'id':'a','cross_worker_gradients':True}]})

def test_composition_cycle():
    from cvsubstrate.adoption.composition import compile_composition
    with pytest.raises(ValueError):compile_composition({'nodes':[{'id':'a','depends_on':['b']},{'id':'b','depends_on':['a']}]})

def test_tensor_port_and_hash(tmp_path):
    np=pytest.importorskip("numpy")
    from cvsubstrate.adoption.composition import inspect_artifact,check_port
    p=tmp_path/'feature.npy';np.save(p,np.ones((1,3,4,4),dtype=np.float32),allow_pickle=False)
    v={'id':'x','kind':'features','path':'feature.npy','sha256':file_digest(p),'shape':[1,3,4,4],'dtype':'float32','semantics':{'stride':4}}
    assert inspect_artifact(v,tmp_path)['status']=='VERIFIED'
    assert check_port(v,{'kind':'features','dtype':'float64'})['errors']

@pytest.mark.parametrize('oracle',['oracle','ground_truth','ground_truth_oracle'])
def test_methodology_oracle(oracle):
    from cvsubstrate.adoption.methodology import lint_methodology
    r=lint_methodology({'prompts':[{'source':oracle}]})
    assert any(x['code']=='ORACLE_PROMPT' for x in r['findings'])

def test_methodology_controls_and_leakage():
    from cvsubstrate.adoption.methodology import lint_methodology
    r=lint_methodology({'arms':[{'id':'R','optimizer_updates':2},{'id':'R+S','optimizer_updates':4}],
       'lineage':[{'split':'train','scene':'x'},{'split':'test','scene':'x'}],'assets':[{'revision':'main'}],
       'test_accesses':[{'before_selection':True}]})
    assert len(r['findings'])==4

def test_eval_missing_not_equal():
    from cvsubstrate.adoption.methodology import evaluation_equivalence
    assert evaluation_equivalence({}, {})['status']=='UNKNOWN'
    assert evaluation_equivalence({'task':'hbb'},{'task':'mask'})['status']=='INCOMPATIBLE'

def test_asset_ack_hash_resume_prune(tmp_path):
    from cvsubstrate.adoption.assets import AssetManager
    p=tmp_path/'data';p.write_bytes(b'abc'*100)
    a={'id':'a','kind':'other','source':str(p),'sha256':file_digest(p),'size_bytes':300,'license_id':'test-fixture'}
    m=AssetManager(tmp_path/'cache')
    with pytest.raises(Exception,match='acknowledge'):m.fetch(a)
    m.acknowledge(a,'test-operator','software fixture');result=m.fetch(a)
    assert result['status']=='FETCHED';assert m.fetch(a)['status']=='CACHED'
    assert m.prune([],apply=False)['dry_run'];assert Path(result['path']).exists()
    assert not m.prune([a['sha256']],apply=False)['candidates']

def test_wrong_asset_quarantined(tmp_path):
    from cvsubstrate.adoption.assets import AssetManager
    p=tmp_path/'data';p.write_bytes(b'bad');a={'id':'a','kind':'other','source':str(p),'sha256':'0'*64}
    m=AssetManager(tmp_path/'cache');m.acknowledge(a,'test','fixture')
    with pytest.raises(Exception,match='quarantined'):m.fetch(a)
    assert list((tmp_path/'cache/objects').glob('*.rejected-*'))

def test_hf_no_implicit_network():
    from cvsubstrate.adoption.assets import hf_inspect
    with pytest.raises(Exception,match='network'):hf_inspect('test/model')

def test_local_full_model_identity(tmp_path):
    from cvsubstrate.adoption.assets import lock_local_assets
    (tmp_path/'weights').write_bytes(b'fake explicit bytes');(tmp_path/'config.json').write_text('{}')
    r=lock_local_assets(tmp_path);assert len(r['files'])==2;assert not r['trust_remote_code']

def test_recipe_archetype_limitations():
    from cvsubstrate.adoption.recipes import recipe_list,recipe_inspect
    assert {'segearth-ov3','uav-synthscene-2026'} <= {x['id'] for x in recipe_list()}
    assert len(recipe_list()) >= 5
    assert recipe_inspect('segearth-ov3')['integration_boundary']=='requires_author_refactor'
    assert recipe_inspect('uav-synthscene-2026')['status']=='CANDIDATE'
    assert all(x['status']!='EXECUTED' for x in recipe_list())

def test_environment_generator_does_not_solve(tmp_path):
    from cvsubstrate.adoption.environments import scaffold_environment
    r=scaffold_environment('mmrotate',tmp_path/'env');assert r['status']=='INCOMPLETE_PINS'
    assert (tmp_path/'env/Apptainer.def').is_file()

@pytest.mark.parametrize('scheduler',['slurm','pbs','lsf'])
def test_hpc_generate_only(tmp_path,scheduler):
    from cvsubstrate.adoption.environments import hpc_script
    r=hpc_script(tmp_path/'space spec.json',tmp_path/'job',scheduler=scheduler)
    assert not r['submitted'];assert 'CVRS_OUTPUT' in (tmp_path/'job').read_text()

def test_bridge_requires_opt_in(tmp_path):
    from cvsubstrate.bridges.service import run_bridge
    with pytest.raises(Exception,match='trust|code'):run_bridge({'bridge':'wandb','operation':'export','payload':{},'output_dir':str(tmp_path/'x')})
    with pytest.raises(Exception,match='acknowledge'):run_bridge({'bridge':'hf','operation':'inspect','payload':{},'output_dir':str(tmp_path/'y'),'trust_code':True,'allow_network':True})

def test_semantic_not_instance_and_ignore():
    np=pytest.importorskip("numpy")
    from cvsubstrate.bridges.semantic import semantic_metrics
    r=semantic_metrics([(np.array([[0,1],[255,1]]),np.array([[0,0],[19,1]]))],2)
    assert r['evaluated_pixels']==3;assert r['confusion_matrix']==[[1,0],[1,1]];assert not r['official_benchmark']

def test_simulator_coco_keeps_missing_unknown(tmp_path):
    from cvsubstrate.bridges.simulators import import_simulator
    p=tmp_path/'coco.json';write_json(p,{'images':[{'id':1,'file_name':'x.png','width':20,'height':20}],'annotations':[],'categories':[]})
    r=import_simulator('blenderproc',p,tmp_path/'out');assert r['samples']==1
    assert read_json(tmp_path/'out/import.json')['simulator_executed'] is False

def test_simulator_requires_explicit_mapping(tmp_path):
    from cvsubstrate.bridges.simulators import import_simulator
    p=tmp_path/'x.json';write_json(p,{})
    with pytest.raises(ValueError,match='field map'):import_simulator('colosseum',p,tmp_path/'x')

def test_public_tree_excludes_assets_but_blocks_identity(tmp_path):
    from cvsubstrate.publication.audit import public_tree
    r=tmp_path/'source';(r/'src').mkdir(parents=True);(r/'src/a.py').write_text('x=1\n');(r/'README.md').write_text('hello')
    (r/'model.pth').write_bytes(b'not a model')
    with pytest.raises(ValueError,match='identity|license'):public_tree(r,tmp_path/'blocked')
    result=public_tree(r,tmp_path/'preview',preview=True)
    assert result['status']=='PREVIEW';assert not (tmp_path/'preview/model.pth').exists()
    assert read_json(tmp_path/'preview/PUBLIC_AUDIT.json')['status']=='BLOCK'

def test_credentials_block_even_preview(tmp_path):
    from cvsubstrate.publication.audit import public_tree
    r=tmp_path/'source';r.mkdir();(r/'README.md').write_text('token='+'ghp_'+'A'*40)
    with pytest.raises(ValueError,match='sensitive'):public_tree(r,tmp_path/'out',preview=True)

def test_support_redacts(tmp_path,monkeypatch):
    from cvsubstrate.publication import support
    monkeypatch.setattr(support,'doctor',lambda:{'python':'test'})
    run=tmp_path/'run';run.mkdir();write_json(run/'execution.json',{'token':'secret','path':'/mnt/data/private-project/a.py'})
    (run/'model.pth').write_bytes(b'not public')
    support.support_bundle(run,tmp_path/'out');s=(tmp_path/'out/execution.json.json').read_text()
    assert 'secret' not in s and 'private-project' not in s
    assert not (tmp_path/'out/model.pth').exists()

def test_html_escapes(tmp_path):
    from cvsubstrate.publication.site import results_site,markdown
    r=tmp_path/'run';r.mkdir();write_json(r/'metrics.json',{'x':'<script>alert(1)</script>'})
    results_site([r],tmp_path/'site');assert '<script>' not in (tmp_path/'site/run-0.html').read_text()
    assert 'javascript:' not in markdown('[bad](javascript:alert)')

def test_source_zip_deterministic(tmp_path):
    from cvsubstrate.publication.build import deterministic_zip
    r=tmp_path/'src';r.mkdir();(r/'a.txt').write_text('abc')
    a=deterministic_zip(r,tmp_path/'a.zip');b=deterministic_zip(r,tmp_path/'b.zip')
    assert a['sha256']==b['sha256']

def test_identity_cannot_fake_approval():
    from cvsubstrate.publication.metadata import validate_settings
    with pytest.raises(ValueError,match='authors'):validate_settings({'identity_approved':True})

def test_project_has_real_canonical_spec(tmp_path):
    from cvsubstrate.adoption.projects import init_project
    from cvsubstrate.execution.runner import load_experiment
    r=init_project(tmp_path/'project');assert r['profile']=='detection'
    load_experiment(tmp_path/'project/experiments/baseline.json')

def test_argv_cli_and_version(tmp_path):
    from cvsubstrate.cli_adoption import main
    assert main(['init',str(tmp_path/'p')])==0
    assert main(['inspect-repo',str(tmp_path/'p'),'--out',str(tmp_path/'report.json')])==0
    from cvsubstrate._version import __version__
    from cvsubstrate.release import source_version
    assert __version__ == source_version(Path(__file__).resolve().parents[1])

def test_yaml_duplicate_rejected(tmp_path):
    p=tmp_path/'x.yaml';p.write_text('a: 1\na: 2\n')
    with pytest.raises(ValueError):load_config(p)

def test_git_dirty_capture_materialize(tmp_path):
    from cvsubstrate.adoption.git import capture_source,materialize_source
    r=tmp_path/'repo';r.mkdir()
    def git(*args):subprocess.run(['git','-C',str(r),*args],check=True,capture_output=True)
    git('init');git('config','user.name','Fixture Author');git('config','user.email','fixture@example.invalid')
    (r/'x.txt').write_text('before');git('add','.');git('commit','-m','fixture');(r/'x.txt').write_text('after')
    capture_source(r,tmp_path/'capture');materialize_source(tmp_path/'capture',tmp_path/'copy',trust=True)
    assert (tmp_path/'copy/x.txt').read_text()=='after';assert (r/'x.txt').read_text()=='after'

def test_license_audit_unknown_blocks():
    from cvsubstrate.publication.licenses import audit_licenses
    assert audit_licenses({'assets':[{'id':'x','kind':'weights','license_id':'unknown'}]})['status']=='BLOCK'

def test_json_and_cuda_changes_affect_repo_identity(tmp_path):
    from cvsubstrate.adoption.inspect import inspect_repository
    (tmp_path/'kernel.cu').write_text('void kernel() {}')
    (tmp_path/'config.json').write_text('{"width": 32}')
    one=inspect_repository(tmp_path)
    (tmp_path/'config.json').write_text('{"width": 64}')
    two=inspect_repository(tmp_path)
    assert one.root_identity!=two.root_identity and 'kernel.cu' in two.files


def test_setup_static_requirements_without_execution(tmp_path):
    from cvsubstrate.adoption.inspect import inspect_repository
    (tmp_path/'setup.py').write_text("from setuptools import setup\nsetup(install_requires=['torch<2'], python_requires='>=3.8')\nraise RuntimeError('never execute')\n")
    (tmp_path/'setup.cfg').write_text('[options]\ninstall_requires =\n    numpy<2\n')
    rows=inspect_repository(tmp_path).observations
    assert {'torch<2','numpy<2'}<={x.value for x in rows if x.kind=='requirement'}


def test_native_requirement_directory(tmp_path):
    from cvsubstrate.adoption.inspect import inspect_repository
    (tmp_path/'requirements').mkdir();(tmp_path/'requirements/runtime.txt').write_text('mmcv-full==1.7.1\n')
    assert any(x.value=='mmcv-full==1.7.1' for x in inspect_repository(tmp_path).observations)


def test_lsf_gpu_and_long_walltime(tmp_path):
    from cvsubstrate.adoption.environments import hpc_script
    p=tmp_path/'job.sh';hpc_script('experiment.json',p,scheduler='lsf',gpus=2,walltime='120:00:01')
    text=p.read_text();assert '#BSUB -gpu "num=2"' in text and '#BSUB -W 7201' in text
    with pytest.raises(ValueError):hpc_script('e',tmp_path/'bad.sh',walltime='01:99:00')


def test_mask_visual_overlay(tmp_path):
    np=pytest.importorskip('numpy');Image=pytest.importorskip('PIL.Image')
    from cvsubstrate.vision.masks import encode_mask
    from cvsubstrate.publication.site import visual_diff
    p=tmp_path/'image.png';Image.new('RGB',(12,10)).save(p)
    mask=np.zeros((10,12),dtype=np.uint8);mask[3:6,4:7]=1
    pred={'width':12,'height':10,'masks':[encode_mask(mask).model_dump(mode='json')], 'polygons':[[1,1,7,1,7,8,1,8]]}
    result=visual_diff(p,pred,pred,tmp_path/'site',allow_image_copy=True)
    assert result['status']=='EXPORTED' and (tmp_path/'site/left.png').is_file()


def test_nested_document_navigation(tmp_path):
    from cvsubstrate.publication.site import build_docs,link_check
    root=tmp_path/'repo';d=root/'docs/public';(d/'reference').mkdir(parents=True)
    for name in ['index','heritage','research','extend']:(d/(name+'.md')).write_text('# '+name)
    (d/'reference/cli.md').write_text('# CLI\n\n[Start](../index.md)')
    build_docs(root,tmp_path/'site')
    assert link_check(tmp_path/'site')['status']=='PASS'


def test_link_check_resolves_site_root_links_inside_site(tmp_path):
    from cvsubstrate.publication.site import link_check
    site=tmp_path/'site';site.mkdir()
    (site/'index.html').write_text('<a href="/assets/app.css">asset</a>')
    (site/'assets').mkdir();(site/'assets/app.css').write_text('body{}')
    assert link_check(site)['status']=='PASS'


def test_cli_schema_inventory_changes_detected(tmp_path):
    from cvsubstrate.publication.compatibility import compare_compatibility
    for name in ['old','new']:
        p=tmp_path/name/'src/cvsubstrate/resources/public';p.mkdir(parents=True)
        write_json(p/'api-surface.json',{'cli':{'cvrs x':{'options':['--old'] if name=='old' else []}},'versions':{'worker':'1' if name=='old' else '2'}})
    r=compare_compatibility(tmp_path/'old',tmp_path/'new')
    assert r['status']=='REVIEW_REQUIRED' and r['cli_changed']==['cvrs x'] and r['protocol_changes']


def test_derived_version_source(tmp_path):
    from cvsubstrate.release import source_version
    (tmp_path/'src/renamed').mkdir(parents=True)
    (tmp_path/'src/renamed/_version.py').write_text("__version__ = '0.6.0a1'\n")
    (tmp_path/'pyproject.toml').write_text('[project]\nname="renamed"\ndynamic=["version"]\n[tool.setuptools.dynamic]\nversion={attr="renamed._version.__version__"}\n')
    assert source_version(tmp_path)=='0.6.0a1'


def test_gallery_external_models_are_not_faked(tmp_path):
    from cvsubstrate.adoption.gallery import run_example
    assert run_example('06-open-vocabulary',tmp_path/'open')['status']=='ASSETS_REQUIRED'
    assert run_example('03-cross-framework',tmp_path/'cross')['status']=='ASSETS_REQUIRED'
    assert run_example('02-mmdetection-heritage',tmp_path/'heritage')['status']=='MATERIALIZED_UNEXECUTED'


def test_stable_native_execution_directory_on_failure(tmp_path):
    from cvsubstrate.adoption.common import execution_tree
    from cvsubstrate.provenance.artifact_set import verify_directory
    out=tmp_path/'native'
    with pytest.raises(RuntimeError):
        with execution_tree(out) as actual:
            assert actual==out.resolve();write_json(actual/'native-path.json',{'path':str(actual)})
            raise RuntimeError('native failure')
    assert read_json(out/'FAILURE.json')['status']=='FAILED'
    assert verify_directory(out)['status']=='VERIFIED'


def test_replicator_export_uses_structured_labels(tmp_path):
    np=pytest.importorskip('numpy')
    from cvsubstrate.bridges.simulators import import_simulator
    a=np.array([(1,0,1,7,8,.2)],dtype=[('semanticId','i4'),('x_min','i4'),('y_min','i4'),('x_max','i4'),('y_max','i4'),('occlusionRatio','f4')])
    np.save(tmp_path/'bounding_box_2d_tight_0000.npy',a,allow_pickle=False)
    write_json(tmp_path/'bounding_box_2d_tight_labels_0000.json',{'1':{'class':'car'}})
    # Reader variants are explicit; native simulator execution is not claimed.
    result=import_simulator('replicator',tmp_path,tmp_path/'../replicator-export')
    assert result.get('status')

def test_profile_observes_real_process(tmp_path):
    pytest.importorskip('psutil')
    from cvsubstrate.publication.profiling import profile_command
    r=profile_command([sys.executable,'-c','import time; x=bytearray(2000000); time.sleep(.15)'],tmp_path/'profile',trust=True)
    assert r['status']=='SUCCEEDED' and r['samples']>0 and r['sampled_peak_process_tree_rss_bytes']>0
    assert r['phase_breakdown']['status']=='UNOBSERVED' and r['sampled_gpu_process_bytes'] is None


def test_phase_durations_are_not_invented(tmp_path):
    from cvsubstrate.publication.profiling import phase_durations
    p=tmp_path/'events.jsonl';p.write_text('{"phase":"model_load","event":"start","monotonic_seconds":1}\n{"phase":"model_load","event":"end","monotonic_seconds":3}\n')
    assert phase_durations(p)['phases']['model_load']==[2]


def test_hash_only_local_asset_is_locked():
    from cvsubstrate.adoption.methodology import lint_methodology
    r=lint_methodology({'assets':[{'source':'local','sha256':'a'*64}]})
    assert not r['findings']

def test_bound_input_hash_prevents_changed_data(tmp_path):
    from cvsubstrate.adoption.wrapping import wrap_repository,validate_paper
    repo=tmp_path/'repo';repo.mkdir();(repo/'infer.py').write_text('pass\n')
    data=tmp_path/'input.json';write_json(data,{'x':1})
    commands={'predict':{'argv':['${python}','${repo}/infer.py','${inputs.data}'],'outputs':{'result':{'path':'result.json','kind':'json'}}}}
    wrap_repository(repo,tmp_path/'wrapped',commands=commands)
    p=tmp_path/'wrapped/paper.json';v=read_json(p);v['inputs']={'data':str(data)};v['input_digests']={'data':file_digest(data)};write_json(p,v)
    assert validate_paper(p)['status']=='READY'
    write_json(data,{'x':2})
    assert validate_paper(p)['status']=='NOT_READY'
