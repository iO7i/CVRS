"""MMDetection heritage inspection/certification without executing configs in core."""
from __future__ import annotations
import ast
from pathlib import Path
from cvsubstrate.contracts.models import HeritageCertification, LegacyExperimentRef
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.bundle import verify_bundle
from cvsubstrate.provenance.io import digest, file_digest, read_json, write_json

LEVELS = [
    'H0_CATALOGUED',
    'H1_CONFIG_RESOLVED',
    'H2_INFERENCE_EXECUTED',
    'H3_OUTPUT_PARITY_VERIFIED',
    'H4_REFERENCE_METRIC_REPRODUCED',
    'H5_TRAINING_REPRODUCED',
]


def inspect_config(path: Path) -> dict:
    if path.stat().st_size > 2 * 1024 * 1024:
        raise CVRSError('CONFIG_TOO_LARGE', 'legacy config exceeds inspection limit')
    tree = ast.parse(path.read_text('utf-8'), filename=path.name)
    values = {}
    unresolved = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [t.id for t in targets if isinstance(t, ast.Name)]
            for name in names:
                try:
                    values[name] = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    unresolved.append(name)
        elif not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Constant):
            unresolved.append(f'{type(node).__name__}@{node.lineno}')
    return {
        'status': 'STATIC_INSPECTION_ONLY',
        'config_sha256': file_digest(path),
        'literal_values': values,
        'unresolved': unresolved,
        'base_references': values.get('_base_', []),
        'executed': False,
        'note': 'Dynamic values and base inheritance are intentionally unresolved. This is not full config resolution.',
    }


def inspect_reference(path: Path) -> dict:
    ref = LegacyExperimentRef.model_validate(read_json(path))
    config = (path.parent / ref.config).resolve() if not Path(ref.config).is_absolute() else Path(ref.config)
    if file_digest(config) != ref.config_sha256:
        raise CVRSError('CONFIG_HASH', 'legacy config digest mismatch')
    report = inspect_config(config)
    report.update({
        'upstream': ref.upstream,
        'revision': ref.revision,
        'framework_version': ref.framework_version,
        'declared_status': ref.status,
        'declared_compatibility_level': ref.compatibility_level,
        'verified_compatibility_level': 'H0_CATALOGUED',
        'licenses': ref.licenses.model_dump(mode='json'),
    })
    report['note'] += ' Declared status/level are not certified by static inspection.'
    return report


def adapter_fragment(path: Path) -> dict:
    """Produce the adapter fragment an existing MMDetection user can place in ExperimentSpec."""
    path = Path(path).resolve()
    ref = LegacyExperimentRef.model_validate(read_json(path))
    config = Path(ref.config)
    config = config if config.is_absolute() else path.parent / config
    if not config.is_file() or file_digest(config) != ref.config_sha256:
        raise CVRSError('CONFIG_HASH', 'legacy config unavailable or digest mismatch')
    fragment = {
        'name': 'mmdetection',
        'config': {
            'config_path': str(config),
            'config_sha256': ref.config_sha256,
            'trust_executable_config': ref.trust_executable_config,
            'category_map': {},
            'upstream': ref.upstream,
            'revision': ref.revision,
            'device': 'cpu',
        },
    }
    return {
        'adapter': fragment,
        'checkpoint': ref.checkpoint.model_dump(mode='json') if ref.checkpoint else None,
        'note': 'Fill category_map explicitly. Paths may be made relative in the final ExperimentSpec; no config translation occurred.',
    }


def _flat_metric_values(metrics: dict) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    if metrics.get('kind') == 'REFERENCE_COCO_BBOX':
        for key, item in metrics.get('metrics', {}).items():
            out[key] = item.get('value') if isinstance(item, dict) else item
        ap50 = metrics.get('AP50')
        out['AP50'] = ap50.get('value') if isinstance(ap50, dict) else ap50
    return out


