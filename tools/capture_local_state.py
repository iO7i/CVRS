"""Capture bounded local hardware/tool state without reading secrets or datasets."""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def command_version(command: str) -> dict[str, object]:
    path = shutil.which(command)
    if not path:
        return {"path": None, "version": None}
    try:
        result = subprocess.run([command, "--version"], capture_output=True, text=True, timeout=15)
        output = (result.stdout + result.stderr).strip().splitlines()
        return {"path": path, "version": output[0] if output else None, "returncode": result.returncode}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"path": path, "version": None, "error": type(exc).__name__}


def powershell_json(script: str) -> object:
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else {"status": "UNAVAILABLE"}
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"status": "UNAVAILABLE", "reason": type(exc).__name__}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error(f"refusing to overwrite existing evidence: {args.out}")
    root = args.out.resolve().parents[1]
    state = {
        "schema": "cvrs.local-state.v1",
        "status": "OBSERVED_NO_EXECUTION",
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "platform": platform.platform(),
        "commands": {name: command_version(name) for name in ("python", "uv", "docker", "conda", "apptainer", "nvidia-smi")},
        "gpu": powershell_json("Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,AdapterRAM,VideoProcessor | ConvertTo-Json -Depth 3"),
        "drives": powershell_json("Get-PSDrive C,D | Select-Object Name,Free,Used | ConvertTo-Json -Depth 3"),
        "workspace": str(root),
        "limits": [
            "Presence and version strings are not native execution proof.",
            "No model, dataset, credential, protected data, or external path is read.",
            "No install, download, GPU job, or paid compute is started by this capture.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": state["status"], "output": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
