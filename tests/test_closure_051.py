"""Engineering conformance for finite v1 closure; no external model certification."""
from pathlib import Path
import json,sys,time,threading,sqlite3
import pytest
from cvsubstrate.provenance.io import digest,file_digest,write_json,read_json
from cvsubstrate.errors import CVRSError
from cvsubstrate.contracts.frontier import MaskRLE

H='1'*64

def test_v1_facade_and_schemas():
    import cvsubstrate.v1 as v1
    from cvsubstrate.schemas.registry import schema_registry
    reg=schema_registry();assert len(reg)>=107
    for cls in reg.values():assert cls.model_json_schema()
    assert v1.content_id('model',{'a':1})!=v1.content_id('dataset',{'a':1})
    assert v1.content_id('model',{'a':1,'b':2})==v1.content_id('model',{'b':2,'a':1})
    with pytest.raises(ValueError):v1.content_id('unknown',{})

def test_provenance_cycle_and_stable_order():
    from cvsubstrate.foundation.identity import ProvenanceGraph
    nodes=[{'id':'a','kind':'dataset','content_sha256':H},{'id':'b','kind':'run','content_sha256':H}]
    edge={'source':'b','target':'a','relation':'uses'}
    g=ProvenanceGraph(nodes=nodes,edges=[edge]);assert g.ancestors('b')==['a']
    assert g.identity==ProvenanceGraph(nodes=nodes[::-1],edges=[edge]).identity
    with pytest.raises(ValueError):ProvenanceGraph(nodes=nodes,edges=[edge,{'source':'a','target':'b','relation':'uses'}])

def test_cas_gc_pins_and_fresh_plan(tmp_path):
    from cvsubstrate.artifacts.managed import ManagedArtifactStore
    s=ManagedArtifactStore(tmp_path/'cas');a=tmp_path/'a';a.write_text('alpha');ref=s.put(a,pin='experiment')
    assert s.gc(minimum_age_seconds=0)['objects']==0
    s.unpin('experiment');plan=s.gc(minimum_age_seconds=0);assert plan['objects']==1
    with pytest.raises(CVRSError):s.gc(minimum_age_seconds=0,dry_run=False,plan_digest=H)
    s.gc(minimum_age_seconds=0,dry_run=False,plan_digest=plan['plan_digest']);assert not s.exists(ref.sha256)

def test_dependency_closure(tmp_path):
    from cvsubstrate.artifacts.dependencies import DependencyClosure,inspect_closure
    p=tmp_path/'w';p.write_text('weights')
    c=DependencyClosure(dependencies=[{'id':'weights','sha256':file_digest(p),'disposition':'EXTERNAL_REQUIRED'},{'id':'notes','sha256':H,'disposition':'OPTIONAL'}])
    assert not inspect_closure(c,tmp_path)['ready']
    assert inspect_closure(c,tmp_path,{'weights':str(p)})['ready']
    with pytest.raises(ValueError):DependencyClosure(dependencies=[{'id':'a','sha256':H,'disposition':'OPTIONAL','depends_on':['a']}])

@pytest.mark.parametrize('target',['SUCCEEDED','FAILED','CANCELLED'])
def test_lifecycle(target):
    from cvsubstrate.foundation.lifecycle import transition
    assert transition('RUNNING',target)==target
    with pytest.raises(CVRSError):transition('PENDING','SUCCEEDED')

def test_session_roundtrip_heartbeats():
    from cvsubstrate.execution.session import run_session
    code="from cvsubstrate.execution.session_runtime import serve; import time; serve(lambda p,c: (time.sleep(.15), {'value':p['x']})[1],heartbeat_interval=.02)"
    events=[];r=run_session([sys.executable,'-c',code],{'x':42},timeout=5,heartbeat_timeout=2,event_handler=events.append)
    assert r['result']=={'value':42};assert any(e['type']=='heartbeat' for e in events)

def test_session_cancel():
    from cvsubstrate.execution.session import run_session
    from cvsubstrate.foundation.lifecycle import CancellationToken,Cancelled
    code="from cvsubstrate.execution.session_runtime import serve; import time; serve(lambda p,c: (time.sleep(10), {})[1],heartbeat_interval=.01)"
    t=CancellationToken();timer=threading.Timer(.2,t.cancel);timer.start()
    try:
        with pytest.raises(Cancelled):run_session([sys.executable,'-c',code],{},timeout=5,cancel=t)
    finally:timer.cancel()

