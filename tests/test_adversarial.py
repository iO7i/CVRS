"""A second verification pass aimed at overclaiming, malformed evidence, and silent repair."""
from copy import deepcopy
from pathlib import Path
import sys
import pytest
from cvsubstrate.contracts.models import WorkerRequest, WorkerResponse, DatasetManifest, DetectionPrediction, EvaluationProtocol
from cvsubstrate.errors import CVRSError
from cvsubstrate.execution import process
from cvsubstrate.execution.runner import run_experiment
from cvsubstrate.evaluation.compare import compare
from cvsubstrate.provenance.io import write_json, read_json, read_jsonl, digest, safe_join
from cvsubstrate.provenance.bundle import RunBundle, verify_bundle

@pytest.mark.parametrize('payload', [{'protocol_version': '9.0', 'status': 'SUCCEEDED', 'result': {}}, {'protocol_version': '1.0', 'status': 'probably fine', 'result': {}}, {'protocol_version': '1.0', 'status': 'SUCCEEDED', 'result': {}, 'fake_verified': True}, {'protocol_version': '1.0', 'status': 'SUCCEEDED', 'result': {'score': float('nan')}}])
def test_successful_process_cannot_bypass_response_validation(monkeypatch, payload):

    def fake(argv, *args, **kwargs):
        dest = Path(argv[argv.index('--response') + 1])
        import json
        dest.write_text(json.dumps(payload))
        return {'exit_code': 0}
    monkeypatch.setattr(process, 'run_command', fake)
    with pytest.raises(CVRSError, match='invalid or incompatible'):
        process.invoke('native_torch', WorkerRequest(operation='capabilities'))

def test_worker_missing_response_not_success(monkeypatch):
    monkeypatch.setattr(process, 'run_command', lambda *args, **kwargs: {'exit_code': 0})
    with pytest.raises(CVRSError, match='without a response'):
        process.invoke('native_torch', WorkerRequest(operation='capabilities'))

def test_worker_declares_success_but_omits_predictions(dataset, tmp_path, monkeypatch):
    from cvsubstrate.execution import runner

    def fake(adapter, request, *args, **kwargs):
        if request.operation == 'capabilities':
            return WorkerResponse(status='SUCCEEDED', result={'installed': True, 'operations': ['train', 'predict']})
        return WorkerResponse(status='SUCCEEDED', result={'pretend_success': True})
    monkeypatch.setattr(runner, 'invoke_configured', fake)
    m, root = dataset
    with pytest.raises(CVRSError, match='omitted prediction'):
        run_experiment(root / 'real.json', tmp_path / 'runs')
    out = next((tmp_path / 'runs').iterdir())
    assert verify_bundle(out)['run_state'] == 'FAILED'

def test_empty_comparison_key_cannot_claim_comparability():
    forged = {'comparison_key': {}, 'comparison_digest': digest({})}
    assert compare(forged, forged)['status'] == 'DESCRIPTIVE_ONLY'

def test_jsonl_duplicate_keys_rejected(tmp_path):
    p = tmp_path / 'rows.jsonl'
    p.write_text('{"score":0.1,"score":0.9}\n')
    with pytest.raises(ValueError, match='duplicate'):
        read_jsonl(p)

def test_jsonl_nonobject_rejected(tmp_path):
    p = tmp_path / 'rows.jsonl'
    p.write_text('[1,2,3]\n')
    with pytest.raises(ValueError, match='objects'):
        read_jsonl(p)

def test_symlink_outside_declared_data_root_rejected(tmp_path):
    root = tmp_path / 'root'
    root.mkdir()
    outside = tmp_path / 'private'
    outside.write_text('private')
    try:
        (root / 'alias').symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip('symlink privileges unavailable')
    with pytest.raises(CVRSError, match='escapes'):
        safe_join(root, 'alias')

def test_artifact_manifest_path_traversal_rejected(tmp_path):
    b = RunBundle(tmp_path, 'a' * 64, 'b' * 64)
    b.finish('SUCCEEDED')
    a = read_json(b.path / 'artifacts.json')
    a['files'].append({'path': '../outside', 'sha256': '0' * 64, 'bytes': 0})
    a['root_digest'] = digest(a['files'])
    write_json(b.path / 'artifacts.json', a)
    assert verify_bundle(b.path)['status'] == 'FAILED'

def test_changed_external_manifest_rejected(dataset, tmp_path):
    m, root = dataset
    b = RunBundle(tmp_path / 'runs', 'a' * 64, digest(m))
    write_json(b.path / 'dataset_manifest.json', m)
    b.finish('SUCCEEDED')
    assert verify_bundle(b.path, root / 'dataset.json')['status'] == 'VERIFIED'
    m.notes = 'different annotation-dataset revision'
    write_json(root / 'dataset.json', m)
    assert verify_bundle(b.path, root / 'dataset.json')['status'] == 'FAILED'

def test_sidecar_distinguishes_unknown_and_zero():
    from cvsubstrate.contracts.models import GenerationMetadata
    a = GenerationMetadata()
    b = GenerationMetadata(occlusion_fraction=0.0)
    assert digest(a) != digest(b)

def test_unknown_run_directory_is_not_a_pass(tmp_path):
    assert verify_bundle(tmp_path / 'missing')['status'] == 'INCOMPLETE'


@pytest.mark.parametrize('value', [[], 'not-a-manifest', {'files': 'wrong-type'}, {'algorithm': 'md5'}])
def test_malformed_artifact_manifest_is_structured_failure(tmp_path, value):
    write_json(tmp_path / 'artifacts.json', value)
    assert verify_bundle(tmp_path)['status'] == 'FAILED'
