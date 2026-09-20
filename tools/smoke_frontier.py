"""Reproducible CPU smoke; no downloads, pretrained models, or scientific claims.

Run: PYTHONPATH=src python tools/smoke_frontier.py /new/output/path
Requires the native and geo extras. Creates its own procedural images/checkpoints.
"""
from pathlib import Path
import json,sys,dataclasses
from cvsubstrate.provenance.io import write_json,read_json,read_jsonl,file_digest,digest
from cvsubstrate.provenance.artifact_set import verify_directory,seal_directory

def run(out):
    import numpy as np
    import torch
    from PIL import Image
    import rasterio
    from rasterio.transform import from_origin
    out=Path(out).resolve()
    if out.exists():raise ValueError('use a new smoke output directory')
    out.mkdir(parents=True);torch.set_num_threads(1);torch.manual_seed(17)
    summary={'purpose':'software_fixture','pretrained_weights':False,'external_models_downloaded':False,'gpu_used':False}
    from cvsubstrate.vision.native_mask import build_mask_detector
    from cvsubstrate.worker_shims.telemetry_runtime import TrainingLedger,observe_optimizer
    mask_model=build_mask_detector(2);opt=torch.optim.SGD(mask_model.parameters(),lr=.001)
    image=torch.zeros((3,64,80));image[:,20:42,24:50]=.7
    target={'boxes':torch.tensor([[24.,20.,50.,42.]]),'labels':torch.tensor([1]),'masks':torch.zeros((1,64,80),dtype=torch.uint8)}
    target['masks'][0,20:42,24:50]=1
    before={k:v.detach().clone() for k,v in mask_model.state_dict().items()}
    ledger=TrainingLedger(out/'native-mask-training.sqlite',run_id='native-mask-cpu',source_map={'mask-0':'synthetic'},mixing_policy='disabled_or_fully_traced')
    with observe_optimizer(opt,ledger):
        mask_model.train();ledger.batch(['mask-0']);losses=mask_model([image],[target]);sum(losses.values()).backward();opt.step()
    summary['mask_training']={'losses':{k:float(v.detach()) for k,v in losses.items()},'parameters_changed':any(not torch.equal(before[k],v) for k,v in mask_model.state_dict().items()),'telemetry':ledger.export(out/'mask-telemetry')};ledger.close()
    assets=out/'mask-assets';assets.mkdir();torch.save(mask_model.state_dict(),assets/'mask.pt')
    Image.fromarray((image.permute(1,2,0).numpy()*255).astype(np.uint8)).save(out/'mask-image.png')
    job={'backend':'torchvision_mask','model_dir':str(assets),'model_files':{'mask.pt':file_digest(assets/'mask.pt')},'images':[{'id':'mask-0','path':str(out/'mask-image.png'),'sha256':file_digest(out/'mask-image.png'),'split_role':'dev'}],
        'config':{'weights_file':'mask.pt','category_map':{'1':0}},'purpose':'software_fixture'}
    write_json(out/'mask-job.json',job)
    from cvsubstrate.vision.service import vision_job
    from cvsubstrate.contracts.frontier import MaskPrediction
    from cvsubstrate.vision.masks import decode_mask
    summary['mask_inference']=vision_job(job,out/'mask-run',timeout=90)
    canonical=MaskPrediction.model_validate(read_jsonl(out/'mask-run/worker/predictions.jsonl')[0])
    raw=next((out/'mask-run/worker').glob('*-native.npz'))
    with np.load(raw,allow_pickle=False) as native:
        assert len(native['masks'])==len(canonical.instances)
        assert all(np.array_equal(m,decode_mask(instance.mask)) for m,instance in zip(native['masks'],canonical.instances))
    summary['mask_native_to_canonical_exact']=True;summary['mask_bundle']=verify_directory(out/'mask-run')
    # Real source-window IO and genuine native Faster R-CNN, small enough for CPU.
    from cvsubstrate.workers.native_torch import model_factory,save_checkpoint
    model=model_factory(2);save_checkpoint(out/'stream-model.pt',model,None,None,{'purpose':'software_fixture'},{'completed_updates':0})
    raster=out/'source.tif'
    with rasterio.open(raster,'w',driver='GTiff',width=96,height=80,count=3,dtype='uint8',crs='EPSG:32637',transform=from_origin(400000,2500000,.5,.5)) as ds:
        ds.write(np.random.default_rng(17).integers(0,255,(3,80,96),dtype=np.uint8))
    spec={'raster':str(raster),'raster_sha256':file_digest(raster),'tile_width':64,'tile_height':64,'overlap':16,'scales':[1.0],'sample_id':'scene',
        'model':{'backend':'native_torch','checkpoint':str(out/'stream-model.pt'),'checkpoint_sha256':file_digest(out/'stream-model.pt'),'trust_checkpoint':True,'category_map':{'1':0},'config':{},'cpu_threads':1}}
    write_json(out/'stream-job.json',spec)
    from cvsubstrate.streaming.service import stream_job
    summary['stream_partial']=stream_job(out/'stream-job.json',out/'stream-run',timeout=90,max_tiles=1)
    summary['stream_resumed']=stream_job(out/'stream-job.json',out/'stream-run',timeout=90,resume=True)
    from cvsubstrate.contracts.models import DetectionPrediction
    rows=read_jsonl(out/'stream-run/canonical-predictions.jsonl');DetectionPrediction.model_validate(rows[0])
    assert summary['stream_resumed']['status']=='SUCCEEDED' and summary['stream_resumed']['reused_tiles']==1
    # Fresh genuine detector run -> original record -> same-experiment rerun -> registry.
    from cvsubstrate.data.fixtures import generate
    from cvsubstrate.execution.runner import run_experiment
    from cvsubstrate.research.capture import capture_run
    generate(out/'fixtures')
    exp=read_json(out/'fixtures/real.json');exp['training']['updates']=1;write_json(out/'fixtures/real.json',exp)
    native_run=run_experiment(out/'fixtures/real.json',out/'runs',timeout=90)
    metadata={'title':'CPU fixture detection execution','question':'Can an actual local detector run be preserved and rerun?','estimand':'diagnostic recall on procedural fixture images','author_id':'local-builder','machine_id':'build-cpu','implementation_id':'cvrs-native-torch','metric_names':['aggregate/counts_by_iou/0/recall']}
    summary['registry_original']=capture_run(out/'registry',native_run,out/'fixtures/dataset.json',**metadata)
    rerun=run_experiment(out/'fixtures/real.json',out/'runs',timeout=90)
    summary['registry_rerun']=capture_run(out/'registry',rerun,out/'fixtures/dataset.json',existing_claim_id=summary['registry_original']['claim_id'],**metadata)
    from cvsubstrate.research.reevaluate import reevaluate
    protocol=read_json(native_run/'experiment.json')['evaluation'];protocol['score_threshold']=.25;write_json(out/'changed-protocol.json',protocol)
    original_hash=file_digest(native_run/'predictions.jsonl')
    summary['reevaluation']=reevaluate(out/'fixtures/dataset.json','dev',native_run/'predictions.jsonl',out/'changed-protocol.json',out/'reevaluation',origin=file_digest(native_run/'artifacts.json'))
    assert file_digest(native_run/'predictions.jsonl')==original_hash
    from cvsubstrate.research.registry import ResearchRegistry
    from cvsubstrate.research.capsule import export_registry_capsule,import_registry_capsule
    with ResearchRegistry(out/'registry') as registry:
        summary['registry_status']=registry.status(summary['registry_original']['claim_id']);registry.export(out/'static-registry');head=registry.verify()['head']
    export_registry_capsule(out/'registry',out/'research-capsule',out/'research-capsule.zip')
    import_registry_capsule(out/'research-capsule.zip',out/'restored-registry')
    with ResearchRegistry(out/'restored-registry') as registry:summary['registry_capsule_restored']=registry.verify();assert summary['registry_capsule_restored']['head']==head
    summary['status']='CPU_WORKFLOWS_EXECUTED';summary['limitations']=['Generated inputs and random model initialization','Same machine/operator; no independent external reproduction','No pretrained foundation/open-vocabulary model executed','No official COCO/DOTA/AP or GPU claim']
    write_json(out/'summary.json',summary);return summary

if __name__=='__main__':
    try:print(json.dumps(run(Path(sys.argv[1])),indent=2))
    except Exception as exc:
        if len(sys.argv)>1:write_json(Path(sys.argv[1])/'smoke-failure.json',{'status':'FAILED','type':type(exc).__name__,'message':str(exc)})
        raise
