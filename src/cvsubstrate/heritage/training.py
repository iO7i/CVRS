"""Native MM training launcher and evidence-conditioned H5 rules.

The launcher uses the upstream tools/train.py, not a new MM training engine.
Native config controls data and schedules: caller must audit it and explicitly
accept code/data access. No portable source-exposure equivalence is inferred.
"""
from pathlib import Path
import subprocess,sys,time,os
from cvsubstrate.provenance.io import read_json,write_json,file_digest,digest,safe_join
from cvsubstrate.provenance.artifact_set import seal_directory,verify_directory,assert_not_inside_sealed
from cvsubstrate.execution.process import run_command
from cvsubstrate.heritage.profiles import get_profile
from cvsubstrate.heritage.importer import config_graph
from cvsubstrate.errors import CVRSError

def train_native(spec,output,*,worker_python=None,timeout=300):
    out=Path(output).resolve();assert_not_inside_sealed(out)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','native training output must be new')
    if not spec.get('trust_executable_config') or not spec.get('acknowledge_native_data_access'):raise CVRSError('HERITAGE_TRUST','explicit config execution and native dataset access acknowledgement required')
    root=Path(spec['source_root']).resolve();config=Path(spec['config']).resolve();profile=get_profile(spec['profile'])
    if not config.is_relative_to(root) or file_digest(config)!=spec['config_sha256']:raise CVRSError('CONFIG_HASH','config must match and belong to source root')
    entry=safe_join(root,profile['training_entrypoint'])
    if file_digest(entry)!=spec['entrypoint_sha256']:raise CVRSError('SOURCE_HASH','training entry point changed')
    revision=subprocess.run(['git','-C',str(root),'rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip()
    if revision!=spec['revision']:raise CVRSError('SOURCE_REVISION','native source revision differs')
    dirty=subprocess.run(['git','-C',str(root),'status','--porcelain'],check=True,capture_output=True,text=True).stdout
    if dirty.strip():raise CVRSError('DIRTY_SOURCE','native training profile requires a clean source checkout')
    args=spec.get('native_args',[])
    if any(not isinstance(x,str) for x in args) or any(x.split('=')[0] in {'--work-dir','--launcher'} for x in args):raise ValueError('output and distributed launcher cannot be overridden')
    overrides=spec.get('cfg_options',{})
    if any(k in {'work_dir','resume','load_from'} for k in overrides):raise ValueError('initialization/resume must remain declared in the preserved config; work_dir is owned')
    graph=config_graph(config,root);out.mkdir(parents=True)
    write_json(out/'request.json',spec);write_json(out/'config_graph.json',graph)
    (out/'original_config.py.txt').write_bytes(config.read_bytes())
    command=[worker_python or sys.executable,str(entry),str(config),'--work-dir',str(out/'training'),'--launcher','none',*args]
    if overrides:command+=['--cfg-options',*[f'{k}={v}' for k,v in sorted(overrides.items())]]
    telemetry=spec.get('telemetry')
    if telemetry:
        source_map=telemetry.get('source_map',{})
        if not source_map:raise ValueError('telemetry requires explicit native identity to canonical sample/source mapping')
        metadata={'path':str(out/'telemetry.sqlite'),'run_id':spec.get('run_id','mm-training'),'source_map':source_map,
            'mixing_policy':telemetry.get('mixing_policy','unobserved'),'profile':spec['profile']}
        write_json(out/'telemetry-spec.json',metadata)
        shim=Path(__file__).resolve().parents[1]/'worker_shims'/'mm_train_telemetry.py'
        command=[worker_python or sys.executable,str(shim),'--entry',str(entry),'--telemetry-spec',str(out/'telemetry-spec.json'),*command[2:]]
    # Trainer is trusted arbitrary upstream code, not a sandbox. Root/env are
    # explicit, no automatic GPU allocation, pip install or download call here.
    env=dict(os.environ)
    if not spec.get('allow_gpu',False):env['CUDA_VISIBLE_DEVICES']='-1'
    env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',WANDB_MODE='disabled')
    write_json(out/'launch.json',{'argv':command,'source_revision':revision,'profile':profile,'gpu_allowed':spec.get('allow_gpu',False),'native_data_contract':spec.get('dataset_identities',{})})
    start=time.perf_counter()
    try:
        run_command(command,timeout,log=out/'train.log',env=env,cwd=root)
        checkpoints=[{'path':p.relative_to(out).as_posix(),'sha256':file_digest(p)} for p in sorted((out/'training').rglob('*.pth'))]
        result={'status':'NATIVE_TRAINING_EXECUTED','source_revision':revision,'config_sha256':spec['config_sha256'],'checkpoints':checkpoints,
            'wall_seconds':time.perf_counter()-start,'portable_exposure_accounting':'NOT_OBSERVED','scientific_reproduction':'NOT_ESTABLISHED','dataset_identities':spec.get('dataset_identities',{})}
        if telemetry:
            result['telemetry']=read_json(out/'telemetry'/'training-summary.json');result['portable_exposure_accounting']=result['telemetry']['source_accounting']
        write_json(out/'result.json',result);seal_directory(out);return result
    except Exception as exc:
        write_json(out/'failure.json',{'code':getattr(exc,'code',type(exc).__name__),'message':str(exc),'wall_seconds':time.perf_counter()-start});seal_directory(out);raise

def certify_training(spec,output):
    from cvsubstrate.execution.heritage import certify_run,_flat_metric_values
    from cvsubstrate.provenance.bundle import verify_bundle
    out=Path(output)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','certification must be a fresh derived artifact')
    training=Path(spec['training_run']);inference=Path(spec['inference_run']);reference=read_json(spec['reference'])
    checks={};checks['training_bundle']=verify_directory(training)['status']=='VERIFIED';checks['inference_bundle']=verify_bundle(inference).get('run_state')=='SUCCEEDED'
    request=read_json(training/'request.json');execution=read_json(training/'result.json');exp=read_json(inference/'experiment.json');worker=read_json(inference/'worker_result.json')
    m=read_json(inference/'dataset_manifest.json');checks['real_research_dataset']=m.get('purpose')=='research_dataset'
    ck=exp.get('checkpoint') or {};checks['trained_checkpoint_is_evaluated']=ck.get('sha256') in {p['sha256'] for p in execution.get('checkpoints',[])}
    checks['native_training_executed']=execution.get('status')=='NATIVE_TRAINING_EXECUTED'
    checks['matching_source_revision']=execution.get('source_revision')==reference.get('revision')==worker.get('actual_source_identity',{}).get('git_sha') and bool(reference.get('revision'))
    checks['matching_training_config']=execution.get('config_sha256')==reference.get('training_config_sha256') and bool(reference.get('training_config_sha256'))
    checks['matching_native_overrides']=request.get('cfg_options',{})==reference.get('cfg_options',{})
    checks['dataset_identities']=bool(reference.get('training_dataset_identities')) and execution.get('dataset_identities')==reference.get('training_dataset_identities')
    checks['evaluation_protocol']=exp.get('evaluation')==reference.get('evaluation_protocol')
    checks['evaluation_dataset']=exp.get('dataset_sha256')==reference.get('evaluation_dataset_sha256')
    checks['published_source']=bool(reference.get('published_source'))
    observed=_flat_metric_values(read_json(inference/'metrics.json'));metrics=reference.get('reported_metrics',{});tolerances=reference.get('absolute_tolerances',{});deltas={}
    for key,expected in metrics.items():
        tolerance=tolerances.get(key)
        if not isinstance(tolerance,(int,float)) or tolerance<0:raise ValueError('each training metric needs an explicit nonnegative absolute tolerance')
        value=observed.get(key);deltas[key]=None if value is None else abs(value-expected)
    checks['reported_metric_reproduction']=bool(metrics) and all(v is not None and v<=tolerances[k] for k,v in deltas.items())
    base=certify_run(inference);checks['prediction_parity']=base['compatibility_level']=='H3_OUTPUT_PARITY_VERIFIED'
    result={'compatibility_level':'H5_TRAINING_REPRODUCED' if all(checks.values()) else base['compatibility_level'],
        'checks':checks,'metric_deltas':deltas,'training_manifest_sha256':file_digest(training/'integrity.json'),
        'inference_manifest_sha256':file_digest(inference/'artifacts.json'),'reference_digest':digest(reference),
        'independently_reproduced':False,'limits':'Evidence consistency rules, not proof of undisclosed data access, authenticity, external peer review or broad environment compatibility. Training H5 uses its trained checkpoint and declared training-reference metric, not byte equality with the published checkpoint.'}
    write_json(out,result);return result