def test_config_closure_no_execution(tmp_path):
    from cvsubstrate.heritage.closure import config_closure,preserve_closure
    (tmp_path/'base.py').write_text('classes=("car",)\n')
    (tmp_path/'config.py').write_text('_base_="base.py"\nimport os\nx=os.getenv("DATA_ROOT")\n')
    result=config_closure(tmp_path/'config.py',tmp_path,environment_names=['DATA_ROOT'],environment_values={'DATA_ROOT':'/private/location'})
    text=json.dumps(result);assert 'base.py' in text and '/private/location' not in text
    preserve_closure(tmp_path/'config.py',tmp_path,tmp_path/'preserved',environment_names=['DATA_ROOT'],environment_values={'DATA_ROOT':'/private/location'})

def test_distributed_telemetry(tmp_path):
    from cvsubstrate.worker_shims.telemetry_runtime import TrainingLedger
    from cvsubstrate.telemetry_v1 import aggregate_ranks
    files=[]
    for rank in range(2):
        p=tmp_path/f'rank{rank}.db';ledger=TrainingLedger(p,run_id='x',rank=rank,world_size=2,source_map={'1':'real'},mixing_policy='disabled_or_fully_traced')
        ledger.batch(['1'],parent_ids=[['parent']]);ledger.loss({'loss':1.0},[.01]);ledger.optimizer();ledger.close();files.append(p)
    result=aggregate_ranks(files,2);assert result['synchronized_optimizer_steps']==1;assert result['source_exposures']['real']==2
    assert result['cross_rank_sample_overlap']==['1'];assert not result['all_reduce_execution_verified']
    with pytest.raises(ValueError):aggregate_ranks(files[:1],2)

@pytest.mark.parametrize('dx,dy,sx,sy',[(0,0,1.,1.),(2,1,1.,1.),(-1,-1,1.,1.),(1,2,2.,3.),(0,0,.5,.5),(1.2,.8,1.3,.7)])
def test_sparse_mask_place_matches_center_sampling(dx,dy,sx,sy):
    pytest.importorskip('numpy')
    import numpy as np
    from cvsubstrate.vision.masks import encode_mask,decode_mask
    from cvsubstrate.vision.sparse_masks import place
    a=np.array([[1,0,0],[0,1,0],[1,1,0]],dtype=bool);out=place(encode_mask(a),width=10,height=10,x=dx,y=dy,scale_x=sx,scale_y=sy)
    expected=np.zeros((10,10),dtype=bool)
    for yy in range(10):
        for xx in range(10):
            x=int(__import__('math').floor((xx+.5-dx)/sx));y=int(__import__('math').floor((yy+.5-dy)/sy))
            if 0<=x<3 and 0<=y<3:expected[yy,xx]=a[y,x]
    assert np.array_equal(decode_mask(out),expected)

def test_sparse_union_and_polygon_interchange():
    pytest.importorskip('numpy')
    import numpy as np
    from cvsubstrate.vision.masks import encode_mask,decode_mask
    from cvsubstrate.vision.sparse_masks import union,mask_to_polygons,polygon_to_mask
    a=np.zeros((8,9),dtype=bool);a[1:7,1:8]=True;a[3:5,3:5]=False
    m=encode_mask(a);polys=mask_to_polygons(m);assert np.array_equal(decode_mask(polygon_to_mask(polys,width=9,height=8)),a)
    assert union([m,m])==m

def test_band_contract_and_lineage():
    pytest.importorskip('numpy')
    import numpy as np
    from cvsubstrate.datasets.sensors import SensorSpec,normalize_bands
    from cvsubstrate.data.asset_lineage import AssetLineage,check_asset_leakage
    sensor=SensorSpec(id='n',kind='multispectral',bands=[{'name':'nir','index':1,'meaning':'NIR','units':'reflectance','normalization':'range','minimum':0.0,'maximum':100.0,'nodata':-1.0}],model_channel_names=['nir'])
    x,v=normalize_bands(np.array([[[50,-1]]]),np.ones((1,2),dtype=bool),sensor);assert x[0,0,0]==.5 and not v[0,1] and x[0,0,1]==0
    graph=AssetLineage(assets=[{'id':'mesh','kind':'vehicle_mesh'},{'id':'scene','kind':'scene','parents':['mesh']}],samples=[{'sample_id':'train','split':'train','asset_ids':['scene']},{'sample_id':'test','split':'locked_test','asset_ids':['mesh']}])
    result=check_asset_leakage(graph);assert result['status']=='CONFLICT'

