"""0.4 engineering checks; not model/evaluator/scientific certification."""
import json,subprocess,sys,os,copy,zipfile
from pathlib import Path
import pytest
from cvsubstrate.provenance.io import read_json,write_json,digest,file_digest
from cvsubstrate.errors import CVRSError

@pytest.fixture
def fixtures(tmp_path):
    from cvsubstrate.data.groundwork_fixtures import generate
    generate(tmp_path/'fixtures');return tmp_path/'fixtures'

def test_schema_export_and_envelope_version(tmp_path):
    from cvsubstrate.schemas.registry import schema_registry,export_schemas,validate_artifact
    from cvsubstrate.contracts.groundwork import ObjectSizePolicy,ArtifactEnvelope
    export_schemas(tmp_path/'schemas');assert len(list((tmp_path/'schemas').glob('*.json')))==len(schema_registry())
    with pytest.raises(CVRSError):validate_artifact(ArtifactEnvelope(schema_name='ObjectSizePolicy',payload_version='9',payload=ObjectSizePolicy().model_dump()).model_dump())

def test_migration_no_source_changes(fixtures):
    from cvsubstrate.schemas.registry import migrate_artifact,validate_artifact
    source=fixtures/'size-envelope-legacy.json';before=file_digest(source);target=fixtures/'converted.json'
    migrate_artifact(source,target);assert file_digest(source)==before;assert validate_artifact(read_json(target))['status']=='VALID'

def test_store_cache_identity_and_tamper(tmp_path):
    from cvsubstrate.artifacts.store import LocalArtifactStore,ActionCache
    p=tmp_path/'source';p.write_bytes(b'payload');store=LocalArtifactStore(tmp_path/'store');r=store.put(p)
    assert store.verify(r.sha256);store.materialize(r.sha256,tmp_path/'copy');assert file_digest(tmp_path/'copy')==r.sha256
    store.get(r.sha256).write_bytes(b'changed');assert not store.verify(r.sha256)
    with pytest.raises(CVRSError):store.get(r.sha256)
    with pytest.raises(CVRSError):store.exists('../escape')

def test_dag_cache_resume_and_invalidation(fixtures):
    from cvsubstrate.contracts.groundwork import ExecutionGraph
    from cvsubstrate.experiments.dag import execute_graph
    g=ExecutionGraph.model_validate(read_json(fixtures/'graph.json'));out=fixtures/'graph-run'
    one=execute_graph(g,out,cache_root=fixtures/'cache');assert all(n['status']=='SUCCEEDED' for n in one['nodes'].values())
    assert execute_graph(g,out,cache_root=fixtures/'cache',resume=True)['nodes']==one['nodes']
    rerun=execute_graph(g,out,cache_root=fixtures/'cache',resume=True,invalidate=['emit'])
    assert rerun['nodes']['copy']['directory']!=one['nodes']['copy']['directory']
    execute_graph(g,fixtures/'second',cache_root=fixtures/'cache')

def test_dag_rejects_cycles_and_unsafe_retries():
    from cvsubstrate.contracts.groundwork import ExecutionGraph,ExecutionNode
    with pytest.raises(ValueError):ExecutionGraph(name='bad',nodes=[{'id':'a','action':'x','depends_on':['b']},{'id':'b','action':'x','depends_on':['a']}])
    with pytest.raises(ValueError):ExecutionNode(id='x',action='x',retries=1)

def test_capsule_roundtrip_and_traversal(fixtures):
    from cvsubstrate.artifacts.capsule import create_capsule,archive_capsule,materialize_capsule,validate_capsule
    source=fixtures/'base';out=fixtures/'capsule';create_capsule(source,out)
    archive_capsule(out,fixtures/'bundle.zip');materialize_capsule(fixtures/'bundle.zip',fixtures/'extracted');assert validate_capsule(fixtures/'extracted')['status']=='VERIFIED'
    with zipfile.ZipFile(fixtures/'evil.zip','w') as z:z.writestr('../outside','x')
    with pytest.raises((ValueError,CVRSError)):materialize_capsule(fixtures/'evil.zip',fixtures/'invalid')

def test_capsule_refuses_invalid_seal(fixtures):
    from cvsubstrate.artifacts.capsule import create_capsule
    from cvsubstrate.provenance.artifact_set import seal_directory
    folder=fixtures/'sealed';folder.mkdir();(folder/'a').write_text('a');seal_directory(folder);(folder/'a').write_text('b')
    with pytest.raises(CVRSError):create_capsule(folder,fixtures/'badcapsule')

