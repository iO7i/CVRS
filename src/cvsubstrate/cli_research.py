"""Opt-in research/heritage commands. Optional ML/geo dependencies stay lazy."""
from pathlib import Path
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import read_json, write_json, read_jsonl


def add_commands(sub):
    a=sub.add_parser('run-tiled',help='Real worker inference on tiles; merge/evaluate in source-image coordinates')
    a.add_argument('spec',type=Path);a.add_argument('--policy',type=Path,required=True)
    a.add_argument('--out',type=Path,required=True);a.add_argument('--worker-python');a.add_argument('--timeout',type=float,default=180.)
    a=sub.add_parser('heritage-import',help='Preserve a config closure without executing its Python code')
    a.add_argument('config',type=Path);a.add_argument('--source-root',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    a.add_argument('--upstream',required=True);a.add_argument('--revision',required=True);a.add_argument('--checkpoint',type=Path);a.add_argument('--dataset',type=Path)
    a=sub.add_parser('heritage-graph');a.add_argument('config',type=Path);a.add_argument('--source-root',type=Path,required=True)
    a=sub.add_parser('import-predictions',help='Safe JSON-native output import; never load arbitrary pickle')
    a.add_argument('native',type=Path);a.add_argument('--dataset',type=Path,required=True);a.add_argument('--split',default='dev')
    a.add_argument('--mapping',type=Path,required=True);a.add_argument('--format',choices=['mmdet2_bbox','mmdet3_instances'],required=True);a.add_argument('--out',type=Path,required=True)
    a=sub.add_parser('catalogue');a.add_argument('catalogue',type=Path);a.add_argument('--source-root',type=Path)
    a=sub.add_parser('capsule');a.add_argument('--out',type=Path,required=True);a.add_argument('--packages',nargs='+',default=['pydantic','torch','torchvision','mmcv','mmdet','pycocotools']);a.add_argument('--declaration',type=Path);a.add_argument('--base-image')
    a=sub.add_parser('synthetic');s=a.add_subparsers(dest='action',required=True)
    b=s.add_parser('map');b.add_argument('source',type=Path);b.add_argument('--mapping',type=Path,required=True);b.add_argument('--out',type=Path,required=True)
    b=s.add_parser('validate');b.add_argument('record',type=Path)
    b=s.add_parser('migrate');b.add_argument('source',type=Path);b.add_argument('--sample-id',required=True);b.add_argument('--out',type=Path,required=True)
    a=sub.add_parser('domain');s=a.add_subparsers(dest='action',required=True)
    b=s.add_parser('describe');b.add_argument('dataset',type=Path);b.add_argument('--split',default='dev');b.add_argument('--sidecars',type=Path);b.add_argument('--out',type=Path)
    b=s.add_parser('compare');b.add_argument('left',type=Path);b.add_argument('right',type=Path);b.add_argument('--out',type=Path)
    a=sub.add_parser('tiny-evaluate');a.add_argument('predictions',type=Path);a.add_argument('--dataset',type=Path,required=True);a.add_argument('--split',default='dev');a.add_argument('--policy',type=Path);a.add_argument('--out',type=Path)
    a=sub.add_parser('audit-predictions');a.add_argument('left',type=Path);a.add_argument('right',type=Path);a.add_argument('--box-atol',type=float,default=1e-5);a.add_argument('--score-atol',type=float,default=1e-6);a.add_argument('--order',choices=['as_emitted','canonical_sort'],default='as_emitted');a.add_argument('--out',type=Path)
    a=sub.add_parser('dota');s=a.add_subparsers(dest='action',required=True)
    b=s.add_parser('import');b.add_argument('--images',type=Path,required=True);b.add_argument('--labels',type=Path,required=True);b.add_argument('--categories',type=Path,required=True);b.add_argument('--name',required=True);b.add_argument('--dataset-version',required=True);b.add_argument('--role',choices=['train','dev','locked_test'],default='dev');b.add_argument('--out',type=Path,required=True)
    b=s.add_parser('validate');b.add_argument('dataset',type=Path);b.add_argument('--metadata-only',action='store_true')
    b=s.add_parser('export');b.add_argument('predictions',type=Path);b.add_argument('--dataset',type=Path,required=True);b.add_argument('--out',type=Path,required=True)
    b=s.add_parser('diagnostic');b.add_argument('predictions',type=Path);b.add_argument('--dataset',type=Path,required=True);b.add_argument('--iou',type=float,default=.5);b.add_argument('--score',type=float,default=.5);b.add_argument('--out',type=Path)
    b=s.add_parser('reference');b.add_argument('predictions',type=Path);b.add_argument('--dataset',type=Path,required=True);b.add_argument('--reference',type=Path,required=True);b.add_argument('--out',type=Path,required=True);b.add_argument('--worker-python');b.add_argument('--timeout',type=float,default=180.)
    a=sub.add_parser('geotiff');s=a.add_subparsers(dest='action',required=True)
    b=s.add_parser('inspect');b.add_argument('source',type=Path)
    b=s.add_parser('window');b.add_argument('source',type=Path);b.add_argument('--out',type=Path,required=True);b.add_argument('--window',type=int,nargs=4,required=True,metavar=('X','Y','WIDTH','HEIGHT'));b.add_argument('--bands',type=int,nargs=3,required=True);b.add_argument('--value-range',type=float,nargs=2,required=True)
    a=sub.add_parser('campaign');s=a.add_subparsers(dest='action',required=True)
    b=s.add_parser('plan');b.add_argument('spec',type=Path);b.add_argument('--out',type=Path)
    b=s.add_parser('run');b.add_argument('spec',type=Path);b.add_argument('--out',type=Path,required=True);b.add_argument('--resume',action='store_true');b.add_argument('--retry-failed',action='store_true');b.add_argument('--worker-python')
    b=s.add_parser('report');b.add_argument('campaign',type=Path);b.add_argument('--out',type=Path)
    a=sub.add_parser('ledger');s=a.add_subparsers(dest='action',required=True)
    b=s.add_parser('verify');b.add_argument('ledger',type=Path);b.add_argument('--expected-head')
    b=s.add_parser('test-report');b.add_argument('ledger',type=Path)
    b=s.add_parser('approve');b.add_argument('ledger',type=Path);b.add_argument('--approval',type=Path,required=True)
    b=s.add_parser('final-run');b.add_argument('spec',type=Path);b.add_argument('--ledger',type=Path,required=True);b.add_argument('--approval-digest',required=True);b.add_argument('--out',type=Path,required=True);b.add_argument('--worker-python');b.add_argument('--timeout',type=float,default=180.)
    a=sub.add_parser('recover');a.add_argument('run',type=Path);a.add_argument('--reason',required=True);a.add_argument('--acknowledge-process-stopped',action='store_true')
    a=sub.add_parser('artifact-verify');a.add_argument('directory',type=Path)
    a=sub.add_parser('research-fixtures',help='Create portable fixture profiles and a six-arm campaign, without executing models')
    a.add_argument('destination',type=Path)


def _predictions(path,oriented=False):
    from cvsubstrate.contracts.models import DetectionPrediction
    from cvsubstrate.contracts.research import OrientedPrediction
    p=Path(path);p=p/'predictions.jsonl' if p.is_dir() else p
    cls=OrientedPrediction if oriented else DetectionPrediction
    return [cls.model_validate(r) for r in read_jsonl(p)]


def _save(payload,out=None):
    if out is not None:
        from cvsubstrate.reporting.research import publish_report
        publish_report(payload,out)
    return payload


def dispatch(args):
    c=args.command
    if c=='run-tiled':
        from cvsubstrate.execution.tiled import run_tiled
        from cvsubstrate.contracts.research import TilingPolicy
        from cvsubstrate.provenance.bundle import verify_bundle
        run=run_tiled(args.spec,TilingPolicy.model_validate(read_json(args.policy)),args.out,worker_python=args.worker_python,timeout=args.timeout)
        return {'run':str(run),'verification':verify_bundle(run)}
    if c=='heritage-import':
        from cvsubstrate.heritage.importer import import_project
        return import_project(args.config,args.source_root,args.out,upstream=args.upstream,revision=args.revision,checkpoint=args.checkpoint,dataset=args.dataset)
    if c=='heritage-graph':
        from cvsubstrate.heritage.importer import config_graph
        return config_graph(args.config,args.source_root)
    if c=='import-predictions':
        from cvsubstrate.heritage.importer import import_predictions
        return import_predictions(args.native,args.dataset,args.split,read_json(args.mapping),args.out,native_format=args.format)
    if c=='catalogue':
        from cvsubstrate.heritage.catalogue import compatibility_matrix
        return compatibility_matrix(args.catalogue,local_source_root=args.source_root)
    if c=='capsule':
        from cvsubstrate.heritage.capsule import capsule_from_snapshot,write_capsule
        if args.declaration:
            d=read_json(args.declaration)
            return write_capsule(args.out,d['python'],d['packages'],source=d.get('source'),base_image=args.base_image)
        return capsule_from_snapshot(args.out,args.packages,base_image=args.base_image)
    if c=='synthetic':
        from cvsubstrate.contracts.research import SyntheticRecord,SidecarMapping
        if args.action=='validate':
            from cvsubstrate.provenance.io import digest
            value=SyntheticRecord.model_validate(read_json(args.record));return {'status':'VALID','record_digest':digest(value)}
        if args.action=='migrate':
            from cvsubstrate.contracts.migrations import migrate_generation
            return migrate_generation(args.source,args.out,sample_id=args.sample_id)
        from cvsubstrate.data.synthetic import import_sidecar
        return import_sidecar(args.source,SidecarMapping.model_validate(read_json(args.mapping)),args.out)
    if c=='domain':
        from cvsubstrate.analysis.domain import describe_dataset,compare_domains
        from cvsubstrate.contracts.research import SyntheticRecord
        from cvsubstrate.data.manifest import load_manifest
        if args.action=='compare':return _save(compare_domains(read_json(args.left),read_json(args.right)),args.out)
        sidecars=[SyntheticRecord.model_validate(r) for r in read_jsonl(args.sidecars)] if args.sidecars else None
        return _save(describe_dataset(load_manifest(args.dataset),args.split,sidecars),args.out)
    if c=='tiny-evaluate':
        from cvsubstrate.data.manifest import load_manifest
        from cvsubstrate.contracts.research import TinyEvaluationPolicy
        from cvsubstrate.evaluation.tiny import tiny_diagnostics
        return _save(tiny_diagnostics(load_manifest(args.dataset),args.split,_predictions(args.predictions),TinyEvaluationPolicy.model_validate(read_json(args.policy)) if args.policy else TinyEvaluationPolicy()),args.out)
    if c=='audit-predictions':
        from cvsubstrate.evaluation.prediction_parity import audit_predictions
        return _save(audit_predictions(_predictions(args.left),_predictions(args.right),box_atol=args.box_atol,score_atol=args.score_atol,order=args.order),args.out)
    if c=='dota':
        from cvsubstrate.contracts.models import Category
        from cvsubstrate.contracts.research import OrientedDataset
        from cvsubstrate.data.dota import import_dota,validate_oriented_dataset,export_task1
        if args.action=='import':
            if args.out.exists():raise CVRSError('OUTPUT_EXISTS','DOTA manifest must be new')
            if args.out.resolve().parent!=args.images.resolve():raise CVRSError('MANIFEST_ROOT','place oriented manifest at image root')
            cats=[Category.model_validate(v) for v in read_json(args.categories)]
            m=import_dota(args.images,args.labels,categories=cats,name=args.name,version=args.dataset_version,role=args.role)
            write_json(args.out,m);return validate_oriented_dataset(m,args.images)
        m=OrientedDataset.model_validate(read_json(args.dataset))
        if args.action=='validate':return validate_oriented_dataset(m,None if args.metadata_only else args.dataset.resolve().parent)
        rows=_predictions(args.predictions,True)
        if args.action=='export':return export_task1(m,rows,args.out)
        if args.action=='reference':
            from cvsubstrate.evaluation.reference_dota import run_reference,DotaReference
            return run_reference(m,rows,DotaReference.model_validate(read_json(args.reference)),args.out,worker_python=args.worker_python,timeout=args.timeout)
        from cvsubstrate.evaluation.oriented import oriented_diagnostics
        return _save(oriented_diagnostics(m,rows,iou_threshold=args.iou,score_threshold=args.score),args.out)
    if c=='geotiff':
        from cvsubstrate.data.geotiff import inspect_geotiff,export_window
        if args.action=='inspect':return inspect_geotiff(args.source)
        return export_window(args.source,args.out,window=args.window,bands=args.bands,value_range=args.value_range)
    if c=='campaign':
        from cvsubstrate.campaigns.engine import load_campaign,plan_campaign,execute_campaign
        if args.action=='run':return execute_campaign(args.spec,args.out,resume=args.resume,retry_failed=args.retry_failed,worker_python=args.worker_python)
        if args.action=='plan':return _save(plan_campaign(load_campaign(args.spec),args.spec.resolve().parent),args.out)
        from cvsubstrate.campaigns.report import campaign_report
        return _save(campaign_report(args.campaign),args.out)
    if c=='ledger':
        from cvsubstrate.governance.ledger import Ledger
        from cvsubstrate.governance.policy import approve_final_test,final_test_report
        from cvsubstrate.contracts.research import AccessApproval
        ledger=Ledger(args.ledger)
        if args.action=='verify':return ledger.verify(args.expected_head)
        if args.action=='test-report':return final_test_report(ledger)
        if args.action=='approve':return approve_final_test(ledger,AccessApproval.model_validate(read_json(args.approval)))
        from cvsubstrate.governance.execution import run_final_test
        return run_final_test(args.spec,args.out,ledger,args.approval_digest,worker_python=args.worker_python,timeout=args.timeout)
    if c=='recover':
        from cvsubstrate.provenance.recovery import recover_interrupted_run
        return recover_interrupted_run(args.run,reason=args.reason,acknowledge_process_stopped=args.acknowledge_process_stopped)
    if c=='artifact-verify':
        from cvsubstrate.provenance.artifact_set import verify_directory
        return verify_directory(args.directory)
    if c=='research-fixtures':
        from cvsubstrate.data.research_fixtures import generate_research_fixtures
        return generate_research_fixtures(args.destination)
    raise AssertionError('unhandled research command')