def test_stream_obb_and_masks_resume(tmp_path):
    pytest.importorskip('numpy')
    pytest.importorskip('rasterio')
    import numpy as np,rasterio
    from rasterio.transform import from_origin
    from cvsubstrate.streaming.raster import StreamSpec
    from cvsubstrate.streaming.tasks import execute_task_stream
    from cvsubstrate.vision.masks import encode_mask
    raster=tmp_path/'image.tif'
    with rasterio.open(raster,'w',driver='GTiff',width=12,height=12,count=3,dtype='uint8',transform=from_origin(0,12,1,1)) as ds:ds.write(np.zeros((3,12,12),dtype='uint8'))
    spec=StreamSpec(str(raster),file_digest(raster),tile_width=8,tile_height=8,overlap=4,model_identity=H,max_detections_per_tile=2)
    def obb(images):
        return [[{'score':.9,'category_id':1,'polygon':[[0.,0.],[float(i.shape[1]),0.],[float(i.shape[1]),float(i.shape[0])],[0.,float(i.shape[0])]]}] for i in images]
    partial=execute_task_stream(spec,obb,tmp_path/'obb',task='obb',max_tiles=1);assert partial['status']=='PAUSED'
    completed=execute_task_stream(spec,obb,tmp_path/'obb',task='obb',resume=True);assert completed['status']=='COMPLETE' and completed['reused_tiles']==1
    from cvsubstrate.contracts.research import OrientedPrediction
    from cvsubstrate.provenance.io import read_jsonl
    OrientedPrediction.model_validate(read_jsonl(tmp_path/'obb'/completed['canonical_predictions'])[0])
    def masks(images):return [[{'score':.8,'category_id':1,'mask':encode_mask(np.ones(i.shape[:2],dtype=bool)).model_dump(mode='json')}] for i in images]
    value=execute_task_stream(spec,masks,tmp_path/'masks',task='masks',mask_policy='union');assert value['selected_instances']>0
    from cvsubstrate.contracts.frontier import MaskPrediction
    MaskPrediction.model_validate(read_jsonl(tmp_path/'masks'/value['canonical_predictions'])[0])
    artifact=tmp_path/'masks'/value['predictions'];artifact.write_text('tampered\n')
    with pytest.raises(ValueError,match='OUTPUT_CHANGED'):execute_task_stream(spec,masks,tmp_path/'masks',task='masks',resume=True,mask_policy='union')

def test_prompt_sets_and_ontology():
    from cvsubstrate.vision.prompts import PromptSet,negotiate_prompts
    from cvsubstrate.vision.ontology import ConceptOntology,evaluate_open_set
    p=PromptSet(id='set',sample_id='im',width=5,height=5,prompts=[{'id':'p','kind':'box','box':[0.,0.,3.,3.],'source':'ORACLE'}])
    assert negotiate_prompts('sam2',[p])['oracle_conditioned']
    assert not negotiate_prompts('hf_grounding_dino',[p])['satisfiable']
    ontology=ConceptOntology(name='tax',concepts=[{'id':'car','name':'car','aliases':['automobile']},{'id':'alien','name':'alien','partition':'unknown'}])
    pred=[{'id':'p','sample_id':'im','box':[0.,0.,3.,3.],'score':.9,'phrase':'automobile'}]
    gt=[{'sample_id':'im','box':[0.,0.,3.,3.],'concept_id':'car'}]
    result=evaluate_open_set(pred,gt,ontology);assert result['partitions']['known']['recall']==1
    with pytest.raises(ValueError):evaluate_open_set([{**pred[0],'score':float('nan')}],gt,ontology)

def test_native_campaign_budget_compile():
    from cvsubstrate.campaigns.native import NativeCampaign,compile_native_campaign
    c={'id':'x','stages':[{'id':'s','backend':'mmdet3','budget_unit':'optimizer_updates','budget':2,'dataset_sha256':H,'source':'synthetic','job':{},'checkpoint_output':'training/iter_2.pth'},{'id':'r','backend':'mmdet3','budget_unit':'optimizer_updates','budget':2,'dataset_sha256':H,'source':'real','job':{},'initialized_from':'s','checkpoint_output':'training/iter_2.pth'}],'seeds':[1,2]}
    assert compile_native_campaign(c)['executable']
    c['equality_requirements']=['real_exposures'];assert not compile_native_campaign(c)['executable']
    c['stages'][0]['backend']='ultralytics'
    with pytest.raises(ValueError):NativeCampaign.model_validate(c)