@pytest.mark.parametrize('kind',['coco','dior','xview','visdrone','uavdt','dota'])
def test_aerial_readers_keep_image_universe(fixtures,kind):
    from cvsubstrate.datasets.importers import import_dataset
    r=import_dataset(read_json(fixtures/f'dataset-{kind}.json'),fixtures/f'import-{kind}')
    assert r['images']==2;assert r['annotations']==1
    m=read_json(fixtures/f'import-{kind}/dataset.json');assert m['purpose']=='software_fixture'
    assert len(m['samples'])==2

def test_materialization_preserves_identity(fixtures):
    from cvsubstrate.datasets.importers import import_dataset
    from cvsubstrate.datasets.materialize import materialize_dataset
    import_dataset(read_json(fixtures/'dataset-coco.json'),fixtures/'import')
    expected=read_json(fixtures/'import/import.json')['dataset_digest']
    r=materialize_dataset(fixtures/'import/dataset.json',fixtures/'base',fixtures/'bound')
    assert r['dataset_digest']==expected

def test_ignore_preserved_not_misrepresented(fixtures):
    from cvsubstrate.datasets.importers import import_dataset
    from cvsubstrate.data.manifest import load_manifest
    spec=read_json(fixtures/'dataset-visdrone.json');p=Path(spec['images'][0]['annotation']);parts=p.read_text().strip().split(',');parts[4]='0';p.write_text(','.join(parts))
    import_dataset(spec,fixtures/'ignored');assert read_json(fixtures/'ignored/dataset.json')['samples'][0]['boxes'][0]['ignore']
    # Import preserves it; a plain HBB evaluator cannot silently score it as normal GT.
    from cvsubstrate.contracts.models import DatasetManifest
    from cvsubstrate.data.manifest import validate_manifest
    with pytest.raises(CVRSError):validate_manifest(DatasetManifest.model_validate(read_json(fixtures/'ignored/dataset.json')),check_files=False)

@pytest.mark.parametrize('kind',['nms','soft_nms','weighted_box_fusion','keep_all'])
def test_merge_deterministic(fixtures,kind):
    from cvsubstrate.geometry.merge import merge_detections
    items=read_json(fixtures/'merge-input.json');a=merge_detections(items,{'kind':kind});b=merge_detections(list(reversed(items)),{'kind':kind})
    assert a==b;assert a['input_count']==2
    assert a['output_count']==(1 if kind in {'nms','weighted_box_fusion'} else 2)

def test_oriented_merge():
    from cvsubstrate.geometry.merge import merge_detections
    p=[[0,0],[3,0],[3,3],[0,3]]
    r=merge_detections([{'id':'a','polygon':p,'score':.9,'category_id':0},{'id':'b','polygon':p,'score':.8,'category_id':0}],{'kind':'oriented_nms'})
    assert r['output_count']==1

def test_multi_scale_geometry_and_memory(fixtures):
    from cvsubstrate.data.large import plan_large_image,map_box_to_source
    p=plan_large_image(read_json(fixtures/'large-plan.json'))
    for tile in p['tiles']:
        v=tile['valid_region_xyxy'];b=map_box_to_source(v,tile)
        assert b[0]>=0 and b[1]>=0 and b[2]<=128+1e-9 and b[3]<=96+1e-9
    spec=read_json(fixtures/'large-plan.json');spec['memory_budget_bytes']=1
    with pytest.raises(ValueError):plan_large_image(spec)

@pytest.mark.parametrize('expression,expected',[
    ({'field':'domain','op':'eq','value':'arid'},True),
    ({'not':{'field':'missing','op':'eq','value':2}},None),
    ({'all':[{'field':'domain','op':'eq','value':'arid'},{'field':'missing','op':'gt','value':1}]},None),
    ({'any':[{'field':'domain','op':'eq','value':'arid'},{'field':'missing','op':'gt','value':1}]},True)])
def test_slice_unknown_semantics(expression,expected):
    from cvsubstrate.analysis.slices import matches
    assert matches({'domain':'arid'},{'name':'filter','expression':expression,'metadata_origin':'test'}) is expected

def test_slice_rejects_code():
    from cvsubstrate.analysis.slices import validate_expression
    with pytest.raises(ValueError):validate_expression({'field':'__class__','op':'eq','value':'x'})
    with pytest.raises(ValueError):validate_expression({'python':'__import__("os")'})

