"""0.4 public CLI extensions. Legacy 0.1–0.3 commands remain supported.

Heavy dependencies are imported only by the operation which needs them. Trusted
plugins/native services run in an explicitly selected separate interpreter.
"""
from pathlib import Path
import argparse,json,sys
from cvsubstrate.provenance.io import read_json,read_jsonl,write_json,digest
from cvsubstrate.errors import CVRSError

ROOTS={'schema','migrate','migrate-run','plugin','graph','artifact','cache','environment','checkpoint','model','backbone','deploy','large','slice','distribution','benchmark','licenses','release','docs','size-evaluate','groundwork-fixtures'}
NESTED={'dataset':{'import','materialize','inspect-geo','geo-manifest','export-world'},
    'heritage':{'import','profiles','graph','convert-predictions','trusted-import','catalogue','train-native','certify-training'},
    'campaign':{'compile','run-stages','budgets','sweep'},'synthetic':{'ingest','validate-sample'},
    'capsule':{'create','validate','inspect','archive','materialize'},'report':{'create'}}

def handles(argv):
    return bool(argv) and (argv[0] in ROOTS or (len(argv)>1 and argv[0] in NESTED and argv[1] in NESTED[argv[0]]))

def parser():
    p=argparse.ArgumentParser(prog='cvrs',description='Groundwork commands; JSON specifications, explicit local assets, no implicit downloads.')
    sub=p.add_subparsers(dest='command',required=True)
    def group(name):return sub.add_parser(name).add_subparsers(dest='action',required=True)
    def path(a,name,**kw):a.add_argument(name,type=Path,**kw)
    def out(a):path(a,'--out',required=True)
    def worker(a):a.add_argument('--worker-python');a.add_argument('--timeout',type=float,default=300)
    def spec(a):path(a,'spec')
    s=group('schema');s.add_parser('list')
    a=s.add_parser('inspect');a.add_argument('name')
    a=s.add_parser('validate');path(a,'artifact');a.add_argument('--schema')
    a=s.add_parser('export');out(a)
    for name in ['migrate','migrate-run']:
        a=sub.add_parser(name);path(a,'source');out(a)
        if name=='migrate':a.add_argument('--schema')
    s=group('plugin')
    for name in ['list','inspect','register']:
        a=s.add_parser(name);path(a,'--registry',required=True)
        if name=='inspect':a.add_argument('name')
        if name=='register':path(a,'descriptor')
    a=s.add_parser('scaffold');a.add_argument('name');a.add_argument('--kind',default='dataset');out(a)
    for name in ['validate','conformance','run']:
        a=s.add_parser(name);path(a,'descriptor');a.add_argument('--trust-code',action='store_true');worker(a)
        if name=='conformance':path(a,'--fixtures',required=True);out(a)
        elif name=='run':a.add_argument('--operation',required=True);path(a,'--payload',required=True);out(a)
    a=s.add_parser('negotiate');spec(a)
    s=group('graph');s.add_parser('actions')
    a=s.add_parser('plan');spec(a)
    a=s.add_parser('run');spec(a);out(a);a.add_argument('--resume',action='store_true');path(a,'--cache');a.add_argument('--invalidate',nargs='*')
    for name in ['artifact','cache']:
        s=group(name)
        for op in ['put','get','verify','exists']:
            a=s.add_parser(op);path(a,'--store',required=True)
            if op=='put':path(a,'source')
            else:a.add_argument('sha256')
            if op=='get':out(a)
    s=group('environment');a=s.add_parser('capture');path(a,'--out');a.add_argument('--probe-hardware',action='store_true')
    a=s.add_parser('import');path(a,'source');a.add_argument('--kind',required=True,choices=['pip','uv','conda','conda-explicit','docker']);path(a,'--out')
    a=s.add_parser('capsule');spec(a);out(a)
    s=group('capsule')
    for name in ['create','validate','inspect','archive','materialize']:
        a=s.add_parser(name);path(a,'source')
        if name in {'create','archive','materialize'}:out(a)
        if name=='create':path(a,'--references');path(a,'--dependencies');a.add_argument('--include',nargs='*')
    s=group('checkpoint')
    a=s.add_parser('inspect');spec(a);worker(a);path(a,'--out')
    a=s.add_parser('convert');spec(a);worker(a);out(a)
    s=group('model')
    a=s.add_parser('capabilities');a.add_argument('backend',choices=['ultralytics','rfdetr']);worker(a)
    for name in ['predict','train-native','export','predict-obb','train-obb']:
        a=s.add_parser(name);spec(a);out(a);worker(a)
    s=group('backbone');a=s.add_parser('extract');spec(a);out(a);worker(a)
    s=group('deploy')
    for name in ['export','infer']:
        a=s.add_parser(name);spec(a);out(a);worker(a)
    for name in ['compare-arrays','compare-detections','compare-metrics']:
        a=s.add_parser(name);path(a,'left');path(a,'right');path(a,'--out')
        if name=='compare-arrays':a.add_argument('--atol',type=float,default=1e-6);a.add_argument('--rtol',type=float,default=1e-5);path(a,'--names')
    a=s.add_parser('decode');path(a,'run');spec(a);out(a)
    s=group('dataset');a=s.add_parser('import');spec(a);out(a)
    a=s.add_parser('materialize');path(a,'manifest');path(a,'--image-root',required=True);out(a);a.add_argument('--mode',choices=['copy','hardlink'],default='copy')
    a=s.add_parser('inspect-geo');path(a,'source');path(a,'--sidecar');path(a,'--out')
    a=s.add_parser('geo-manifest');spec(a);out(a)
    a=s.add_parser('export-world');path(a,'predictions');path(a,'--georeferences',required=True);a.add_argument('--format',choices=['geojson','json','csv'],default='geojson');out(a)
    s=group('large');a=s.add_parser('plan');spec(a);path(a,'--out')
    a=s.add_parser('run');spec(a);path(a,'--policy',required=True);out(a);worker(a);a.add_argument('--evaluator-python')
    a=s.add_parser('merge');path(a,'detections');path(a,'--policy',required=True);path(a,'--out')
    a=sub.add_parser('size-evaluate');path(a,'predictions');path(a,'--dataset',required=True);path(a,'--policy',required=True);a.add_argument('--split',default='dev');a.add_argument('--iou',type=float,default=.5);a.add_argument('--threshold',type=float,default=.5);path(a,'--gsd');path(a,'--out')
    s=group('slice');a=s.add_parser('select');path(a,'dataset');a.add_argument('--split',default='dev');path(a,'--policy',required=True);path(a,'--metadata');path(a,'--out')
    s=group('distribution');a=s.add_parser('describe');path(a,'dataset');a.add_argument('--split',default='dev');path(a,'--metadata');a.add_argument('--image-stats',action='store_true');path(a,'--out')
    a=s.add_parser('compare');path(a,'left');path(a,'right');path(a,'--out')
    a=s.add_parser('embeddings');path(a,'left');path(a,'right');path(a,'--left-descriptor',required=True);path(a,'--right-descriptor',required=True);path(a,'--out')
    s=group('synthetic');a=s.add_parser('ingest');path(a,'source');path(a,'--mapping',required=True);out(a)
    a=s.add_parser('validate-sample');path(a,'source')
    s=group('campaign')
    for name in ['compile','budgets','run-stages']:
        a=s.add_parser(name);spec(a)
        if name=='run-stages':out(a);worker(a);a.add_argument('--resume',action='store_true');a.add_argument('--retry-failed',action='store_true')
        else:path(a,'--out')
    a=s.add_parser('sweep');spec(a);path(a,'--axes',required=True);out(a);a.add_argument('--max-cases',type=int,default=10000)
    s=group('heritage');s.add_parser('profiles')
    a=s.add_parser('train-native');spec(a);out(a);worker(a)
    a=s.add_parser('certify-training');spec(a);out(a)
    a=s.add_parser('import');spec(a);out(a)
    a=s.add_parser('graph');path(a,'config');path(a,'--source-root',required=True);path(a,'--out')
    a=s.add_parser('convert-predictions');path(a,'native');a.add_argument('--format',required=True);path(a,'--mapping',required=True);path(a,'--dataset');a.add_argument('--split',default='dev');path(a,'--image-id-map');path(a,'--angle-convention');out(a)
    a=s.add_parser('trusted-import');spec(a);out(a);worker(a)
    a=s.add_parser('catalogue');ss=a.add_subparsers(dest='catalogue_action',required=True)
    for name in ['list','search','validate','add','docs']:
        a=ss.add_parser(name);path(a,'catalogue')
        if name=='search':a.add_argument('query')
        if name=='add':path(a,'entry');out(a)
        if name=='docs':out(a)
    s=group('benchmark')
    a=s.add_parser('register');spec(a);path(a,'--registry',required=True)
    a=s.add_parser('list');path(a,'--registry',required=True)
    for name in ['preregister','authorize-final']:
        a=s.add_parser(name);spec(a);path(a,'--ledger',required=True);path(a,'--out')
    a=s.add_parser('final-eval');path(a,'benchmark');path(a,'experiment');path(a,'--ledger',required=True);a.add_argument('--approval-digest',required=True);out(a);worker(a);a.add_argument('--evaluator-python')
    a=s.add_parser('access-log');path(a,'ledger')
    a=s.add_parser('submission-check');path(a,'benchmark');path(a,'run');path(a,'--out')
    a=s.add_parser('orchestrate');spec(a);out(a);worker(a);a.add_argument('--resume',action='store_true');a.add_argument('--retry-failed',action='store_true')
    s=group('report');a=s.add_parser('create');a.add_argument('kind');a.add_argument('records',type=Path,nargs='+');a.add_argument('--title');a.add_argument('--limitation',action='append',default=[]);out(a)
    a=sub.add_parser('licenses');spec(a);out(a)
    s=group('release')
    a=s.add_parser('prepare');path(a,'root');out(a);a.add_argument('--version',required=True);a.add_argument('--note',action='append',required=True)
    for name in ['counts','sbom','verify','build']:
        a=s.add_parser(name);path(a,'root')
        if name=='build':out(a);a.add_argument('--wheel',action='store_true')
        else:path(a,'--out')
    s=group('docs');a=s.add_parser('generate');out(a)
    a=sub.add_parser('groundwork-fixtures');path(a,'destination')
    return p

