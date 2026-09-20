"""Closure commands. Success JSON on stdout; typed errors on stderr."""
from pathlib import Path
import argparse,json,sys
from cvsubstrate.provenance.io import read_json,write_json,digest
from cvsubstrate.errors import CVRSError

def parser():
    p=argparse.ArgumentParser(prog='cvrs closure');sp=p.add_subparsers(dest='command',required=True)
    sp.add_parser('policy')
    a=sp.add_parser('compatibility');a.add_argument('manifest',type=Path);a.add_argument('--root',type=Path,required=True)
    a=sp.add_parser('identity');a.add_argument('kind');a.add_argument('artifact',type=Path)
    a=sp.add_parser('dependencies');a.add_argument('spec',type=Path);a.add_argument('--root',type=Path,default=Path('.'));a.add_argument('--bindings',type=Path)
    a=sp.add_parser('gc');a.add_argument('store',type=Path);a.add_argument('--age',type=float,default=86400);a.add_argument('--apply-plan');a.add_argument('--pin');a.add_argument('--hashes',nargs='*',default=[]);a.add_argument('--unpin')
    a=sp.add_parser('config');a.add_argument('config',type=Path);a.add_argument('--root',type=Path,required=True);a.add_argument('--out',type=Path);a.add_argument('--environment',type=Path)
    a=sp.add_parser('model-index');a.add_argument('index',type=Path);a.add_argument('--root',type=Path,required=True)
    a=sp.add_parser('checkpoint');a.add_argument('operation',choices=['diff','transform']);a.add_argument('left',type=Path);a.add_argument('right',type=Path);a.add_argument('--out',type=Path);a.add_argument('--worker-python')
    a=sp.add_parser('telemetry');a.add_argument('files',nargs='+',type=Path);a.add_argument('--world-size',required=True,type=int)
    a=sp.add_parser('environment-diff');a.add_argument('recipe',type=Path);a.add_argument('observation',type=Path)
    a=sp.add_parser('lineage');a.add_argument('spec',type=Path)
    a=sp.add_parser('slice');a.add_argument('records',type=Path);a.add_argument('predicate',type=Path)
    a=sp.add_parser('assets');a.add_argument('spec',type=Path);a.add_argument('--root',type=Path,required=True)
    a=sp.add_parser('native-campaign');a.add_argument('operation',choices=['plan','run']);a.add_argument('spec',type=Path);a.add_argument('--out',type=Path);a.add_argument('--workers',type=Path);a.add_argument('--resume',action='store_true');a.add_argument('--timeout',type=float,default=3600)
    a=sp.add_parser('stream');a.add_argument('spec',type=Path);a.add_argument('--out',type=Path,required=True);a.add_argument('--worker-python');a.add_argument('--resume',action='store_true');a.add_argument('--max-tiles',type=int);a.add_argument('--timeout',type=float,default=600)
    a=sp.add_parser('prompts');a.add_argument('operation',choices=['negotiate','trajectory','continue']);a.add_argument('spec',type=Path);a.add_argument('--backend');a.add_argument('--out',type=Path);a.add_argument('--worker-python')
    a=sp.add_parser('authorize-evaluation');a.add_argument('spec',type=Path);a.add_argument('--ledger',type=Path,required=True);a.add_argument('--approved-by',required=True);a.add_argument('--reason',required=True);a.add_argument('--max-uses',type=int,default=1)
    a=sp.add_parser('reevaluate');a.add_argument('spec',type=Path);a.add_argument('--out',type=Path,required=True);a.add_argument('--worker-python')
    a=sp.add_parser('compare');a.add_argument('left',type=Path);a.add_argument('right',type=Path)
    a=sp.add_parser('keygen');a.add_argument('destination',type=Path);a.add_argument('--unencrypted',action='store_true')
    a=sp.add_parser('registry');a.add_argument('operation',choices=['add','edge','status','query','verify','export','merge','site','sign','migrate']);a.add_argument('root',type=Path);a.add_argument('--kind');a.add_argument('--input',type=Path);a.add_argument('--id');a.add_argument('--out',type=Path);a.add_argument('--key',type=Path);a.add_argument('--trusted-key',action='append',default=[]);a.add_argument('--require-signature',action='store_true');a.add_argument('--key-password-env');a.add_argument('--minimum-level');a.add_argument('--filters',type=Path)
    a=sp.add_parser('capture-comparison');a.add_argument('spec',type=Path);a.add_argument('--registry',type=Path,required=True)
    return p

