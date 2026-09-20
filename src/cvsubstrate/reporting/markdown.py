"""Plain Markdown reports suitable for source control and offline reading."""
import json
from cvsubstrate.provenance.io import atomic_bytes

def render_report(experiment, metrics, worker_result, plan=None) -> str:
    lines = [f'# {experiment.name}', '', '**Scope:** executable research foundation; not a detector-performance claim.', '', f'- Backend: `{experiment.adapter.name}`', f'- Dataset digest: `{experiment.dataset_sha256}`', f"- Evaluator: `{metrics['evaluator']}` / `{metrics['evaluator_version']}`", f'- Evaluation split: `{experiment.eval_split}`', f'- Seed: `{experiment.seed}`', '', '## Measurement', '']
    if metrics['kind'] == 'DIAGNOSTIC_NOT_COCO':
        lines += ['**These are diagnostic precision/recall counts, not COCO AP.**', '', '```json', json.dumps(metrics['aggregate'], indent=2), '```', '']
    else:
        lines += ['```json', json.dumps(metrics['metrics'], indent=2), '```', '']
    if metrics.get('scientific_claim'):
        lines += [metrics['scientific_claim'], '']
    lines += ['## Model execution', '', '```json', json.dumps(worker_result, indent=2), '```', '']
    if plan:
        lines += ['## Planned source exposure', '', '```json', json.dumps(plan['planned_counts'], indent=2), '```', '', 'See training_trace.jsonl / worker/training_trace.jsonl for measured per-update evidence.', '']
    lines += ['## Verification limits', '', 'The bundle has unsigned content hashes. Integrity is not authenticity, independent reproduction, or a scientific result.', 'A toy CPU run with random initialization does not reproduce a pretrained model-zoo score.', 'Locked-test checks are local policy, not a security sandbox.', '']
    return '\n'.join(lines)
