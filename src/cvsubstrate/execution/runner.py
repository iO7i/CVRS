"""Controller: validate → worker → validate outputs → evaluate → seal evidence."""
from __future__ import annotations
from pathlib import Path
import shutil
from cvsubstrate.contracts.models import DetectionPrediction, ExperimentSpec, WorkerRequest
from cvsubstrate.data.manifest import load_manifest, validate_experiment
from cvsubstrate.errors import CVRSError
from cvsubstrate.evaluation.metrics import evaluate, validate_predictions
from cvsubstrate.execution.plugins import invoke_configured
from cvsubstrate.protocols.planner import plan
from cvsubstrate.provenance.bundle import RunBundle, environment_snapshot, source_snapshot
from cvsubstrate.provenance.io import atomic_bytes, digest, experiment_identity, file_digest, read_json, read_jsonl, write_json, safe_join
from cvsubstrate.reporting.markdown import render_report

def load_experiment(path: Path, authorization: dict | None=None):
    path = Path(path).resolve()
    spec = ExperimentSpec.model_validate(read_json(path))
    dataset = Path(spec.dataset)
    dataset = dataset if dataset.is_absolute() else path.parent / dataset
    m = load_manifest(dataset)
    validate_experiment(spec, m, authorization)
    return (spec, m, dataset.resolve())


def _worker_experiment(spec: ExperimentSpec, spec_path: Path) -> dict:
    """Materialize execution-only absolute paths without changing experiment identity."""
    value = spec.model_dump(mode='json')
    if spec.adapter.name == 'mmdetection':
        config = dict(value['adapter']['config'])
        raw = config.get('config_path')
        if raw:
            p = Path(raw)
            p = p if p.is_absolute() else spec_path.resolve().parent / p
            if not p.is_file():
                raise CVRSError('CONFIG_MISSING', 'heritage config unavailable')
            if file_digest(p) != config.get('config_sha256'):
                raise CVRSError('CONFIG_HASH', 'heritage config digest mismatch')
            config['config_path'] = str(p.resolve())
        value['adapter']['config'] = config
    return value


def _copy_worker_evidence(bundle: RunBundle, worker_result: dict) -> None:
    """Copy declared worker evidence into a sealed, discoverable heritage directory."""
    artifacts = worker_result.get('evidence_artifacts', [])
    if not artifacts:
        return
    if not isinstance(artifacts, list) or any(not isinstance(x, str) for x in artifacts):
        raise CVRSError('EVIDENCE_ARTIFACTS', 'worker evidence artifact list is invalid')
    worker_root = bundle.path / 'worker'
    target_root = bundle.path / 'heritage'
    seen = set()
    for rel in artifacts:
        if rel in seen:
            raise CVRSError('EVIDENCE_ARTIFACTS', 'duplicate worker evidence artifact')
        seen.add(rel)
        src = safe_join(worker_root, rel)
        if not src.is_file():
            raise CVRSError('EVIDENCE_ARTIFACTS', f'declared worker evidence missing: {rel}')
        if rel == 'predictions.jsonl':
            continue
        dst = safe_join(target_root, rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)