def execute(a):
    if a.command=='compatibility':
        from cvsubstrate.foundation.compatibility import inspect_compatibility
        return inspect_compatibility(a.manifest,a.root)
    if a.command=='policy':
        from cvsubstrate.foundation.policy import POLICY
        return POLICY
    if a.command=='identity':
        from cvsubstrate.foundation.identity import content_id
        return {'id':content_id(a.kind,read_json(a.artifact))}
    if a.command=='dependencies':
        from cvsubstrate.artifacts.dependencies import DependencyClosure,inspect_closure
        return inspect_closure(DependencyClosure.model_validate(read_json(a.spec)),a.root,read_json(a.bindings) if a.bindings else {})
    if a.command=='gc':
        from cvsubstrate.artifacts.managed import ManagedArtifactStore
        store=ManagedArtifactStore(a.store)
        if a.pin:return store.pin(a.pin,a.hashes)
        if a.unpin:store.unpin(a.unpin);return {'unpinned':a.unpin}
        return store.gc(minimum_age_seconds=a.age,dry_run=not a.apply_plan,plan_digest=a.apply_plan)
    if a.command=='config':
        from cvsubstrate.heritage.closure import config_closure,preserve_closure
        result=config_closure(a.config,a.root,environment_values=read_json(a.environment) if a.environment else {},environment_names=list(read_json(a.environment)) if a.environment else ())
        if a.out:return preserve_closure(a.config,a.root,a.out,environment_values=read_json(a.environment) if a.environment else {},environment_names=list(read_json(a.environment)) if a.environment else ())
        return result
    if a.command=='model-index':
        from cvsubstrate.heritage.model_index import ingest_model_index
        return ingest_model_index(a.index,a.root)
    if a.command=='checkpoint':
        from cvsubstrate.heritage.checkpoint_v1 import diff_checkpoints,transform_checkpoint
        if a.operation=='diff':return diff_checkpoints(read_json(a.left),read_json(a.right),worker_python=a.worker_python)
        if a.out is None:raise ValueError('--out is required for conversion')
        return transform_checkpoint(read_json(a.left),read_json(a.right),a.out,worker_python=a.worker_python)
    if a.command=='telemetry':
        from cvsubstrate.telemetry_v1 import aggregate_ranks
        return aggregate_ranks(a.files,a.world_size)
    if a.command=='environment-diff':
        from cvsubstrate.environments.compare import compare_environment
        return compare_environment(read_json(a.recipe),read_json(a.observation))
    if a.command=='lineage':
        from cvsubstrate.data.asset_lineage import AssetLineage,check_asset_leakage
        return check_asset_leakage(AssetLineage.model_validate(read_json(a.spec)))
    if a.command=='slice':
        from cvsubstrate.analysis.metric_plugins import slice_receipt
        return slice_receipt(read_json(a.records),read_json(a.predicate))
    if a.command=='assets':
        from cvsubstrate.vision.assets import inspect_assets
        return inspect_assets(read_json(a.spec),a.root,reject_unlisted=True)
    if a.command=='native-campaign':
        from cvsubstrate.campaigns.native import compile_native_campaign,run_native_campaign
        if a.operation=='plan':return compile_native_campaign(read_json(a.spec))
        if not a.out:raise ValueError('--out required')
        return run_native_campaign(read_json(a.spec),a.out,worker_pythons=read_json(a.workers) if a.workers else {},timeout=a.timeout,resume=a.resume)
    if a.command=='stream':
        from cvsubstrate.execution.services import invoke_service
        return invoke_service('task_stream',{'spec':read_json(a.spec),'output_dir':str(a.out.resolve()),'resume':a.resume,'max_tiles':a.max_tiles},worker_python=a.worker_python,timeout=a.timeout)
    if a.command=='prompts':
        from cvsubstrate.vision.prompts import PromptSet,negotiate_prompts
        from cvsubstrate.vision.trajectories import execute_trajectory,continue_prompt_step
        value=read_json(a.spec)
        if a.operation=='negotiate':return negotiate_prompts(a.backend,[PromptSet.model_validate(s) for s in value])
        if not a.out:raise ValueError('--out required')
        if a.operation=='continue':return continue_prompt_step(value['job'],value['previous_step'],value['prompt_set'],a.out,worker_python=a.worker_python)
        return execute_trajectory(value['job'],value['sets'],a.out,worker_python=a.worker_python)
    if a.command=='authorize-evaluation':
        from cvsubstrate.research.task_access import authorize_task_evaluation
        return authorize_task_evaluation(read_json(a.spec),a.ledger,approved_by=a.approved_by,reason=a.reason,max_uses=a.max_uses)
    if a.command=='reevaluate':
        from cvsubstrate.research.evaluators import reevaluate_task
        return reevaluate_task(read_json(a.spec),a.out,worker_python=a.worker_python)
    if a.command=='compare':
        from cvsubstrate.vision.diagnostics import compare_paradigms
        return compare_paradigms(read_json(a.left),read_json(a.right))
    if a.command=='keygen':
        from cvsubstrate.research.signing import keygen
        import getpass
        password=None if a.unencrypted else getpass.getpass('Private-key password (not logged): ').encode()
        return keygen(a.destination,password=password,allow_unencrypted=a.unencrypted)
    if a.command=='capture-comparison':
        from cvsubstrate.research.federated import FederatedRegistry
        from cvsubstrate.research.capture_v2 import capture_comparison
        with FederatedRegistry(a.registry) as reg:return capture_comparison(reg,**read_json(a.spec))
    if a.command=='registry':
        from cvsubstrate.research.federated import FederatedRegistry,migrate_registry_v1
        if a.operation=='migrate':
            if not a.out:raise ValueError('--out required')
            return migrate_registry_v1(a.root,a.out)
        password=None
        if a.key and a.key_password_env:
            import os
            if a.key_password_env not in os.environ:raise ValueError('declared key password environment variable is absent')
            password=os.environ[a.key_password_env].encode()
        elif a.key and b'ENCRYPTED PRIVATE KEY' in a.key.read_bytes():
            import getpass
            password=getpass.getpass('Private-key password (not logged): ').encode()
        with FederatedRegistry(a.root) as reg:
            if a.operation=='verify':return reg.verify()
            if a.operation=='add':return {'id':reg.add(a.kind,read_json(a.input))}
            if a.operation=='edge':return {'id':reg.add_edge(read_json(a.input))}
            if a.operation=='status':return reg.status(a.id)
            if a.operation=='query':return reg.search(kind=a.kind,filters=read_json(a.filters) if a.filters else {},minimum_level=a.minimum_level)
            if a.operation=='site':return reg.export_site(a.out)
            if a.operation=='export':return {'root_digest':reg.exchange(a.out,signing_key=a.key,password=password)}
            if a.operation=='merge':return reg.merge(a.input,trusted_keys=a.trusted_key,require_signature=a.require_signature)
            if a.operation=='sign':return reg.sign_record(a.id,a.key,password=password)
    raise ValueError('unknown closure operation')

def main(argv=None):
    try:
        args=parser().parse_args(argv);result=execute(args);print(json.dumps(result,indent=2,allow_nan=False,default=str));return 0
    except Exception as e:
        from cvsubstrate.security import sanitize
        if isinstance(e,CVRSError):code=e.code
        elif isinstance(e,ImportError):code='DEPENDENCY_UNAVAILABLE'
        elif isinstance(e,FileNotFoundError):code='ARTIFACT_MISSING'
        elif isinstance(e,PermissionError):code='PERMISSION_DENIED'
        elif isinstance(e,(ValueError,KeyError,TypeError)):code='VALIDATION_ERROR'
        else:code='INTERNAL_ERROR'
        print(json.dumps(sanitize({'status':'FAILED','error':{'code':code,'message':str(e)}})),file=sys.stderr);return 2
