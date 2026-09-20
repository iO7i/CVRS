"""Bounded subprocess transport. Isolation from dependencies, NOT malicious code."""
from __future__ import annotations
from collections import deque
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
from cvsubstrate.contracts.models import WorkerRequest, WorkerResponse
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.bundle import redact
from cvsubstrate.provenance.io import atomic_bytes, read_json, write_json
MAX_CAPTURE = 256 * 1024

def run_command(argv: list[str], timeout: float, log: Path | None=None, cwd: Path | None=None, env: dict[str,str] | None=None, cancel_token=None, pass_env=(), process_observer=None) -> dict:
    if cancel_token is None:
        from cvsubstrate.foundation.lifecycle import CURRENT_CANCELLATION
        cancel_token=CURRENT_CANCELLATION.get()
    if timeout <= 0:
        raise ValueError('timeout must be positive')
    # No shell, no inherited credential variables. Subprocess is still TRUSTED code.
    allowed = {'PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'TMPDIR', 'LANG', 'LC_ALL', 'PYTHONPATH', 'LD_LIBRARY_PATH', 'CUDA_VISIBLE_DEVICES', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'VIRTUAL_ENV'}
    allowed |= {'WANDB_MODE','WANDB_DISABLED','HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','YOLO_AUTOINSTALL','RANK','LOCAL_RANK','WORLD_SIZE','LOCAL_WORLD_SIZE','MASTER_ADDR','MASTER_PORT'}
    if any(not isinstance(k,str) or not k.replace('_','').isalnum() for k in pass_env):
        raise ValueError('invalid explicit environment variable name')
    allowed.update(pass_env)
    env = {k: v for k, v in {**os.environ,**(env or {})}.items() if k in allowed}
    env.update({'PYTHONUNBUFFERED': '1', 'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'})
    try:
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd, env=env, start_new_session=os.name == 'posix')
    except OSError as exc:
        raise CVRSError('WORKER_LAUNCH', f'cannot start configured worker: {exc.strerror}') from exc
    if process_observer is not None:process_observer(proc.pid, 'started')
    chunks = deque()
    state = {'size': 0, 'truncated': False}

    def collect():
        while True:
            data = proc.stdout.read(4096)
            if not data:
                break
            chunks.append(data)
            state['size'] += len(data)
            while state['size'] > MAX_CAPTURE:
                state['size'] -= len(chunks.popleft())
                state['truncated'] = True
    reader = threading.Thread(target=collect, daemon=True)
    reader.start()

    def stop():
        try:
            if os.name == 'posix':
                os.killpg(proc.pid, signal.SIGKILL)
            else:
                proc.kill()
        except ProcessLookupError:
            pass
        proc.wait(timeout=5)
    error = None
    try:
        import time
        deadline=time.monotonic()+timeout
        while proc.poll() is None:
            if process_observer is not None:process_observer(proc.pid, 'sample')
            if cancel_token is not None and cancel_token.cancelled:
                from cvsubstrate.foundation.lifecycle import Cancelled
                stop();raise Cancelled()
            if time.monotonic()>=deadline:raise subprocess.TimeoutExpired(argv,timeout)
            time.sleep(.025)
    except subprocess.TimeoutExpired:
        stop()
        error = CVRSError('WORKER_TIMEOUT', 'worker exceeded configured deadline and was terminated')
    except CVRSError as exc:
        stop();error=exc
    except KeyboardInterrupt:
        stop()
        error = KeyboardInterrupt()
    if process_observer is not None:process_observer(proc.pid, 'exited')
    reader.join(timeout=5)
    # A child that intentionally holds stdout open is not trusted by this launcher.
    if reader.is_alive():
        if os.name == 'posix':
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        reader.join(timeout=1)
    text = redact(b''.join(chunks).decode('utf-8', 'replace'))
    if state['truncated']:
        text = '[earlier worker output truncated]\n' + text
    if log:
        atomic_bytes(log, text.encode('utf-8'))
    if error:
        raise error
    if proc.returncode != 0:
        raise CVRSError('WORKER_EXIT', f'worker exited with status {proc.returncode}; inspect bounded log')
    return {'exit_code': proc.returncode, 'captured_bytes': len(text.encode()), 'truncated': state['truncated']}

def worker_command(adapter: str, worker_python: str | None=None) -> list[str]:
    """Return a dependency-isolated worker command.

    The heritage bridge is executed by file path and contains no cvsubstrate or
    Pydantic imports, so the target MMDetection interpreter does not need the
    modern controller package installed.
    """
    python = worker_python or sys.executable
    if adapter == 'native_torch':
        return [python, '-m', 'cvsubstrate.workers.native_torch']
    if adapter in {'ultralytics','rfdetr'}:
        return [python, str(Path(__file__).resolve().parents[1] / 'worker_shims' / (adapter + '_worker.py'))]
    if adapter == 'mmdetection':
        shim = Path(__file__).resolve().parents[1] / 'worker_shims' / 'mmdetection_worker.py'
        if not shim.is_file():
            raise CVRSError('WORKER_MISSING', 'packaged standalone MMDetection bridge is missing')
        return [python, str(shim)]
    raise CVRSError('ADAPTER_UNKNOWN', 'unknown built-in worker')


def invoke(adapter: str, request: WorkerRequest, worker_python: str | None=None, timeout: float=180.0, log: Path | None=None, cancel_token=None) -> WorkerResponse:
    with tempfile.TemporaryDirectory(prefix='cvrs-request-') as td:
        req = Path(td) / 'request.json'
        res = Path(td) / 'response.json'
        write_json(req, request)
        command = worker_command(adapter, worker_python) + ['--request', str(req), '--response', str(res)]
        run_command(command, timeout, log=log, cancel_token=cancel_token)
        if not res.is_file():
            raise CVRSError('MISSING_RESPONSE', 'worker exited without a response')
        try:
            response = WorkerResponse.model_validate(read_json(res))
        except (ValueError, OSError) as exc:
            raise CVRSError('INVALID_RESPONSE', 'invalid or incompatible worker response') from exc
        if response.status != 'SUCCEEDED':
            err = response.error or {'code': 'WORKER_FAILED', 'message': 'worker returned structured failure'}
            raise CVRSError(err['code'], err['message'])
        return response