def test_size_metrics_support(fixtures):
    from cvsubstrate.evaluation.object_size import size_metrics
    from cvsubstrate.contracts.models import DatasetManifest,DetectionPrediction
    from cvsubstrate.provenance.io import read_jsonl
    m=DatasetManifest.model_validate(read_json(fixtures/'base/dataset.json'));rows=[DetectionPrediction.model_validate(r) for r in read_jsonl(fixtures/'fixture-predictions.jsonl')]
    r=size_metrics(m,'dev',rows,read_json(fixtures/'size-policy.json'));assert r['kind']=='SIZE_DIAGNOSTICS_NOT_OFFICIAL_AP'

def test_synthetic_missing_and_zero(fixtures):
    from cvsubstrate.data.simulator_sdk import import_export
    import_export(fixtures/'synthetic-raw.json',read_json(fixtures/'synthetic-mapping.json'),fixtures/'sidecar.json');r=read_json(fixtures/'sidecar.json')
    assert r['illumination']['sun_elevation']['value']==0;assert r['weather']['visibility']['status']=='unknown'
    assert r['scene']['altitude']['value']==123;assert r['scene']['altitude']['status']=='derived'

def test_dsl_plans_and_budget_conflicts(fixtures):
    from cvsubstrate.campaigns.dsl import compile_campaign
    c=read_json(fixtures/'campaign.json');r=compile_campaign(c,fixtures);assert len(r['cases'])==6
    assert all(case['stages'][0]['experiment']['training']['real_per_update']>=1 for case in r['cases'])
    c['constraints']=[{'metric':'real_exposures','arms':['R','Rreplay']}]
    with pytest.raises(CVRSError):compile_campaign(c,fixtures)

def test_fresh_seed_contract(fixtures):
    from cvsubstrate.contracts.groundwork import ResearchCampaign
    c=read_json(fixtures/'campaign.json');c.update(phase='confirmatory',previous_seeds=[7],seeds=[7,8,9],selection_digest='0'*64)
    with pytest.raises(ValueError):ResearchCampaign.model_validate(c)

def test_sweep_unique_deterministic(fixtures):
    from cvsubstrate.campaigns.dsl import expand_sweep
    c=read_json(fixtures/'campaign.json');r=expand_sweep(c,{'/seeds':[[3],[5]]},fixtures/'sweep');assert r['count']==2;assert len({x['digest'] for x in r['cases']})==2

def test_benchmark_version_immutable(fixtures):
    from cvsubstrate.benchmarks.registry import register_benchmark,list_benchmarks
    b=read_json(fixtures/'benchmark.json');reg=fixtures/'registry';a=register_benchmark(b,reg);register_benchmark(b,reg);assert len(list_benchmarks(reg))==1
    b['tiling']={'changed':True}
    with pytest.raises(CVRSError):register_benchmark(b,reg)

def test_environment_parser(tmp_path):
    from cvsubstrate.environments.capture import import_environment
    p=tmp_path/'requirements';p.write_text('package==1.2\nother>=2\n')
    e=import_environment(p,'pip');assert len(e.packages)==1 and e.unresolved
    p.write_text('image@sha256:'+'a'*64);assert import_environment(p,'docker').container_digest

def test_plugin_registry_metadata_not_execution(tmp_path):
    from cvsubstrate.adapters.sdk import PluginRegistry
    from cvsubstrate.contracts.groundwork import PluginDescriptor
    reg=PluginRegistry(tmp_path/'registry.json');reg.register(PluginDescriptor(id='external',kind='dataset',target='not_installed:Plugin',operations=['read']))
    assert reg.inspect('external')['metadata_only']
    with pytest.raises(CVRSError):reg.load('external')

def test_capability_conflict():
    from cvsubstrate.adapters.sdk import negotiate
    from cvsubstrate.contracts.groundwork import CapabilityRequirement
    req=CapabilityRequirement(task='obb_detection',operation='predict',input_format='images',output_format='polygons')
    assert negotiate(req,model={'tasks':['hbb_detection']},dataset={'tasks':['obb_detection']})['status']=='UNSATISFIABLE'

def test_unsafe_checkpoint_trust_spec():
    from cvsubstrate.contracts.groundwork import CheckpointDescriptor
    from cvsubstrate.checkpoints import inspect_checkpoint
    spec=CheckpointDescriptor(source_framework='test',architecture='test',path='x',sha256='a'*64,serialization='trusted_pickle')
    # Metadata may describe an untrusted file; execution must refuse BEFORE loading it.
    assert not spec.trust_legacy_pickle
    with pytest.raises(CVRSError,match='CHECKPOINT_TRUST'):
        inspect_checkpoint(spec.model_dump(mode='json'),timeout=10)