def claim():
    from cvsubstrate.research.claims import ScientificClaim
    return ScientificClaim(title='synthetic effect',population='arid',dataset_sha256=H,split='dev',intervention={'arm':'R+S'},comparator={'arm':'R'},metric='recall',direction='greater',protocol_sha256=H,author_id='author',purpose='software_fixture')

def test_registry_signed_merge_and_independence(tmp_path):
    pytest.importorskip('cryptography')
    from cvsubstrate.research.federated import FederatedRegistry
    from cvsubstrate.research.signing import keygen
    key=keygen(tmp_path/'key.pem',allow_unencrypted=True)
    c=claim()
    with FederatedRegistry(tmp_path/'base') as base:
        cid=base.add('claim',c.model_dump(mode='json'));base.sign_record(cid,tmp_path/'key.pem');base.exchange(tmp_path/'base-pack',signing_key=tmp_path/'key.pem')
    for name in ['left','right']:
        with FederatedRegistry(tmp_path/name) as reg:
            reg.merge(tmp_path/'base-pack',trusted_keys=[key['key_id']],require_signature=True)
            reg.add('actor',{'id':name,'display_name':name})
            reg.exchange(tmp_path/(name+'-pack'))
    with FederatedRegistry(tmp_path/'left') as reg:
        reg.merge(tmp_path/'right-pack');assert reg.verify()['records']==3
        before=reg.verify()['root_digest'];reg.merge(tmp_path/'right-pack');assert reg.verify()['root_digest']==before
        assert reg.status(cid)['level']=='R0';assert reg.search(kind='claim',filters={'metric':'recall'})
        site=reg.export_site(tmp_path/'site');assert site['pages']==4
        reg.db.execute('DELETE FROM records WHERE id=?',(cid,))
        with pytest.raises(Exception):reg.verify()

def test_registry_combined_cycle_rejected(tmp_path):
    from cvsubstrate.research.federated import FederatedRegistry
    with FederatedRegistry(tmp_path/'base') as reg:
        a=reg.add('claim',claim().model_dump(mode='json'));c=claim();c.title='other';b=reg.add('claim',c.model_dump(mode='json'));reg.exchange(tmp_path/'base-pack')
    for name,left,right in [('x',a,b),('y',b,a)]:
        with FederatedRegistry(tmp_path/name) as reg:
            reg.merge(tmp_path/'base-pack');reg.add_edge({'source':left,'target':right,'relation':'supersedes'});reg.exchange(tmp_path/(name+'-pack'))
    with FederatedRegistry(tmp_path/'x') as reg:
        before=reg.verify()['root_digest']
        with pytest.raises(ValueError,match='cycle'):reg.merge(tmp_path/'y-pack')
        assert reg.verify()['root_digest']==before

def test_effect_assertions_and_no_self_reproduction(tmp_path):
    from cvsubstrate.research.claims import EffectObservation,EvidenceAttempt
    from cvsubstrate.research.federated import FederatedRegistry
    c=claim();effect=EffectObservation(metric='recall',baseline=.4,treatment=.5)
    assert effect.assess(c)['assertion']=='SUPPORTED' and effect.assess(c)['strength']=='POINT_ESTIMATE_ONLY'
    with FederatedRegistry(tmp_path/'reg') as reg:
        cid=reg.add('claim',c.model_dump(mode='json'))
        execution=reg.add_json({'status':'SUCCEEDED','run_id':'original','scope_fingerprint':c.scope_fingerprint})
        evaluation=reg.add_json({'run_id':'original','metric':'recall','effect_digest':digest(effect)})
        base=dict(claim_id=cid,actor_id='author',machine_id='machine',environment_sha256=H,implementation_id='impl',scope_fingerprint=c.scope_fingerprint,outcome='completed',effect=effect,evidence={'execution':execution,'evaluation':evaluation},purpose='software_fixture')
        for role in ['original','reproduction']:reg.add('attempt',EvidenceAttempt(role=role,**base).model_dump(mode='json'))
        assert reg.status(cid)['level']=='R1'

