"""Bounded local command execution with no shell and no secret-bearing logs."""
from __future__ import annotations
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Mapping
from cvsubstrate.errors import CVRSError
from cvsubstrate.security import sanitize
from cvsubstrate.provenance.io import write_json


def clean_environment(overrides: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    for key in list(env):
        if key.startswith(("PIP_", "UV_", "PYTHON", "CONDA_", "VIRTUAL_ENV")):
            env.pop(key, None)
    env.update({"PYTHONNOUSERSITE": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                "PIP_NO_INPUT": "1", "UV_NO_PROGRESS": "1"})
    if overrides:
        env.update(overrides)
    return env


def _kill_process_group(pid: int) -> None:
    killpg = getattr(os, "killpg", None)
    sigkill = getattr(signal, "SIGKILL", None)
    if killpg is None or sigkill is None:
        raise RuntimeError("process-group termination is unavailable on this platform")
    killpg(pid, sigkill)


def execute(argv: list[str], *, cwd: Path | None = None, timeout: float = 600,
            log: Path | None = None, env: dict[str, str] | None = None,
            max_output_bytes: int = 8 * 1024 * 1024) -> dict:
    """Kill the owned process group on timeout; cap captured diagnostic output.

    This is an execution boundary, not a sandbox. Callers must authorize native
    code. Temporary spools are bounded while the subprocess is running.
    """
    if not argv or any(not isinstance(a, str) or "\x00" in a for a in argv):
        raise ValueError("invalid argv")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="cvrs-command-") as td:
        output = Path(td) / "output"
        with output.open("wb") as stream:
            proc = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
                                    stdout=stream, stderr=subprocess.STDOUT,
                                    env=env or clean_environment(),
                                    start_new_session=(os.name != "nt"),
                                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
            stopped = None
            try:
                while proc.poll() is None:
                    if time.monotonic() - started > timeout:
                        stopped = "TIMEOUT"
                    elif output.stat().st_size > max_output_bytes:
                        stopped = "OUTPUT_LIMIT"
                    if stopped:
                        if os.name == "nt":
                            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                        else:
                            _kill_process_group(proc.pid)
                        break
                    time.sleep(0.03)
                proc.wait(timeout=10)
            except BaseException:
                if proc.poll() is None:
                    if os.name != "nt":
                        _kill_process_group(proc.pid)
                    else:
                        proc.kill()
                    proc.wait(timeout=10)
                raise
        with output.open("rb") as stream:
            raw = stream.read(max_output_bytes)
        text = str(sanitize(raw.decode("utf-8", errors="replace")))
        result = {"argv": sanitize(argv), "returncode": proc.returncode,
                  "elapsed_seconds": time.monotonic() - started, "output": text,
                  "status": stopped or ("SUCCEEDED" if proc.returncode == 0 else "FAILED")}
        if log:
            write_json(log, result)
        if stopped:
            raise CVRSError("ENV_" + stopped, "owned command terminated; inspect the bounded operation log")
        if proc.returncode:
            raise CVRSError("ENV_COMMAND_FAILED", "command failed; inspect the sanitized operation log")
        return result
