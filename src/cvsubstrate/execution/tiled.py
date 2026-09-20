"""Real process-isolated tiled inference, evaluated on source-image ground truth."""
from pathlib import Path
import time
from cvsubstrate.contracts.models import ExperimentSpec, WorkerRequest, DetectionPrediction
from cvsubstrate.contracts.research import TilingPolicy
from cvsubstrate.data.manifest import load_manifest
from cvsubstrate.data.tiled import materialize_tiles,merge_tile_predictions
from cvsubstrate.evaluation.metrics import evaluate
from cvsubstrate.execution.plugins import invoke_configured
from cvsubstrate.execution.runner import load_experiment,_worker_experiment,_copy_worker_evidence
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.bundle import RunBundle,environment_snapshot,source_snapshot
from cvsubstrate.provenance.io import digest,experiment_identity,file_digest,read_jsonl,write_json,write_jsonl,atomic_bytes
from cvsubstrate.reporting.markdown import render_report


def run_tiled(path: Path, policy: TilingPolicy, output_root: Path, *, worker_python=None, timeout=180.0):
    original,m,dataset_path=load_experiment(path)
    if original.training is not None:
        raise CVRSError('TILED_TRAINING_UNSUPPORTED','tiled execution is inference only; use an explicit checkpoint')
    if m.splits[original.eval_split].role!='dev':
        raise CVRSError('EVAL_ROLE','tiled inference currently accepts dev only; no locked-test policy bypass')
    if original.evaluation.evaluator=='pycocotools':
        import importlib.metadata
        try:version=importlib.metadata.version('pycocotools')
        except importlib.metadata.PackageNotFoundError as exc:
            raise CVRSError('COCO_DEPENDENCY','install pinned reference evaluator; no diagnostic fallback') from exc
        if version!=original.evaluation.evaluator_version:raise CVRSError('EVALUATOR_VERSION','wrong reference version')
    value=original.model_dump(mode='json')
    value['preprocessing']={**value['preprocessing'],'controller_tiling':policy.model_dump(mode='json')}
    value['evaluation']['tile_merge_policy']={'kind':'tiled_hbb_v1','policy':policy.model_dump(mode='json')}
    spec=ExperimentSpec.model_validate(value)
    ck=None
    if spec.checkpoint:
        cp=Path(spec.checkpoint.path);cp=cp if cp.is_absolute() else Path(path).resolve().parent/cp
        if not cp.is_file() or file_digest(cp)!=spec.checkpoint.sha256:raise CVRSError('CHECKPOINT_HASH','checkpoint missing/changed')
        ck={**spec.checkpoint.model_dump(mode='json'),'path':str(cp.resolve())}
    bundle=RunBundle(Path(output_root).resolve(),experiment_identity(spec),digest(m));start=time.perf_counter()
    try:
        write_json(bundle.path/'experiment.json',spec);write_json(bundle.path/'caller_experiment.json',original)
        write_json(bundle.path/'dataset_manifest.json',m);write_json(bundle.path/'environment.json',environment_snapshot())
        write_json(bundle.path/'source.json',source_snapshot())
        tm,plan=materialize_tiles(m,spec.eval_split,dataset_path.parent,bundle.path/'tiles',policy)
        write_json(bundle.path/'tiling_plan.json',plan)
        native=_worker_experiment(spec,Path(path));native['dataset']=str(bundle.path/'tiles'/'dataset.json')
        native['dataset_sha256']=digest(tm);native['eval_split']='tiles';native['training']=None
        native['preprocessing']=original.preprocessing
        native['evaluation']['tile_merge_policy']={'kind':'none'}
        request=WorkerRequest(operation='predict',experiment=native,manifest=tm.model_dump(mode='json'),
            data_root=str(bundle.path/'tiles'),output_dir=str(bundle.path/'worker'),checkpoint=ck)
        cap=invoke_configured(spec.adapter,WorkerRequest(operation='capabilities'),worker_python,min(timeout,45),bundle.path/'capabilities.log')
        write_json(bundle.path/'adapter.json',cap.result)
        if not cap.result.get('installed') or 'predict' not in cap.result.get('operations',[]):
            raise CVRSError('ADAPTER_CAPABILITY','configured worker cannot run inference')
        if spec.adapter.name=='mmdetection':
            validation=invoke_configured(spec.adapter,request.model_copy(update={'operation':'validate'}),worker_python,min(timeout,90),bundle.path/'heritage-validate.log')
            write_json(bundle.path/'heritage_validation.json',validation.result)
        response=invoke_configured(spec.adapter,request,worker_python,timeout,bundle.path/'worker.log')
        write_json(bundle.path/'worker_result.json',response.result);_copy_worker_evidence(bundle,response.result)
        preds=[DetectionPrediction.model_validate(row) for row in read_jsonl(bundle.path/'worker'/'predictions.jsonl')]
        merged,audit=merge_tile_predictions(m,spec.eval_split,plan,preds,policy)
        write_jsonl(bundle.path/'predictions.jsonl',merged);write_json(bundle.path/'merge_audit.json',audit)
        metrics=evaluate(m,spec.eval_split,merged,spec.evaluation);write_json(bundle.path/'metrics.json',metrics)
        write_json(bundle.path/'timing.json',{'end_to_end_wall_seconds':time.perf_counter()-start,
            'gpu_time_seconds':None,'scope':'includes process startup, tile rendering, inference and evaluation; NOT steady-state latency'})
        atomic_bytes(bundle.path/'report.md',render_report(spec,metrics,response.result,None).encode())
        if digest(load_manifest(dataset_path))!=digest(m):raise CVRSError('DATASET_CHANGED','source dataset changed during tiled run')
        bundle.finish('SUCCEEDED')
    except KeyboardInterrupt:
        bundle.finish('CANCELLED',{'code':'CANCELLED','message':'tiled run interrupted'});raise
    except Exception as exc:
        error=exc.as_dict() if isinstance(exc,CVRSError) else {'code':type(exc).__name__,'message':str(exc)}
        bundle.finish('FAILED',error);raise CVRSError(error['code'],f"{error['message']}; evidence {bundle.path}") from exc
    return bundle.path
