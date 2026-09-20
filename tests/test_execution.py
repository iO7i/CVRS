import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from cvsubstrate.contracts.models import WorkerRequest, WorkerResponse, ExperimentSpec
from cvsubstrate.errors import CVRSError
from cvsubstrate.execution.process import run_command, invoke, MAX_CAPTURE
from cvsubstrate.execution.heritage import inspect_config
from cvsubstrate.execution.runner import run_experiment
from cvsubstrate.provenance.bundle import RunBundle, verify_bundle, redact
from cvsubstrate.provenance.io import digest, write_json, read_json, experiment_identity

def test_child_exit_code_propagates(tmp_path):
    with pytest.raises(CVRSError, match='status 7'):
        run_command([sys.executable, '-c', 'raise SystemExit(7)'], 5, tmp_path / 'log')

def test_timeout_kills_worker(tmp_path):
    with pytest.raises(CVRSError, match='deadline'):
        run_command([sys.executable, '-c', 'import time;time.sleep(30)'], 0.1, tmp_path / 'log')

def test_large_stdout_is_bounded(tmp_path):
    p = tmp_path / 'log'
    r = run_command([sys.executable, '-c', "print('x'*1000000)"], 10, p)
    assert r['truncated'] is True and p.stat().st_size <= MAX_CAPTURE + 100

def test_logs_redact_secrets(tmp_path):
    p = tmp_path / 'log'
    run_command([sys.executable, '-c', "print('token=SUPERSECRET password: PRIVATE')"], 5, p)
    assert 'SUPERSECRET' not in p.read_text() and 'PRIVATE' not in p.read_text()

def test_credentials_not_inherited(tmp_path, monkeypatch):
    monkeypatch.setenv('VERY_SECRET_API_TOKEN', 'should-not-pass')
    p = tmp_path / 'log'
    run_command([sys.executable, '-c', "import os;print(os.environ.get('VERY_SECRET_API_TOKEN','ABSENT'))"], 5, p)
    assert p.read_text().strip() == 'ABSENT'

def test_no_shell_interpolation(tmp_path):
    marker = tmp_path / 'oops'
    p = tmp_path / 'log'
    run_command([sys.executable, '-c', 'import sys;print(sys.argv[1])', f';touch {marker}'], 5, p)
    assert not marker.exists()

def test_invalid_interpreter_structured_error():
    with pytest.raises(CVRSError, match='cannot start'):
        run_command(['/definitely/not/a/python'], 1)

def test_config_inspection_never_executes(tmp_path):
    marker = tmp_path / 'EXECUTED'
    p = tmp_path / 'config.py'
    p.write_text(f"_base_ = ['base.py']\nvalue=3\nopen({str(marker)!r},'w').write('bad')\nmodel=dict(type='TOOD')\n")
    r = inspect_config(p)
    assert r['executed'] is False and (not marker.exists())
    assert r['literal_values']['value'] == 3 and 'model' in r['unresolved']
    assert r['base_references'] == ['base.py']

def test_heritage_not_installed_is_honest():
    import importlib.util
    if importlib.util.find_spec('mmdet'):
        pytest.skip('actual heritage env available')
    r = invoke('mmdetection', WorkerRequest(operation='capabilities'), timeout=15)
    assert r.result['installed'] is False and r.result['execution_verified_in_this_process'] is False
    with pytest.raises(CVRSError, match='no substitute'):
        invoke('mmdetection', WorkerRequest(operation='predict'), timeout=15)

def test_heritage_training_explicitly_unsupported():
    with pytest.raises(CVRSError, match='not implemented'):
        invoke('mmdetection', WorkerRequest(operation='train'), timeout=15)

def test_sealed_bundle_detects_tamper(tmp_path):
    b = RunBundle(tmp_path, 'a' * 64, 'b' * 64)
    write_json(b.path / 'payload.json', {'x': 1})
    b.finish('SUCCEEDED')
    assert verify_bundle(b.path)['status'] == 'VERIFIED'
    write_json(b.path / 'payload.json', {'x': 2})
    assert verify_bundle(b.path)['status'] == 'FAILED'

def test_missing_artifact_detected(tmp_path):
    b = RunBundle(tmp_path, 'a' * 64, 'b' * 64)
    write_json(b.path / 'payload.json', {'x': 1})
    b.finish('SUCCEEDED')
    (b.path / 'payload.json').unlink()
    assert verify_bundle(b.path)['status'] == 'FAILED'

def test_extra_artifact_detected(tmp_path):
    b = RunBundle(tmp_path, 'a' * 64, 'b' * 64)
    b.finish('FAILED', {'code': 'X', 'message': 'fixture failure'})
    assert verify_bundle(b.path)['run_state'] == 'FAILED'
    (b.path / 'injected').write_text('bad')
    assert verify_bundle(b.path)['status'] == 'FAILED'

def test_unfinished_run_incomplete(tmp_path):
    b = RunBundle(tmp_path, 'a' * 64, 'b' * 64)
    assert verify_bundle(b.path)['status'] == 'INCOMPLETE'

def test_cannot_modify_sealed_bundle(tmp_path):
    b = RunBundle(tmp_path, 'a' * 64, 'b' * 64)
    b.finish('SUCCEEDED')
    with pytest.raises(CVRSError):
        b.event('changed')
    with pytest.raises(CVRSError):
        b.finish('FAILED')

def test_failure_run_not_success(dataset, real_spec, tmp_path):
    m, root = dataset
    real_spec.adapter.name = 'mmdetection'
    write_json(root / 'bad.json', real_spec)
    with pytest.raises(CVRSError):
        run_experiment(root / 'bad.json', tmp_path / 'runs', timeout=15)
    runs = list((tmp_path / 'runs').iterdir())
    assert len(runs) == 1
    v = verify_bundle(runs[0])
    assert v['status'] == 'VERIFIED' and v['run_state'] == 'FAILED'

@pytest.mark.native
def test_native_missing_operation_inputs_structured():
    pytest.importorskip('torch')
    with pytest.raises(CVRSError, match='required'):
        invoke('native_torch', WorkerRequest(operation='train'), timeout=15)

def test_core_import_does_not_import_ml():
    # The hosted interpreter may preload NumPy via sitecustomize. Verify the core
    # does not add heavyweight ML modules rather than assuming a pristine process.
    code = (
        "import sys;before=set(sys.modules);"
        "import cvsubstrate.cli,cvsubstrate.contracts.models,cvsubstrate.data.fixtures;"
        "after=set(sys.modules);added=after-before;"
        "assert 'torch' not in added;assert 'PIL' not in added;assert 'mmcv' not in added;assert 'mmdet' not in added"
    )
    subprocess.run([sys.executable, '-c', code], check=True, timeout=15)