def test_secret_redaction():
    from cvsubstrate.security import sanitize
    value=sanitize({'api_key':'abc','url':'https://example.test/a?token=secret','authorization':'Bearer secret'})
    assert 'secret' not in json.dumps(value) and 'abc' not in json.dumps(value)

def test_modern_missing_dep_response():
    from cvsubstrate.execution.services import invoke_service
    r=invoke_service('ultralytics',{'operation':'capabilities'},timeout=30)
    assert r['adapter']=='ultralytics' and not r['execution_verified_in_this_process']

def test_cli_public_help():
    from cvsubstrate.cli_groundwork import parser,ROOTS
    text=parser().format_help();assert 'schema' in text and 'benchmark' in text

@pytest.mark.native
def test_torch_export_and_reload_same_tensor(fixtures):
    pytest.importorskip('torch');pytest.importorskip('numpy')
    from cvsubstrate.deployment.service import execute_deployment
    from cvsubstrate.deployment.compare import compare_arrays
    d=read_json(fixtures/'deployment.json');execute_deployment(d,fixtures/'export',operation='export',timeout=45)
    execute_deployment(d,fixtures/'native',operation='infer',timeout=45)
    p=fixtures/'export/model.pt2';d.update(model_path=str(p),model_sha256=file_digest(p))
    execute_deployment(d,fixtures/'exported-inference',operation='infer',timeout=45)
    assert compare_arrays(fixtures/'native',fixtures/'exported-inference')['status']=='WITHIN_TOLERANCE'

@pytest.mark.native
def test_checkpoint_key_conversion(fixtures):
    torch=pytest.importorskip('torch')
    from cvsubstrate.checkpoints import convert_checkpoint,inspect_checkpoint
    path=fixtures/'weights.pth';torch.save({'old':torch.arange(4)},path)
    source={'source_framework':'fixture','architecture':'one_tensor','path':str(path),'sha256':file_digest(path)}
    assert 'old' in inspect_checkpoint(source)['tensors']
    result=convert_checkpoint({'source':source,'destination_framework':'fixture','destination_architecture':'renamed','parameter_mapping':{'old':'new'},'destination_shapes':{'new':[4]}},fixtures/'converted')
    assert result['tensor_roundtrip_exact'] and result['model_output_parity']=='NOT_EXECUTED'


def test_graph_named_output_reference(tmp_path):
    from cvsubstrate.experiments.dag import execute_graph,register_action,ACTIONS
    from cvsubstrate.contracts.groundwork import ExecutionGraph
    def handler(inputs,params,out):
        (out/'actual-name').write_text('named value')
        return {'outputs':{'friendly':'actual-name'}}
    if 'test.named' not in ACTIONS:register_action('test.named',handler)
    g=ExecutionGraph(name='named',nodes=[{'id':'a','action':'test.named'},{'id':'b','action':'artifact.copy','inputs':{'artifact':{'node':'a','artifact':'friendly'}}}])
    result=execute_graph(g,tmp_path/'graph');assert result['status']=='SUCCEEDED'
    assert (tmp_path/'graph'/result['nodes']['b']['directory']/'artifact').read_text()=='named value'


def test_wizard_preserves_unresolved_environment(fixtures):
    from cvsubstrate.heritage.wizard import import_wizard
    source=fixtures/'legacy-source';source.mkdir();(source/'base.py').write_text('model=dict(type="TOOD")\n');(source/'config.py').write_text('_base_="base.py"\n')
    ck=fixtures/'dummy.pth';ck.write_bytes(b'not-a-model; no loading is authorized')
    out=fixtures/'heritage'
    result=import_wizard(config=source/'config.py',source_root=source,checkpoint=ck,dataset=fixtures/'base/dataset.json',output=out,profile='mmdet3',revision='fixture-only',category_map={'0':3,'1':17})
    assert not result['execution_verified'] and result['environment']=='UNRESOLVED'
    assert not read_json(out/'experiment.json')['adapter']['config']['trust_executable_config']


def test_obb_service_capabilities_no_model():
    from cvsubstrate.execution.services import invoke_service
    r=invoke_service('ultralytics_obb',{'operation':'capabilities'},timeout=10)
    assert r['tasks']==['obb_detection'] and not r['execution_verified']
