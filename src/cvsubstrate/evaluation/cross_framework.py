"""Evidence-scoped cross-framework comparison for completed run bundles."""
from __future__ import annotations
from pathlib import Path
from cvsubstrate.errors import CVRSError
from cvsubstrate.evaluation.compare import compare
from cvsubstrate.provenance.bundle import verify_bundle
from cvsubstrate.provenance.io import digest, read_json


def _load_run(path: Path) -> dict:
    path = Path(path)
    verified = verify_bundle(path)
    if verified['status'] != 'VERIFIED' or verified.get('run_state') != 'SUCCEEDED':
        raise CVRSError('EVIDENCE_INVALID', f'run is not a verified successful bundle: {path}')
    return {
        'experiment': read_json(path / 'experiment.json'),
        'metrics': read_json(path / 'metrics.json'),
        'adapter': read_json(path / 'adapter.json'),
        'worker_result': read_json(path / 'worker_result.json'),
        'environment': read_json(path / 'environment.json'),
    }


def compare_runs(left_path: Path, right_path: Path) -> dict:
    left = _load_run(left_path)
    right = _load_run(right_path)
    measurement = compare(left['metrics'], right['metrics'])
    left_adapter = left['experiment']['adapter']['name']
    right_adapter = right['experiment']['adapter']['name']
    left_worker_env = left['adapter'].get('environment', {})
    right_worker_env = right['adapter'].get('environment', {})
    left_env_digest = digest(left_worker_env)
    right_env_digest = digest(right_worker_env)
    distinct_implementations = left_adapter != right_adapter
    distinct_recorded_worker_environments = left_env_digest != right_env_digest
    left_training = left['experiment'].get('training')
    right_training = right['experiment'].get('training')
    if left_training is None and right_training is None:
        training_fairness = 'NOT_ASSESSED_PRETRAINED_OR_INFERENCE_ONLY'
    elif left_training == right_training:
        training_fairness = 'SAME_DECLARED_TRAINING_SPEC_ONLY'
    else:
        training_fairness = 'NOT_MATCHED'
    return {
        'measurement': measurement,
        'left': {'adapter': left_adapter, 'worker_environment_digest': left_env_digest, 'checkpoint': left['experiment'].get('checkpoint')},
        'right': {'adapter': right_adapter, 'worker_environment_digest': right_env_digest, 'checkpoint': right['experiment'].get('checkpoint')},
        'distinct_implementations': distinct_implementations,
        'distinct_recorded_worker_environments': distinct_recorded_worker_environments,
        'training_fairness': training_fairness,
        'claim_scope': 'Measurement comparability is separate from matched training/pretraining/compute and does not establish model superiority.',
    }