def test_concurrent_registry_writers(tmp_path):
    from cvsubstrate.research.federated import FederatedRegistry
    with FederatedRegistry(tmp_path/'reg'):pass
    errors=[]
    def writer(i):
        try:
            with FederatedRegistry(tmp_path/'reg') as reg:reg.add('actor',{'id':'actor'+str(i),'display_name':'actor'})
        except Exception as e:errors.append(e)
    ts=[threading.Thread(target=writer,args=(i,)) for i in range(8)]
    for t in ts:t.start()
    for t in ts:t.join()
    assert not errors
    with FederatedRegistry(tmp_path/'reg') as reg:assert reg.verify()['records']==8

def test_cli_policy_and_missing_asset(tmp_path):
    import subprocess,os
    p=subprocess.run([sys.executable,'-m','cvsubstrate','closure','policy'],capture_output=True,text=True);assert p.returncode==0;assert json.loads(p.stdout)['policy_version']=='1.0'
    p=subprocess.run([sys.executable,'-m','cvsubstrate','closure','identity','model',str(tmp_path/'missing')],capture_output=True,text=True);assert p.returncode==2;assert json.loads(p.stderr)['error']['code']=='ARTIFACT_MISSING'

def test_exact_legacy_compatibility():
    from cvsubstrate.foundation.compatibility import inspect_compatibility
    root=Path(__file__).parent/'compat'/'v0.5.0a1'
    report=inspect_compatibility(root/'manifest.json',root)
    assert len(report['historical_readers'])==6

def test_capsule_dependency_manifest(tmp_path):
    from cvsubstrate.artifacts.capsule import create_capsule,validate_capsule
    source=tmp_path/'src';source.mkdir();(source/'model.json').write_text('{"x":1}')
    closure={'dependencies':[{'id':'model','sha256':file_digest(source/'model.json'),'disposition':'EMBEDDED','path':'model.json'},
                             {'id':'external','sha256':H,'disposition':'RESTRICTED'}]}
    created=create_capsule(source,tmp_path/'capsule',dependency_closure=closure)
    assert not created['dependency_closure']['ready']
    assert validate_capsule(tmp_path/'capsule')['dependency_closure']['dependencies'][0]['status']=='VERIFIED'

def test_native_coco_binding(tmp_path):
    from cvsubstrate.data.fixtures import generate
    from cvsubstrate.heritage.native_data import bind_coco_training
    from cvsubstrate.contracts.models import DatasetManifest
    from types import SimpleNamespace
    generate(tmp_path/'data');manifest=DatasetManifest.model_validate(read_json(tmp_path/'data/dataset.json'))
    train=next(k for k,s in manifest.splits.items() if s.role=='train')
    cfg=SimpleNamespace(data=type('AttrDict',(dict,),{'__getattr__':dict.__getitem__,'__setattr__':dict.__setitem__})(train={'type':'CocoDataset','pipeline':[]},val={'type':'CocoDataset','pipeline':[]}))
    receipt=bind_coco_training(cfg,{'dataset_manifest':str(tmp_path/'data/dataset.json'),'dataset_sha256':digest(manifest),'train_split':train,'eval_split':'dev','category_map':{str(i):c.id for i,c in enumerate(manifest.categories)},'source':'real'},tmp_path/'bound','mmdet2')
    assert receipt['source_map'] and Path(cfg.data.train['ann_file']).exists()
    assert read_json(Path(cfg.data.train['ann_file']))['info']['cvrs_dataset_sha256']==digest(manifest)

def test_prompt_corrections_share_native_object():
    from cvsubstrate.vision.prompts import PromptSet,native_prompt_groups,legacy_prompts
    from cvsubstrate.worker_shims.vision_drivers import grouped_prompts
    p=PromptSet(id='x',sample_id='im',width=10,height=10,prompts=[{'id':'a','kind':'points','target_id':'car','source':'NON_ORACLE','points':[[1.,1.]],'labels':[1]},
        {'id':'b','kind':'points','target_id':'car','source':'NON_ORACLE','points':[[8.,8.]],'labels':[0]}])
    groups=grouped_prompts(legacy_prompts(p,Path('.')),native_prompt_groups(p))
    assert len(groups)==1 and len(groups[0][1])==2