def run_experiment(path: Path, output_root: Path, worker_python: str | None=None, timeout: float=180.0, authorization: dict | None=None, *, access_ledger=None, approval_digest: str | None=None, evaluator_python: str | None=None) -> Path:
    # The low-level validator still accepts a bound authorization for a legacy
    # worker. Controller execution additionally requires a counted ledger access.
    raw = ExperimentSpec.model_validate(read_json(path))
    dp = Path(raw.dataset)
    dp = dp if dp.is_absolute() else Path(path).resolve().parent / dp
    meta = load_manifest(dp)
    access_record = None
    if raw.eval_split in meta.splits and meta.splits[raw.eval_split].role == 'locked_test':
        if raw.training is not None:
            raise CVRSError('TEST_TRAINING', 'locked-test execution cannot include training')
        if access_ledger is None or not approval_digest:
            raise CVRSError('TEST_LEDGER_REQUIRED', 'use ledger final-run with a recorded, identity-bound approval')
        from cvsubstrate.governance.policy import consume_final_test
        from cvsubstrate.contracts.models import FinalTestAuthorization
        approved, access_record = consume_final_test(access_ledger, approval_digest,
            dataset_digest=digest(meta), experiment_digest=experiment_identity(raw), split=raw.eval_split)
        authorization = FinalTestAuthorization(experiment_digest=experiment_identity(raw),
            dataset_digest=digest(meta), split=raw.eval_split, approved_by=approved['approved_by'],
            approved_at=access_record['at'], acknowledge_policy_not_sandbox=True).model_dump(mode='json')
    elif access_ledger is not None or approval_digest:
        raise CVRSError('TEST_ROLE', 'final-test approvals are only for locked-test evaluation')
    spec, m, dataset_path = load_experiment(path, authorization)
    if spec.evaluation.evaluator == 'pycocotools' and evaluator_python is None:
        try:
            import importlib.metadata
            version = importlib.metadata.version('pycocotools')
        except importlib.metadata.PackageNotFoundError as exc:
            raise CVRSError('COCO_DEPENDENCY', 'install pycocotools==2.0.11 in the controller evaluator environment; no fallback used') from exc
        if version != spec.evaluation.evaluator_version:
            raise CVRSError('EVALUATOR_VERSION', 'wrong pycocotools version')
    ck = None
    if spec.checkpoint:
        p = Path(spec.checkpoint.path)
        p = p if p.is_absolute() else Path(path).resolve().parent / p
        if not p.is_file():
            raise CVRSError('MISSING_CHECKPOINT', 'checkpoint unavailable')
        if file_digest(p) != spec.checkpoint.sha256:
            raise CVRSError('CHECKPOINT_HASH', 'checkpoint mismatch')
        ck = {**spec.checkpoint.model_dump(mode='json'), 'path': str(p.resolve())}
    bundle = RunBundle(Path(output_root).resolve(), experiment_identity(spec), digest(m))
    from cvsubstrate.events import append_event
    def event(kind,payload=None):
        return append_event(bundle.path/'lifecycle.jsonl',run_id=bundle.path.name,component='controller',event_type=kind,payload=payload)
    event('RUN_CREATED')
    try:
        # Paths retained relative to caller spec in the record; scientific identity
        # uses explicit hashes. No dataset or existing external checkpoints copied.
        write_json(bundle.path / 'experiment.json', spec)
        write_json(bundle.path / 'dataset_manifest.json', m)
        write_json(bundle.path / 'environment.json', environment_snapshot())
        write_json(bundle.path / 'source.json', source_snapshot())
        if m.splits[spec.eval_split].role == 'selection':
            write_json(bundle.path / 'selection_access.json', {'split':spec.eval_split,'experiment_digest':experiment_identity(spec),
                'purpose':'explicit model/arm selection evaluation','limits':'Recorded local access, not a locked-test secrecy guarantee'})
        if access_record:
            write_json(bundle.path / 'final_test_access_receipt.json', access_record)
        if authorization:
            write_json(bundle.path / 'final_test_authorization.json', authorization)
        protocol_plan = plan(spec, m) if spec.training else None
        if protocol_plan:
            write_json(bundle.path / 'protocol_plan.json', protocol_plan)
        cap = invoke_configured(spec.adapter, WorkerRequest(operation='capabilities'), worker_python, timeout=min(timeout, 45), log=bundle.path / 'capabilities.log')
        write_json(bundle.path / 'adapter.json', cap.result)
        if not cap.result.get('installed', False):
            raise CVRSError('ADAPTER_NOT_INSTALLED', 'worker environment lacks the requested backend')
        operation = 'train' if spec.training else 'predict'
        if operation not in cap.result.get('operations', []):
            raise CVRSError('OPERATION_UNSUPPORTED', 'worker does not implement requested operation')
        worker_spec = _worker_experiment(spec, Path(path))
        common = dict(experiment=worker_spec, manifest=m.model_dump(mode='json'), data_root=str(dataset_path.parent), output_dir=str(bundle.path / 'worker'), checkpoint=ck, final_test_authorization=authorization)
        if spec.adapter.name == 'mmdetection':
            validation = invoke_configured(spec.adapter, WorkerRequest(operation='validate', **common), worker_python, min(timeout, 90), log=bundle.path / 'heritage-validate.log')
            write_json(bundle.path / 'heritage_validation.json', validation.result)
        event('WORKER_STARTED',{'operation':operation,'adapter':spec.adapter.name})
        response = invoke_configured(spec.adapter, WorkerRequest(operation=operation, **common), worker_python, timeout, log=bundle.path / 'worker.log')
        event('TRAIN_COMPLETED' if operation=='train' else 'INFERENCE_COMPLETED',{'observed':'worker returned a successful response; outputs still require validation'})
        write_json(bundle.path / 'worker_result.json', response.result)
        _copy_worker_evidence(bundle, response.result)
        predictions_path = bundle.path / 'worker' / 'predictions.jsonl'
        if not predictions_path.is_file():
            raise CVRSError('PREDICTIONS_MISSING', 'successful worker omitted prediction artifact')
        rows = [DetectionPrediction.model_validate(r) for r in read_jsonl(predictions_path)]
        validate_predictions(m, spec.eval_split, rows)
        shutil.copyfile(predictions_path, bundle.path / 'predictions.jsonl')
        if (bundle.path / 'worker' / 'training_trace.jsonl').exists():
            shutil.copyfile(bundle.path / 'worker' / 'training_trace.jsonl', bundle.path / 'training_trace.jsonl')
        if evaluator_python:
            from cvsubstrate.evaluation.service import evaluate_isolated
            metrics = evaluate_isolated(m, spec.eval_split, rows, spec.evaluation, worker_python=evaluator_python, timeout=timeout, log=bundle.path / 'evaluator.log')
        else:
            metrics = evaluate(m, spec.eval_split, rows, spec.evaluation)
        event('EVALUATION_COMPLETED',{'evaluator':spec.evaluation.evaluator})
        write_json(bundle.path / 'metrics.json', metrics)
        atomic_bytes(bundle.path / 'report.md', render_report(spec, metrics, response.result, protocol_plan).encode())
        # Validate external file identities again; detects normal mutation during
        # execution, not a hostile race with perfectly timed byte restoration.
        final_manifest = load_manifest(dataset_path)
        if digest(final_manifest) != digest(m):
            raise CVRSError('DATASET_CHANGED_DURING_RUN', 'dataset manifest changed during execution')
        event('RUN_SUCCEEDED')
        bundle.finish('SUCCEEDED')
    except KeyboardInterrupt:
        event('RUN_CANCELLED')
        bundle.finish('CANCELLED', {'code': 'CANCELLED', 'message': 'user interrupted execution'})
        raise CVRSError('CANCELLED', f'cancelled run preserved at {bundle.path}')
    except Exception as exc:
        error = exc.as_dict() if isinstance(exc, CVRSError) else {'code': type(exc).__name__, 'message': str(exc)}
        event('RUN_FAILED',error)
        bundle.finish('FAILED', error)
        raise CVRSError(error['code'], f"{error['message']}; failure evidence: {bundle.path}") from exc
    return bundle.path