def _json(v):
    if isinstance(v,Path):return str(v)
    if hasattr(v,'model_dump'):return v.model_dump(mode='json')
    if isinstance(v,dict):return {str(k):_json(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [_json(x) for x in v]
    return v

def _save(v,out):
    if out:
        from cvsubstrate.provenance.artifact_set import assert_not_inside_sealed
        assert_not_inside_sealed(out)
        if out.exists():raise CVRSError('OUTPUT_EXISTS','JSON output must be new')
        write_json(out,_json(v))
    return v

def _dataset(path):
    from cvsubstrate.contracts.models import DatasetManifest
    return DatasetManifest.model_validate(read_json(path))

def _predictions(path):
    from cvsubstrate.contracts.models import DetectionPrediction
    return [DetectionPrediction.model_validate(r) for r in read_jsonl(path)]

def dispatch(a):
    c=a.command
    op: str | None=getattr(a,'action',None)
    if c=='schema':
        from cvsubstrate.schemas.registry import schema_registry,inspect_schema,validate_artifact,export_schemas
        if op=='list':return {'schemas':sorted(schema_registry()),'count':len(schema_registry())}
        if op=='inspect':return inspect_schema(a.name)
        if op=='validate':return validate_artifact(read_json(a.artifact),a.schema)
        return export_schemas(a.out)
    if c in {'migrate','migrate-run'}:
        from cvsubstrate.schemas.registry import migrate_artifact,migrate_run
        return migrate_artifact(a.source,a.out,schema_name=a.schema) if c=='migrate' else migrate_run(a.source,a.out)
    if c=='plugin':
        from cvsubstrate.adapters.sdk import PluginRegistry,scaffold,negotiate
        from cvsubstrate.contracts.groundwork import PluginDescriptor,CapabilityRequirement
        if op=='scaffold':return scaffold(a.out,a.name,a.kind)
        if op=='negotiate':
            d=read_json(a.spec);return negotiate(CapabilityRequirement.model_validate(d['requirements']),model=d['model'],dataset=d['dataset'],evaluator=d.get('evaluator'))
        if op in {'list','inspect','register'}:
            reg=PluginRegistry(a.registry)
            if op=='list':return reg.list()
            if op=='inspect':return reg.inspect(a.name)
            d=PluginDescriptor.model_validate(read_json(a.descriptor));reg.register(d);return reg.inspect(d.id)
        d=PluginDescriptor.model_validate(read_json(a.descriptor))
        if a.trust_code:d=d.model_copy(update={'trust_code':True})
        if op=='validate':
            from cvsubstrate.execution.services import invoke_service
            result=invoke_service('plugin',{'descriptor':d.model_dump(mode='json'),'operation':'capabilities','payload':{}},worker_python=a.worker_python,timeout=a.timeout)
            return {'status':'CAPABILITIES_EXECUTED','result':result,'note':'Use conformance fixtures for semantic operation validation.'}
        from cvsubstrate.adapters.conformance import execute_plugin,conformance
        if op=='run':return execute_plugin(d,a.operation,read_json(a.payload),a.out,worker_python=a.worker_python,timeout=a.timeout)
        return conformance(d,read_json(a.fixtures),a.out,worker_python=a.worker_python)
    if c=='graph':
        from cvsubstrate.experiments.dag import execute_graph,topological,ACTIONS
        from cvsubstrate.experiments.actions import install_actions
        from cvsubstrate.contracts.groundwork import ExecutionGraph
        install_actions()
        if op=='actions':return {k:{'version':v.version,'cacheable':v.cacheable,'retry_safe':v.retry_safe} for k,v in ACTIONS.items()}
        g=ExecutionGraph.model_validate(read_json(a.spec))
        if op=='plan':return {'graph_digest':digest(g),'order':[n.id for n in topological(g)]}
        return execute_graph(g,a.out,base=a.spec.resolve().parent,cache_root=a.cache,resume=a.resume,invalidate=a.invalidate)
    if c in {'artifact','cache'}:
        from cvsubstrate.artifacts.store import LocalArtifactStore
        store=LocalArtifactStore(a.store)
        if op=='put':return store.put(a.source)
        if op=='get':return {'path':str(store.materialize(a.sha256,a.out))}
        if op=='exists':return {'exists':store.exists(a.sha256)}
        return store.verify(a.sha256)
    if c=='environment':
        from cvsubstrate.environments.capture import capture,import_environment
        if op=='capture':return _save(capture(probe_hardware=a.probe_hardware),a.out)
        if op=='import':return _save(import_environment(a.source,a.kind),a.out)
        from cvsubstrate.heritage.capsule import write_capsule
        d=read_json(a.spec);return write_capsule(a.out,d['python'],d['packages'],source=d.get('source'),base_image=d.get('base_image'))
    if c=='capsule':
        from cvsubstrate.artifacts.capsule import create_capsule,validate_capsule,archive_capsule,materialize_capsule
        if op=='create':return create_capsule(a.source,a.out,include=a.include,external_references=read_json(a.references) if a.references else None,dependency_closure=read_json(a.dependencies) if a.dependencies else None)
        if op=='validate':return validate_capsule(a.source)
        if op=='inspect':return {'validation':validate_capsule(a.source),'manifest':read_json(a.source/'capsule.json')}
        if op=='archive':return archive_capsule(a.source,a.out)
        return materialize_capsule(a.source,a.out)
    if c=='checkpoint':
        from cvsubstrate.checkpoints import inspect_checkpoint,convert_checkpoint
        if op=='inspect':return _save(inspect_checkpoint(read_json(a.spec),worker_python=a.worker_python,timeout=a.timeout),a.out)
        return convert_checkpoint(read_json(a.spec),a.out,worker_python=a.worker_python,timeout=a.timeout)
    if c=='model':
        if op is None:raise ValueError('model action is required')
        if op in {'predict-obb','train-obb'}:
            from cvsubstrate.adapters.oriented import run_oriented_job
            return run_oriented_job(a.spec,a.out,operation='train' if op=='train-obb' else 'predict',worker_python=a.worker_python,timeout=a.timeout)
        if op=='capabilities':
            from cvsubstrate.execution.services import invoke_service
            return invoke_service(a.backend,{'operation':'capabilities'},worker_python=a.worker_python,timeout=a.timeout)
        from cvsubstrate.adapters.modern import native_model_job
        return native_model_job(a.spec,a.out,operation={'train-native':'train'}.get(op,op),worker_python=a.worker_python,timeout=a.timeout)
    if c=='backbone':
        from cvsubstrate.backbones.service import extract_features
        return extract_features(read_json(a.spec),a.out,worker_python=a.worker_python,timeout=a.timeout)
    if c=='deploy':
        from cvsubstrate.deployment.service import execute_deployment
        from cvsubstrate.deployment.compare import compare_arrays,compare_detections,compare_metrics
        if op in {'export','infer'}:return execute_deployment(read_json(a.spec),a.out,operation=op,worker_python=a.worker_python,timeout=a.timeout)
        if op=='decode':
            from cvsubstrate.deployment.decode import decode_outputs
            return decode_outputs(a.run,read_json(a.spec),a.out)
        if op=='compare-arrays':return _save(compare_arrays(a.left,a.right,atol=a.atol,rtol=a.rtol,name_mapping=read_json(a.names) if a.names else None),a.out)
        if op=='compare-detections':return _save(compare_detections(_predictions(a.left),_predictions(a.right)),a.out)
        return _save(compare_metrics(read_json(a.left),read_json(a.right)),a.out)
    if c=='dataset':
        if op=='import':
            from cvsubstrate.datasets.importers import import_dataset
            return import_dataset(read_json(a.spec),a.out)
        if op=='materialize':
            from cvsubstrate.datasets.materialize import materialize_dataset
            return materialize_dataset(a.manifest,a.image_root,a.out,mode=a.mode)
        from cvsubstrate.datasets.geospatial import inspect_raster,build_geo_manifest,export_world_predictions
        if op=='inspect-geo':return _save(inspect_raster(a.source,sidecar=a.sidecar),a.out)
        if op=='geo-manifest':return _save(build_geo_manifest(**read_json(a.spec)),a.out)
        return export_world_predictions(read_jsonl(a.predictions),read_json(a.georeferences),a.out,format=a.format)
    if c=='large':
        if op=='plan':
            from cvsubstrate.data.large import plan_large_image
            return _save(plan_large_image(read_json(a.spec)),a.out)
        if op=='merge':
            from cvsubstrate.geometry.merge import merge_detections
            return _save(merge_detections(read_json(a.detections),read_json(a.policy)),a.out)
        from cvsubstrate.execution.large import run_large
        return run_large(a.spec,a.out,read_json(a.policy),worker_python=a.worker_python,evaluator_python=a.evaluator_python,timeout=a.timeout)
    if c=='size-evaluate':
        from cvsubstrate.evaluation.object_size import size_metrics
        return _save(size_metrics(_dataset(a.dataset),a.split,_predictions(a.predictions),read_json(a.policy),iou=a.iou,threshold=a.threshold,gsd_by_image=read_json(a.gsd) if a.gsd else None),a.out)
    if c=='slice':
        from cvsubstrate.analysis.slices import select_slice
        return _save(select_slice(_dataset(a.dataset),a.split,read_json(a.policy),metadata=read_json(a.metadata) if a.metadata else None),a.out)
    if c=='distribution':
        from cvsubstrate.analysis.distributions import distribution_report,compare_distributions,compare_embeddings
        if op=='describe':return _save(distribution_report(_dataset(a.dataset),a.split,root=a.dataset.resolve().parent,metadata=read_json(a.metadata) if a.metadata else None,image_stats=a.image_stats),a.out)
        if op=='compare':return _save(compare_distributions(read_json(a.left),read_json(a.right)),a.out)
        return _save(compare_embeddings(a.left,a.right,left_descriptor=read_json(a.left_descriptor),right_descriptor=read_json(a.right_descriptor)),a.out)
    if c=='synthetic':
        if op=='ingest':
            from cvsubstrate.data.simulator_sdk import import_export
            return import_export(a.source,read_json(a.mapping),a.out)
        from cvsubstrate.contracts.synthetic import SyntheticSampleManifest
        d=SyntheticSampleManifest.model_validate(read_json(a.source));return {'status':'VALID','digest':digest(d)}
    if c=='campaign' or (c=='benchmark' and op=='orchestrate'):
        from cvsubstrate.contracts.groundwork import ResearchCampaign
        from cvsubstrate.campaigns.dsl import compile_campaign,check_budgets,execute_research_campaign,expand_sweep
        d=read_json(a.spec)
        if op=='compile':return _save(compile_campaign(d,a.spec.resolve().parent),a.out)
        if op=='budgets':return _save(check_budgets(ResearchCampaign.model_validate(d)),a.out)
        if op=='sweep':return expand_sweep(d,read_json(a.axes),a.out,max_cases=a.max_cases)
        return execute_research_campaign(a.spec,a.out,resume=a.resume,retry_failed=a.retry_failed,worker_python=a.worker_python,timeout=a.timeout)
    if c=='heritage':
        from cvsubstrate.heritage.profiles import PROFILES
        if op=='profiles':return PROFILES
        if op=='train-native':
            from cvsubstrate.heritage.training import train_native
            return train_native(read_json(a.spec),a.out,worker_python=a.worker_python,timeout=a.timeout)
        if op=='certify-training':
            from cvsubstrate.heritage.training import certify_training
            return certify_training(read_json(a.spec),a.out)
        if op=='import':
            from cvsubstrate.heritage.wizard import import_wizard
            d=read_json(a.spec)
            for k in ['config','source_root','checkpoint','dataset']:d[k]=Path(d[k])
            return import_wizard(**d,output=a.out)
        if op=='graph':
            from cvsubstrate.heritage.importer import config_graph
            return _save(config_graph(a.config,a.source_root),a.out)
        if op=='convert-predictions':
            from cvsubstrate.evaluation.converters import convert_results
            return convert_results(read_json(a.native),format=a.format,category_map=read_json(a.mapping),output=a.out,manifest=_dataset(a.dataset) if a.dataset else None,split=a.split,image_id_map=read_json(a.image_id_map) if a.image_id_map else None,angle_convention=read_json(a.angle_convention) if a.angle_convention else None)
        if op=='trusted-import':
            from cvsubstrate.execution.services import invoke_service
            return _save(invoke_service('unsafe_import',read_json(a.spec),worker_python=a.worker_python,timeout=a.timeout),a.out)
        from cvsubstrate.heritage.catalogue_tools import search_catalogue,add_entry,generate_docs
        if a.catalogue_action=='add':return add_entry(a.catalogue,read_json(a.entry),a.out)
        if a.catalogue_action=='docs':return generate_docs(a.catalogue,a.out)
        return search_catalogue(a.catalogue,getattr(a,'query',''))
    if c=='benchmark':
        from cvsubstrate.benchmarks.registry import register_benchmark,list_benchmarks,preregister_selection,authorize_final,final_evaluate,validate_submission
        if op=='register':return register_benchmark(read_json(a.spec),a.registry)
        if op=='list':return list_benchmarks(a.registry)
        if op=='preregister':return _save(preregister_selection(**read_json(a.spec),ledger=a.ledger),a.out)
        if op=='authorize-final':return _save(authorize_final(**read_json(a.spec),ledger_path=a.ledger),a.out)
        if op=='final-eval':return {'run':str(final_evaluate(a.benchmark,a.experiment,a.ledger,a.approval_digest,a.out,worker_python=a.worker_python,evaluator_python=a.evaluator_python,timeout=a.timeout))}
        if op=='submission-check':return _save(validate_submission(read_json(a.benchmark),a.run),a.out)
        from cvsubstrate.governance.ledger import Ledger
        from cvsubstrate.governance.policy import final_test_report
        return final_test_report(Ledger(a.ledger))
    if c=='report':
        from cvsubstrate.reporting.formal import create_report
        return create_report(a.kind,[read_json(p) for p in a.records],a.out,title=a.title,limitations=a.limitation)
    if c=='licenses':
        from cvsubstrate.licensing import license_report
        return license_report(read_json(a.spec),a.out)
    if c=='release':
        if op is None:raise ValueError('release action is required')
        if op=='prepare':
            from cvsubstrate.release import prepare_release
            return prepare_release(a.root,a.out,a.version,a.note)
        from cvsubstrate.release import line_counts,sbom,verify_release,package_release
        if op=='build':return package_release(a.root,a.out,build_wheel=a.wheel)
        return _save({'counts':line_counts,'sbom':sbom,'verify':verify_release}[op](a.root),a.out)
    if c=='docs':
        from cvsubstrate.documentation import generate_reference
        return generate_reference(a.out)
    if c=='groundwork-fixtures':
        from cvsubstrate.data.groundwork_fixtures import generate
        return generate(a.destination)
    raise ValueError('unknown command')

def main(argv):
    a=parser().parse_args(argv)
    try:
        value=_json(dispatch(a));print(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False))
        return 2 if isinstance(value,dict) and value.get('status') in {'FAILED','INVALID','INFEASIBLE','UNSATISFIABLE','FAIL'} else 0
    except (KeyboardInterrupt,SystemExit):raise
    except Exception as exc:
        from cvsubstrate.security import sanitize
        print(json.dumps({'status':'FAILED','error':{'code':getattr(exc,'code','DEPENDENCY_UNAVAILABLE' if isinstance(exc,ImportError) else type(exc).__name__),'message':sanitize(str(exc))}},ensure_ascii=False,allow_nan=False),file=sys.stderr);return 2