def test_declared_budget_mismatch_rejected():
    from cvsubstrate.campaigns.native import compile_native_campaign
    stages=[{'id':n,'backend':'mmdet3','budget_unit':'optimizer_updates','budget':b,'dataset_sha256':H,'source':'real','job':{},'checkpoint_output':'x.pth'} for n,b in [('a',2),('b',3)]]
    assert not compile_native_campaign({'id':'x','stages':stages,'seeds':[1],'equality_requirements':['optimizer_updates']})['executable']

def test_population_and_grounded_reevaluation(tmp_path):
    from cvsubstrate.contracts.frontier import GroundedPrediction,PromptSpec
    from cvsubstrate.provenance.io import write_jsonl
    from cvsubstrate.research.evaluators import reevaluate_task
    images=[{'id':'a','width':10,'height':10,'domain':'arid'},{'id':'b','width':10,'height':10,'domain':'urban'}]
    dataset={'images':images,'annotations':[{'sample_id':'a','box':[1.,1.,4.,4.],'concept_id':'car'}]}
    rows=[GroundedPrediction(sample_id=i['id'],width=10,height=10,prompt=PromptSpec(id='p'+i['id'],sample_id=i['id'],kind='text',text='car',source='ground_truth_oracle'),boxes=[[1.,1.,4.,4.]] if i['id']=='a' else [],scores=[.9] if i['id']=='a' else [],phrases=['car'] if i['id']=='a' else [],native_output_sha256=H).model_dump(mode='json') for i in images]
    write_json(tmp_path/'data.json',dataset);write_jsonl(tmp_path/'predictions.jsonl',rows)
    write_json(tmp_path/'protocol.json',{'ontology':{'name':'o','concepts':[{'id':'car','name':'car'}]}})
    r=reevaluate_task({'task':'grounding','dataset':str(tmp_path/'data.json'),'predictions':str(tmp_path/'predictions.jsonl'),'protocol':str(tmp_path/'protocol.json'),'purpose':'software_fixture'},tmp_path/'evaluation')
    assert r['result']['oracle_conditioned'] and r['result']['partitions']['known']['recall']==1


def test_native_optimizer_learning_rates(tmp_path):
    pytest.importorskip('torch')
    import torch,json
    from cvsubstrate.worker_shims.telemetry_runtime import TrainingLedger,observe_optimizer
    p=torch.nn.Parameter(torch.tensor(1.));o=torch.optim.SGD([p],lr=.125)
    ledger=TrainingLedger(tmp_path/'lr.sqlite',run_id='lr')
    with observe_optimizer(o,ledger):
        p.grad=torch.tensor(.5);o.step()
    steps=[json.loads(x[0]) for x in ledger.db.execute('SELECT payload FROM events') if json.loads(x[0])['kind']=='OPTIMIZER_STEP']
    assert steps[0]['data']['learning_rates']==[.125]
    ledger.close()


def test_session_delegates_real_native_capabilities():
    pytest.importorskip("torch")
    from cvsubstrate.execution.session import run_session
    from cvsubstrate.contracts.models import WorkerRequest
    result=run_session([sys.executable,'-m','cvsubstrate.execution.session_runtime'],
                      {'adapter':'native_torch','worker_python':sys.executable,'request':WorkerRequest(operation='capabilities').model_dump(mode='json')},
                      timeout=60,heartbeat_timeout=20)
    assert result['result']['status']=='SUCCEEDED'
    assert result['result']['result']['installed'] is True


def test_bound_multitask_final_access(tmp_path):
    from cvsubstrate.research.task_access import authorize_task_evaluation,consume_task_authorization
    from cvsubstrate.provenance.io import write_json
    spec={'task':'mask_diagnostics','dataset':str(tmp_path/'data.json'),'predictions':str(tmp_path/'pred.jsonl'),'protocol':str(tmp_path/'protocol.json'),'split':'locked_test'}
    for key in ('dataset','predictions','protocol'):write_json(Path(spec[key]),{'kind':key})
    approved=authorize_task_evaluation(spec,tmp_path/'access.jsonl',approved_by='owner',reason='Frozen final comparison')
    spec['authorization']={k:approved[k] for k in ('ledger','approval_digest')}
    access=consume_task_authorization(spec);assert access['approval']['max_uses']==1
    with pytest.raises(Exception):consume_task_authorization(spec)
    spec['protocol']=str(tmp_path/'other.json');write_json(tmp_path/'other.json',{})
    with pytest.raises(Exception):consume_task_authorization(spec)
