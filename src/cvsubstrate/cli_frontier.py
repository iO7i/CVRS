"""Slice4/5 and engineering-closure command surfaces. No native imports at startup."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from cvsubstrate.provenance.io import read_json,read_jsonl,write_json
from cvsubstrate.errors import CVRSError
ROOTS={'telemetry','stream','vision','quantize','research-registry','detector-deploy','adapter-recipes'}
def handles(argv):return bool(argv) and argv[0] in ROOTS

def parser():
    p=argparse.ArgumentParser(prog='cvrs');groups=p.add_subparsers(dest='group',required=True)
    g=groups.add_parser('telemetry').add_subparsers(dest='action',required=True)
    a=g.add_parser('inspect');a.add_argument('ledger',type=Path)
    a=g.add_parser('aggregate');a.add_argument('ledgers',nargs='+',type=Path);a.add_argument('--expected-ranks',type=int,required=True)
    g=groups.add_parser('stream').add_subparsers(dest='action',required=True)
    a=g.add_parser('plan');a.add_argument('spec',type=Path);a.add_argument('--width',type=int,required=True);a.add_argument('--height',type=int,required=True);a.add_argument('--first',type=int,default=5)
    a=g.add_parser('run');a.add_argument('spec',type=Path);a.add_argument('--out',type=Path,required=True);a.add_argument('--worker-python');a.add_argument('--timeout',type=float,default=600)
    a.add_argument('--resume',action='store_true');a.add_argument('--stop-after-tiles',type=int)
    g=groups.add_parser('vision').add_subparsers(dest='action',required=True)
    a=g.add_parser('run');a.add_argument('spec',type=Path);a.add_argument('--out',type=Path,required=True);a.add_argument('--worker-python');a.add_argument('--timeout',type=float,default=600)
    a=g.add_parser('evaluate-prompts');a.add_argument('spec',type=Path)
    a=g.add_parser('evaluate-masks');a.add_argument('spec',type=Path);a.add_argument('--evaluator-python')
    a=g.add_parser('map-grounding');a.add_argument('predictions',type=Path);a.add_argument('--mapping',type=Path,required=True)
    a=g.add_parser('compare');a.add_argument('reports',nargs='+',type=Path)
    a=g.add_parser('transform-mask');a.add_argument('mask',type=Path);a.add_argument('--transform',type=Path,required=True)
    g=groups.add_parser('quantize').add_subparsers(dest='action',required=True)
    a=g.add_parser('validate');a.add_argument('spec',type=Path)
    a=g.add_parser('run');a.add_argument('spec',type=Path);a.add_argument('--out',type=Path,required=True);a.add_argument('--worker-python');a.add_argument('--timeout',type=float,default=600)
    a=g.add_parser('prepare');a.add_argument('spec',type=Path);a.add_argument('--out',type=Path,required=True)
    a=g.add_parser('regression');a.add_argument('baseline',type=Path);a.add_argument('quantized',type=Path);a.add_argument('--limits',type=Path,required=True)
    g=groups.add_parser('detector-deploy').add_subparsers(dest='action',required=True)
    a=g.add_parser('profile');a.add_argument('spec',type=Path)
    a=g.add_parser('infer');a.add_argument('spec',type=Path);a.add_argument('--out',type=Path,required=True);a.add_argument('--worker-python');a.add_argument('--timeout',type=float,default=600)
    a=g.add_parser('export-mm');a.add_argument('spec',type=Path);a.add_argument('--out',type=Path,required=True);a.add_argument('--worker-python');a.add_argument('--timeout',type=float,default=600)
    g=groups.add_parser('adapter-recipes').add_subparsers(dest='action',required=True)
    g.add_parser('list');a=g.add_parser('show');a.add_argument('name')
    a=g.add_parser('scaffold');a.add_argument('out',type=Path)
    registry=groups.add_parser('research-registry');g=registry.add_subparsers(dest='action',required=True)
    for name in ['init','verify','list']:
        a=g.add_parser(name);a.add_argument('registry',type=Path)
        if name=='list':a.add_argument('--kind',choices=['claim','attempt','review'])
    for name in ['claim','attempt','review']:
        a=g.add_parser(name);a.add_argument('registry',type=Path);a.add_argument('spec',type=Path)
    a=g.add_parser('evidence');a.add_argument('registry',type=Path);a.add_argument('file',type=Path);a.add_argument('--media-type',default='application/octet-stream');a.add_argument('--license-status',default='UNKNOWN')
    a=g.add_parser('status');a.add_argument('registry',type=Path);a.add_argument('claim_id')
    a=g.add_parser('supersede');a.add_argument('registry',type=Path);a.add_argument('old');a.add_argument('new');a.add_argument('--reason',required=True)
    a=g.add_parser('export');a.add_argument('registry',type=Path);a.add_argument('--out',type=Path,required=True)
    a=g.add_parser('import');a.add_argument('snapshot',type=Path);a.add_argument('--out',type=Path,required=True)
    a=g.add_parser('capsule');a.add_argument('registry',type=Path);a.add_argument('--out',type=Path,required=True);a.add_argument('--archive',type=Path)
    a=g.add_parser('restore');a.add_argument('archive',type=Path);a.add_argument('--out',type=Path,required=True)
    a=g.add_parser('capture-run');a.add_argument('registry',type=Path);a.add_argument('run',type=Path);a.add_argument('--dataset',type=Path,required=True);a.add_argument('--metadata',type=Path,required=True)
    a=g.add_parser('reevaluate');a.add_argument('--dataset',type=Path,required=True);a.add_argument('--predictions',type=Path,required=True);a.add_argument('--protocol',type=Path,required=True);a.add_argument('--split',default='dev');a.add_argument('--out',type=Path,required=True);a.add_argument('--evaluator-python');a.add_argument('--origin')
    return p

def execute(a):
    if a.group=='telemetry':
        from cvsubstrate.telemetry import summarize_telemetry,aggregate_telemetry
        return summarize_telemetry(a.ledger) if a.action=='inspect' else aggregate_telemetry(a.ledgers,expected_ranks=list(range(a.expected_ranks)))
    if a.group=='stream':
        if a.action=='plan':
            from cvsubstrate.streaming.raster import StreamSpec,plan_tiles
            from dataclasses import asdict
            import itertools
            value=read_json(a.spec)
            if 'model' in value:
                from cvsubstrate.provenance.io import digest
                native=value.pop('model');value['model_identity']=digest({k:v for k,v in native.items() if k!='checkpoint'})
            s=StreamSpec(**value);s.validate()
            if a.first<0 or a.first>1000:raise ValueError('first tile preview must be 0..1000')
            tiles=list(itertools.islice(plan_tiles(a.width,a.height,s),a.first))
            return {'plan':asdict(s),'preview':[asdict(t) for t in tiles],'materializes_whole_scene':False,'memory_limit_scope':'CVRS pixel queues and configured SQLite/GDAL caches, excluding model/process/driver allocations'}
        from cvsubstrate.streaming.service import stream_job
        return stream_job(a.spec,a.out,worker_python=a.worker_python,timeout=a.timeout,resume=a.resume,max_tiles=a.stop_after_tiles)
    if a.group=='vision':
        if a.action=='run':
            from cvsubstrate.vision.service import vision_job
            return vision_job(a.spec,a.out,worker_python=a.worker_python,timeout=a.timeout)
        if a.action=='evaluate-prompts':
            from cvsubstrate.vision.masks import evaluate_prompt_masks
            from cvsubstrate.contracts.frontier import MaskPrediction,MaskAnnotation
            s=read_json(a.spec);return evaluate_prompt_masks([MaskPrediction.model_validate(x) for x in s['predictions']],[MaskAnnotation.model_validate(x) for x in s['annotations']],s['pairs'])
        if a.action=='evaluate-masks':
            from cvsubstrate.vision.evaluation import evaluate_masks
            return evaluate_masks(**read_json(a.spec),worker_python=a.evaluator_python)
        if a.action=='map-grounding':
            from cvsubstrate.vision.grounding import map_grounded
            from cvsubstrate.contracts.frontier import GroundedPrediction
            rows=[map_grounded(GroundedPrediction.model_validate(x),read_json(a.mapping)) for x in read_jsonl(a.predictions)]
            return {'predictions':[p.model_dump(mode='json') for p,audit in rows],'audits':[audit for p,audit in rows]}
        if a.action=='compare':
            from cvsubstrate.vision.grounding import cross_paradigm_report
            return cross_paradigm_report([read_json(p) for p in a.reports])
        if a.action=='transform-mask':
            from cvsubstrate.vision.masks import transform_mask
            from cvsubstrate.contracts.frontier import MaskRLE
            return transform_mask(MaskRLE.model_validate(read_json(a.mask)),**read_json(a.transform)).model_dump(mode='json')
    if a.group=='quantize':
        if a.action=='prepare':
            from cvsubstrate.deployment.calibration import prepare_calibration
            return prepare_calibration(read_json(a.spec),a.out)
        if a.action=='regression':
            from cvsubstrate.deployment.calibration import accuracy_regression
            return accuracy_regression(read_json(a.baseline),read_json(a.quantized),read_json(a.limits))
        from cvsubstrate.deployment.quantization import validate_calibration,quantize
        return validate_calibration(read_json(a.spec)) if a.action=='validate' else quantize(a.spec,a.out,worker_python=a.worker_python,timeout=a.timeout)
    if a.group=='detector-deploy':
        if a.action=='profile':
            from cvsubstrate.deployment.profiles import DetectorProfile
            from dataclasses import asdict
            p=DetectorProfile(**read_json(a.spec));p.validate();return {'profile':asdict(p),'native_execution_verified':False}
        if a.action=='infer':
            from cvsubstrate.deployment.detector_job import run_detector_deployment
            return run_detector_deployment(a.spec,a.out,worker_python=a.worker_python,timeout=a.timeout)
        from cvsubstrate.deployment.export_profiles import export_mmdeploy
        return export_mmdeploy(read_json(a.spec),a.out,worker_python=a.worker_python,timeout=a.timeout)
    if a.group=='adapter-recipes':
        from cvsubstrate.adapters.recipes import recipes,recipe,scaffold_vision_adapter
        return recipes() if a.action=='list' else recipe(a.name) if a.action=='show' else scaffold_vision_adapter(a.out)
    if a.group=='research-registry':
        from cvsubstrate.research.registry import ResearchRegistry,import_snapshot
        if a.action=='import':return import_snapshot(a.snapshot,a.out)
        if a.action=='capsule':
            from cvsubstrate.research.capsule import export_registry_capsule
            return export_registry_capsule(a.registry,a.out,a.archive)
        if a.action=='restore':
            from cvsubstrate.research.capsule import import_registry_capsule
            return import_registry_capsule(a.archive,a.out)
        if a.action=='capture-run':
            from cvsubstrate.research.capture import capture_run
            return capture_run(a.registry,a.run,a.dataset,**read_json(a.metadata))
        if a.action=='reevaluate':
            from cvsubstrate.research.reevaluate import reevaluate
            return reevaluate(a.dataset,a.split,a.predictions,a.protocol,a.out,worker_python=a.evaluator_python,origin=a.origin)
        if a.action!='init' and not (a.registry/'registry.sqlite').is_file():raise ValueError('registry missing; initialize explicitly')
        with ResearchRegistry(a.registry) as reg:
            if a.action=='init':return {'status':'INITIALIZED','registry':str(a.registry),'verification':reg.verify()}
            if a.action=='verify':return reg.verify()
            if a.action=='list':return reg.list(a.kind)
            if a.action in {'claim','attempt','review'}:
                fn={'claim':reg.register_claim,'attempt':reg.register_attempt,'review':reg.register_review}[a.action]
                return {'id':fn(read_json(a.spec)),'kind':a.action}
            if a.action=='evidence':return {'sha256':reg.add_file(a.file,media_type=a.media_type,license_status=a.license_status)}
            if a.action=='status':return reg.status(a.claim_id)
            if a.action=='supersede':return reg.supersede(a.old,a.new,a.reason)
            if a.action=='export':return reg.export(a.out)
    raise ValueError('unsupported command')

def main(argv):
    a=parser().parse_args(argv)
    try:
        result=execute(a);print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False));return 0
    except (ValueError,KeyError,OSError,TypeError,RuntimeError,CVRSError) as exc:
        print(json.dumps({'status':'FAILED','error':{'code':getattr(exc,'code',type(exc).__name__),'message':str(exc)}},ensure_ascii=False),file=sys.stderr);return 2
