"""Finite v1 closure demonstration, CPU/local/generated assets only.

Run after installing native, geo and signing extras:
    python tools/smoke_closure.py /new/output/path

This is engineering evidence, not real aerial or pretrained-model performance.
Private signing keys exist only in a temporary directory and are not packaged.
"""
from pathlib import Path
import json,sys,tempfile,os
from cvsubstrate.provenance.io import read_json,read_jsonl,write_json,write_jsonl,digest,file_digest
from cvsubstrate.provenance.artifact_set import verify_directory,seal_directory


def run(out):
    import torch,numpy as np,rasterio
    from rasterio.transform import from_origin
    from cvsubstrate.vision.native_mask import build_mask_detector
    from cvsubstrate.vision.masks import encode_mask
    from cvsubstrate.worker_shims.telemetry_runtime import TrainingLedger,observe_optimizer
    from cvsubstrate.execution.services import invoke_service
    out=Path(out).resolve()
    if out.exists():raise ValueError('use a fresh smoke directory')
    out.mkdir(parents=True);torch.set_num_threads(1);torch.manual_seed(83)
    summary={'version':'0.5.1a1','purpose':'software_fixture','pretrained_models':False,'gpu_used':False,'paid_compute':False}
    def record(key,value):summary[key]=value;write_json(out/'summary-in-progress.json',summary)
    # Session protocol 2 delegates to the existing real native worker protocol 1.
    from cvsubstrate.execution.session import run_session
    from cvsubstrate.contracts.models import WorkerRequest
    session=run_session([sys.executable,'-m','cvsubstrate.execution.session_runtime'],
        {'adapter':'native_torch','worker_python':sys.executable,'request':WorkerRequest(operation='capabilities').model_dump(mode='json')},timeout=60,heartbeat_timeout=20)
    record('protocol2_real_native_handshake',session)
    # True model training, including actual native loss and optimizer observations.
    model=build_mask_detector(2);optimizer=torch.optim.SGD(model.parameters(),lr=.001)
    image=torch.zeros((3,64,80));image[:,18:45,20:50]=.65
    target={'boxes':torch.tensor([[20.,18.,50.,45.]]),'labels':torch.tensor([1]),'masks':torch.zeros((1,64,80),dtype=torch.uint8)}
    target['masks'][0,18:45,20:50]=1
    old={k:v.detach().clone() for k,v in model.state_dict().items()}
    ledger=TrainingLedger(out/'rank0.sqlite',run_id='closure-native-mask',rank=0,world_size=1,source_map={'im':'synthetic'},mixing_policy='disabled_or_fully_traced')
    with observe_optimizer(optimizer,ledger):
        model.train();ledger.batch(['im'],parent_ids=[['procedural-parent']],augmentation={'method':'none'})
        losses=model([image],[target]);ledger.loss(losses,[.001]);sum(losses.values()).backward();optimizer.step()
    weights=out/'mask.pt';torch.save(model.state_dict(),weights);ledger.checkpoint(weights,step=1);ledger.close()
    from cvsubstrate.telemetry_v1 import aggregate_ranks
    record('native_training',{'changed_parameters':any(not torch.equal(old[k],v) for k,v in model.state_dict().items()),'telemetry':aggregate_ranks([out/'rank0.sqlite'],1)})
    raster=out/'scene.tif'
    with rasterio.open(raster,'w',driver='GTiff',width=80,height=64,count=3,dtype='uint8',crs='EPSG:32637',transform=from_origin(400000,2500000,.5,.5),tiled=True,blockxsize=16,blockysize=16) as ds:
        ds.write((image.numpy()*255).astype(np.uint8))
    spec={'raster':str(raster),'raster_sha256':file_digest(raster),'tile_width':48,'tile_height':48,'overlap':16,'scales':[1.0],'task':'masks','mask_policy':'union','sample_id':'scene',
          'model':{'backend':'torchvision_mask','checkpoint':str(weights),'checkpoint_sha256':file_digest(weights),'trust_checkpoint':True,'category_map':{'1':0},'cpu_threads':1,'mask_threshold':.25}}
    write_json(out/'stream-spec.json',spec)
    partial=invoke_service('task_stream',{'spec':spec,'output_dir':str(out/'mask-stream'),'max_tiles':1},timeout=180)
    complete=invoke_service('task_stream',{'spec':spec,'output_dir':str(out/'mask-stream'),'resume':True},timeout=180)
    assert complete['status']=='COMPLETE' and complete['reused_tiles']==1
    from cvsubstrate.contracts.frontier import MaskPrediction,MaskAnnotation
    predictions=out/'mask-stream'/complete['canonical_predictions'];parsed=MaskPrediction.model_validate(read_jsonl(predictions)[0])
    assert (parsed.width,parsed.height)==(80,64)
    assert len(parsed.instances)>0, 'low-threshold random model must exercise nonempty native masks in this fixture'
    record('mask_stream',{'partial':partial,'complete':complete,'canonical_instances':len(parsed.instances)})
    # A reference-shaped diagnostic analysis of actual model output, without model execution.
    mask=encode_mask(target['masks'][0].numpy().astype(bool))
    write_json(out/'mask-dataset.json',{'images':[{'id':'scene','width':80,'height':64,'domain':'procedural'}],'annotations':[MaskAnnotation(sample_id='scene',instance_id='gt',mask=mask,category_id=0).model_dump(mode='json')],'categories':[{'id':0,'name':'fixture_object'}],'purpose':'software_fixture'})
    write_json(out/'mask-protocol.json',{'iou_threshold':.5,'boundary':True})
    from cvsubstrate.research.evaluators import reevaluate_task
    before=file_digest(predictions)
    analysis=reevaluate_task({'task':'mask_diagnostics','dataset':str(out/'mask-dataset.json'),'predictions':str(predictions),'protocol':str(out/'mask-protocol.json'),'purpose':'software_fixture'},out/'mask-analysis')
    assert not analysis['model_executed'] and before==file_digest(predictions)
    record('mask_artifact_reevaluation',analysis)
    # Real exact tensor transforms and a reversible explicit mapping.
    from cvsubstrate.heritage.checkpoint_v1 import transform_checkpoint,diff_checkpoints
    tiny=out/'tiny.pth';torch.save({'head.weight':torch.arange(16,dtype=torch.float32).reshape(4,4)},tiny)
    def desc(path):return {'source_framework':'owned-torch','architecture':'tensor-fixture','path':str(path),'sha256':file_digest(path)}
    transformed=transform_checkpoint(desc(tiny),{'rules':[{'source':'head.weight','operation':'rename','destination':'renamed.weight'},{'source':'head.weight','operation':'reshape','shape':[2,8]},{'source':'head.weight','operation':'cast','dtype':'float64'}]},out/'converted')
    restored=transform_checkpoint(desc(out/'converted/weights.pth'),{'rules':[{'source':'renamed.weight','operation':'rename','destination':'head.weight'},{'source':'renamed.weight','operation':'reshape','shape':[4,4]},{'source':'renamed.weight','operation':'cast','dtype':'float32'}]},out/'restored')
    difference=diff_checkpoints(desc(tiny),desc(out/'restored/weights.pth'));assert difference['structurally_identical']
    record('checkpoint_transforms',{'forward':transformed,'reverse':restored,'restored_exact':difference})
    # Two actual baseline/treatment execution pairs, original and same-machine rerun.
    from cvsubstrate.data.fixtures import generate
    from cvsubstrate.execution.runner import run_experiment
    generate(out/'fixtures')
    for name in ['real','supplement']:
        e=read_json(out/'fixtures'/(name+'.json'));e['training']['updates']=1;write_json(out/'fixtures'/(name+'.json'),e)
    runs=[]
    for role in ['original','reproduction']:
        pair=[]
        for name in ['real','supplement']:
            path=run_experiment(out/'fixtures'/(name+'.json'),out/'runs',timeout=180);pair.append(path)
        runs.append(pair);record(role+'_runs',[str(p.relative_to(out)) for p in pair])
    from cvsubstrate.research.claims import ScientificClaim
    from cvsubstrate.research.federated import FederatedRegistry
    from cvsubstrate.research.capture_v2 import capture_comparison
    from cvsubstrate.research.signing import keygen
    first=runs[0][0]
    claim=ScientificClaim(title='Procedural CPU campaign effect fixture',population='generated development images',dataset_sha256=digest(read_json(first/'dataset_manifest.json')),split='dev',intervention={'arm':'R+S'},comparator={'arm':'R'},metric='diagnostic_recall',direction='greater',protocol_sha256=digest(read_json(first/'experiment.json')['evaluation']),author_id='local-builder',purpose='software_fixture')
    environment=digest({'python':sys.version,'torch':torch.__version__,'device':'cpu'})
    with tempfile.TemporaryDirectory() as temp:
        key=Path(temp)/'signing.pem';pub=keygen(key,allow_unencrypted=True)
        with FederatedRegistry(out/'registry') as registry:
            cid=registry.add('claim',claim.model_dump(mode='json'))
            captures=[]
            for role,pair in zip(['original','reproduction'],runs):
                captures.append(capture_comparison(registry,cid,pair[0],pair[1],metric_path='aggregate.counts_by_iou.0.recall.value',actor_id='local-builder',machine_id='local-cpu',environment_sha256=environment,implementation_id='cvrs-native-torch',role=role))
            registry.sign_record(cid,key);registry.exchange(out/'base-exchange',signing_key=key)
            record('paired_run_capture',captures)
        # Separate writable copies; a failed attempt must survive their exchange.
        for name in ['left','right']:
            with FederatedRegistry(out/name) as reg:
                reg.merge(out/'base-exchange',trusted_keys=[pub['key_id']],require_signature=True)
                reg.add('actor',{'id':name,'display_name':'Local simulated writer '+name})
                if name=='right':
                    reg.add('attempt',{'claim_id':cid,'role':'reproduction','actor_id':'right','machine_id':'local-cpu','environment_sha256':environment,'implementation_id':'fixture-unavailable-backend','scope_fingerprint':claim.scope_fingerprint,'outcome':'blocked','failure_reason':'Deliberate unavailable-backend fixture; no model run claimed','purpose':'software_fixture'})
                reg.exchange(out/(name+'-exchange'),signing_key=key)
        with FederatedRegistry(out/'left') as reg:
            merged=reg.merge(out/'right-exchange',trusted_keys=[pub['key_id']],require_signature=True)
            root_before=reg.verify()['root_digest'];reg.merge(out/'right-exchange',trusted_keys=[pub['key_id']],require_signature=True);assert reg.verify()['root_digest']==root_before
            site=reg.export_site(out/'registry-site');reg.exchange(out/'merged-exchange',signing_key=key)
            status=reg.status(cid);assert status['level'] not in {'R4','R5'}
            record('federated_registry',{'verification':merged,'status':status,'site':site,'merge_idempotent':True,'public_signing_key':pub['public_key'],'private_key_packaged':False})
    # Typed external requirements remain missing without invalidating preserved evidence.
    from cvsubstrate.artifacts.capsule import create_capsule,archive_capsule,materialize_capsule
    closure={'dependencies':[{'id':'metrics','sha256':file_digest(out/'mask-analysis/evaluation.json'),'disposition':'EMBEDDED','path':'evaluation.json'},
                             {'id':'external-pretrained-weights','sha256':'1'*64,'disposition':'RESTRICTED','license':'UNKNOWN'}]}
    record('capsule',create_capsule(out/'mask-analysis',out/'capsule',dependency_closure=closure))
    archive_capsule(out/'capsule',out/'capsule.zip');record('restored_capsule',materialize_capsule(out/'capsule.zip',out/'capsule-restored'))
    summary['status']='CPU_CLOSURE_WORKFLOWS_EXECUTED';summary['scientific_certification']='NOT_CLAIMED'
    summary['limitations']=['Procedural inputs and random model initialization','Same operator and machine; R4/R5 not earned','Native MM/SAM/Grounding/UL/RF libraries not used in this smoke','No official benchmark/AP, GPU, or real Sim2Real claim']
    (out/'summary-in-progress.json').unlink(missing_ok=True);write_json(out/'summary.json',summary)
    return summary

if __name__=='__main__':
    try:print(json.dumps(run(Path(sys.argv[1])),indent=2))
    except Exception as exc:
        if len(sys.argv)>1:write_json(Path(sys.argv[1])/'failure.json',{'status':'FAILED','type':type(exc).__name__,'message':str(exc)})
        raise
