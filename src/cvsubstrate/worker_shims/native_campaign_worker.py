"""Execute a native stage with preserved resolved config and checkpoint identity."""
from pathlib import Path
import sys,os,runpy,time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from runtime_common import main,offline,check_file,write,sha

def run(request):
    job=request['job'];out=Path(request['output_dir']);out.mkdir(parents=True,exist_ok=False);offline()
    if job.get('initial_checkpoint'):check_file(job['initial_checkpoint'],job['initial_checkpoint_sha256'])
    backend=job['backend']
    if backend in {'ultralytics','rfdetr'}:
        from modern_detector_worker import run as modern
        from cvsubstrate.contracts.models import ExperimentSpec,DatasetManifest
        from cvsubstrate.provenance.io import digest
        import copy
        request=copy.deepcopy(job['native_request']);exp=request['experiment']
        exp['seed']=job['seed'];exp['adapter']['config'].setdefault('native_training',{})['epochs']=job['budget']
        if exp['adapter']['name']!=backend:raise ValueError('native backend mismatch')
        ExperimentSpec.model_validate(exp);manifest=DatasetManifest.model_validate(request['manifest'])
        if digest(manifest)!=job['dataset_sha256']:raise ValueError('native dataset identity mismatch')
        if job.get('initial_checkpoint'):
            request['checkpoint']={'path':job['initial_checkpoint'],'sha256':job['initial_checkpoint_sha256'],'trust':'trusted_legacy_pickle'}
        request['operation']='train';request['service']=backend;request['output_dir']=str(out/'training')
        return modern(request)
    if not job.get('trust_executable_config'):raise ValueError('explicit native config trust required')
    root=Path(job['source_root']).resolve();config=check_file(job['config'],job['config_sha256']);entry=check_file(root/'tools'/'train.py',job['entrypoint_sha256'])
    import subprocess
    revision=subprocess.run(['git','-C',str(root),'rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip()
    if revision!=job['revision']:raise ValueError('upstream revision mismatch')
    from mm_drivers import get_driver
    driver=get_driver(backend);cfg=driver.resolve(config)
    from cvsubstrate.heritage.closure import config_closure
    closure=config_closure(config,root,environment_names=job.get('environment_names',()),environment_values=job.get('environment_values',{}))
    write(out/'input-config-closure.json',closure)
    from cvsubstrate.heritage.native_data import bind_coco_training
    binding=bind_coco_training(cfg,job,out/'bound-data',backend)
    job['source_map']=binding['source_map']
    cfg.work_dir=str(out/'training');cfg.seed=job['seed']
    if backend!='mmdet2':cfg.randomness=dict(seed=job['seed'],deterministic=bool(job.get('deterministic',False)))
    if job['budget_unit']=='optimizer_updates':driver.configure_updates(cfg,job['budget'],1)
    elif backend=='mmdet2':cfg.runner=dict(type='EpochBasedRunner',max_epochs=job['budget'])
    else:cfg.train_cfg=dict(type='EpochBasedTrainLoop',max_epochs=job['budget'],val_interval=job['budget'])
    overrides=job.get('config_overrides',{})
    if any(k.split('.')[0] in {'work_dir','load_from','resume','resume_from','seed','randomness','runner','train_cfg','data','train_dataloader','val_dataloader','test_dataloader','val_evaluator','test_evaluator'} for k in overrides):raise ValueError('owned native configuration override refused')
    cfg.merge_from_dict(overrides)
    if job.get('initial_checkpoint'):cfg.load_from=job['initial_checkpoint']
    cfg.resume=False
    if backend=='mmdet2':cfg.resume_from=None
    if job['budget_unit']=='optimizer_updates':driver.configure_updates(cfg,job['budget'],1)
    resolved=out/'resolved_config.py';cfg.dump(str(resolved))
    # The upstream checkout is untouched; only this derived config is passed.
    from telemetry_runtime import TrainingLedger,observe_mm_runner
    import contextlib,importlib
    world=int(os.environ.get('WORLD_SIZE','1'));rank=int(os.environ.get('RANK','0'))
    ledger=TrainingLedger(out/f'telemetry-rank{rank}.sqlite',run_id=job.get('run_id',str(out.name)),rank=rank,world_size=world,source_map=job.get('source_map',{}),mixing_policy=job.get('mixing_policy','unobserved'))
    module='mmcv.runner.base_runner' if backend=='mmdet2' else 'mmengine.runner.runner';cls=getattr(importlib.import_module(module),'BaseRunner' if backend=='mmdet2' else 'Runner');old=cls.call_hook;stack=contextlib.ExitStack();active=set()
    def hook(runner,name,*args,**kwargs):
        if name==('before_run' if backend=='mmdet2' else 'before_train') and id(runner) not in active:stack.enter_context(observe_mm_runner(runner,ledger));active.add(id(runner))
        return old(runner,name,*args,**kwargs)
    cls.call_hook=hook;argv=sys.argv;start=time.monotonic();sys.path.insert(0,str(root))
    try:
        sys.argv=[str(entry),str(resolved),'--work-dir',str(out/'training'),'--launcher','pytorch' if world>1 else 'none']
        if backend=='mmdet2':sys.argv.extend(['--seed',str(job['seed'])])
        runpy.run_path(str(entry),run_name='__main__')
        checkpoint=out/'training'/job.get('checkpoint_filename','')
        if checkpoint.is_file():ledger.checkpoint(checkpoint)
    finally:
        sys.argv=argv;cls.call_hook=old;stack.close();summary=ledger.export(out/f'telemetry-rank{rank}');ledger.close()
    if job['budget_unit']=='optimizer_updates' and summary['optimizer_step_calls']!=job['budget']:raise ValueError('observed optimizer steps differ from declared fixed-update budget')
    result={'status':'EXECUTED','backend':backend,'source_revision':revision,'resolved_config_sha256':sha(resolved),'dataset_binding_sha256':sha(out/'bound-data'/'binding.json'),'config_closure_digest':closure['closure_digest'],'initial_checkpoint_sha256':job.get('initial_checkpoint_sha256'),'budget_unit':job['budget_unit'],'budget':job['budget'],'telemetry':summary,'wall_seconds':time.monotonic()-start}
    write(out/'execution.json',result);return result
if __name__=='__main__':main(run)