def certify_run(run: Path, reference: Path | None = None, tolerance: float = 1e-6, output: Path | None = None) -> dict:
    import math
    run = Path(run).resolve()
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('metric tolerance must be finite and positive')
    if output is not None:
        output = Path(output).resolve()
        if output.is_relative_to(run):
            raise CVRSError('SEALED_BUNDLE', 'certification must be a derived artifact outside the sealed run')
        if output.exists():
            raise CVRSError('OUTPUT_EXISTS', 'refusing to overwrite a prior certification')
    reproduction = None
    verified = verify_bundle(run)
    if verified['status'] != 'VERIFIED' or verified.get('run_state') != 'SUCCEEDED':
        raise CVRSError('EVIDENCE_INVALID', 'heritage certification requires a verified successful run')
    experiment = read_json(run / 'experiment.json')
    if experiment.get('adapter', {}).get('name') != 'mmdetection':
        raise CVRSError('ADAPTER_MISMATCH', 'heritage certification requires an MMDetection run')
    result = read_json(run / 'worker_result.json')
    level = 'H0_CATALOGUED'
    evidence: dict[str, str] = {}
    blockers: list[str] = []
    if (run / 'heritage_validation.json').is_file() and (run / 'heritage' / 'resolved_config.py.txt').is_file():
        level = 'H1_CONFIG_RESOLVED'
        evidence['resolved_config'] = file_digest(run / 'heritage' / 'resolved_config.py.txt')
    if result.get('status') in {'INFERENCE_EXECUTED', 'OUTPUT_PARITY_VERIFIED'} and (run / 'predictions.jsonl').is_file():
        level = 'H2_INFERENCE_EXECUTED'
        evidence['predictions'] = file_digest(run / 'predictions.jsonl')
    audit_path = run / 'heritage' / 'conversion_audit.json'
    if audit_path.is_file():
        audit = read_json(audit_path)
        if audit.get('exact_representation_fidelity') is True:
            level = 'H3_OUTPUT_PARITY_VERIFIED'
            evidence['conversion_audit'] = file_digest(audit_path)
    if reference is not None:
        ref = LegacyExperimentRef.model_validate(read_json(reference))
        run_manifest = read_json(run / 'run.json')
        metrics_payload = read_json(run / 'metrics.json')
        actual = _flat_metric_values(metrics_payload)
        deltas = {}
        checks = {
            'dataset_identity': bool(ref.dataset_sha256) and ref.dataset_sha256 == run_manifest.get('dataset_digest'),
            'evaluation_protocol': bool(ref.reference_protocol) and ref.reference_protocol == experiment.get('evaluation'),
            'checkpoint_identity': bool(ref.checkpoint) and experiment.get('checkpoint', {}).get('sha256') == ref.checkpoint.sha256,
            'config_identity': experiment.get('adapter', {}).get('config', {}).get('config_sha256') == ref.config_sha256,
        }
        source = result.get('actual_source_identity') or {}
        checks['revision_identity'] = bool(source.get('git_sha')) and source.get('git_sha') == ref.revision
        if not ref.reported_metrics:
            checks['reported_metrics'] = False
            blockers.append('reference has no reported_metrics')
        else:
            metric_ok = True
            for key, expected in ref.reported_metrics.items():
                observed = actual.get(key)
                if observed is None:
                    metric_ok = False
                    deltas[key] = None
                else:
                    deltas[key] = abs(float(observed) - float(expected))
                    metric_ok = metric_ok and deltas[key] <= tolerance
            checks['reported_metrics'] = metric_ok
            if not metric_ok:
                blockers.append('reported reference metrics were not reproduced within tolerance')
        for key, ok in checks.items():
            if not ok and key != 'reported_metrics':
                blockers.append(f'H4 identity check failed or was undeclared: {key}')
        reproduction = {
            'tolerance': tolerance,
            'reported': ref.reported_metrics,
            'observed': actual,
            'absolute_deltas': deltas,
            'identity_checks': checks,
            'pass': all(checks.values()) and level == 'H3_OUTPUT_PARITY_VERIFIED',
            'note': 'H4 requires exact dataset, evaluator protocol, checkpoint, config, verified source revision, and reported metric agreement.',
        }
        if reproduction['pass']:
            level = 'H4_REFERENCE_METRIC_REPRODUCED'
            evidence['metric_reproduction'] = digest(reproduction)
    if level != 'H4_REFERENCE_METRIC_REPRODUCED':
        blockers.append('H4 requires exact reference data/protocol plus reported metric agreement')
    cert = HeritageCertification(
        reference_digest=digest(read_json(reference)) if reference is not None else digest({'run': str(run), 'experiment': experiment}),
        compatibility_level=level,
        evidence=evidence,
        blockers=sorted(set(blockers)),
        independently_reproduced=False,
    ).model_dump(mode='json')
    if reproduction is not None:
        cert['metric_reproduction'] = reproduction
    cert['source_run_artifact_manifest_sha256'] = file_digest(run / 'artifacts.json')
    if output is not None:
        write_json(output, cert)
    return cert
