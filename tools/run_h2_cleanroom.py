"""Run the H2 proof from an installed candidate wheel outside the source checkout."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv


PROBE = r'''
from __future__ import annotations
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from cvsubstrate.artifacts.capsule import create_capsule, validate_capsule
from cvsubstrate.errors import CVRSError
from cvsubstrate.product.qualification_browser import render_qualification_browser
from cvsubstrate.provenance.io import file_digest

root = Path(sys.argv[1]).resolve()
package = Path(__import__("cvsubstrate").__file__).resolve()
forbidden = ["torch", "torchvision", "transformers", "mmdet", "mmcv", "mmseg", "mmrotate"]
frameworks_absent = {name: importlib.util.find_spec(name) is None for name in forbidden}
if not all(frameworks_absent.values()):
    raise RuntimeError("clean-room contains an ML framework")
if "site-packages" not in package.as_posix().lower():
    raise RuntimeError(f"package was not imported from site-packages: {package}")

rq001 = root / "inputs" / "rq001-portable"
manifest = json.loads((rq001 / "manifest.json").read_text("utf-8"))
rq001_checks = []
for item in manifest["files"]:
    path = rq001 / item["path"]
    rq001_checks.append(
        path.is_file() and path.stat().st_size == item["bytes"] and file_digest(path) == item["sha256"]
    )
if not rq001_checks or not all(rq001_checks):
    raise RuntimeError("RQ001 portable manifest verification failed")

matrix_path = root / "inputs" / "qualification-matrix.json"
matrix = json.loads(matrix_path.read_text("utf-8"))
rq002_root = root / "inputs" / "rq002-evidence"
rq002_files = [rq002_root / lane["evidence"] for lane in matrix["lanes"] if lane["reference"] == "CVRS_REFERENCE_002"]
if not rq002_files or not all(path.is_file() for path in rq002_files):
    raise RuntimeError("staged RQ002 evidence is incomplete")

dinov2 = json.loads(
    (rq002_root / "qualification/evidence/dinov2-public-2026-09-20/qualification/report.json").read_text("utf-8")
)
similarity = dinov2["retrieval_from_reloaded_artifact"]["cosine_similarity"]
nearest = [max(range(len(row)), key=row.__getitem__) for row in similarity]
reevaluation = {
    "kind": "saved_artifact_metadata_only",
    "model_rerun": False,
    "nearest_indices_recomputed": nearest,
    "matches_recorded": nearest == dinov2["retrieval_from_reloaded_artifact"]["nearest_indices"],
    "feature_artifact_sha256_matches": file_digest(
        rq002_root / "qualification/evidence/dinov2-public-2026-09-20/qualification/features.npz"
    ) == dinov2["features"]["artifact_sha256"],
}
if not all((reevaluation["matches_recorded"], reevaluation["feature_artifact_sha256_matches"])):
    raise RuntimeError("saved DINOv2 artifact re-evaluation failed")

browser = render_qualification_browser(matrix_path, root / "browser")
capsule_source = root / "inputs"
capsule = create_capsule(capsule_source, root / "capsule")
capsule_validation = validate_capsule(root / "capsule")
if capsule_validation["status"] != "VERIFIED":
    raise RuntimeError("clean-room capsule did not verify")

tamper = root / "tamper-capsule"
shutil.copytree(root / "capsule", tamper)
tamper_target = next((tamper / "evidence").rglob("*.json"))
tamper_target.write_bytes(tamper_target.read_bytes() + b"\n")
tamper_rejected = validate_capsule(tamper)["status"] != "VERIFIED"

missing = root / "missing-capsule"
shutil.copytree(root / "capsule", missing)
missing_target = next((missing / "evidence").rglob("*.json"))
missing_target.unlink()
missing_rejected = validate_capsule(missing)["status"] != "VERIFIED"
if not tamper_rejected or not missing_rejected:
    raise RuntimeError("negative integrity controls failed")

report = {
    "schema": "cvrs.h2.cleanroom.v1",
    "status": "PASS_CLEANROOM_WHEEL_ONLY",
    "python": sys.version,
    "package_import": str(package),
    "source_checkout_on_sys_path": False,
    "ml_frameworks_absent": frameworks_absent,
    "rq001_manifest_files_verified": len(rq001_checks),
    "rq002_evidence_files_verified": len(rq002_files),
    "browser": browser,
    "capsule": capsule,
    "capsule_validation": capsule_validation,
    "saved_artifact_reevaluation": reevaluation,
    "tamper_rejected": tamper_rejected,
    "missing_evidence_rejected": missing_rejected,
}
(root / "cleanroom-report.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
print(json.dumps(report))
'''


def _copy_inputs(matrix_path: Path, rq001: Path, rq002_root: Path, root: Path) -> None:
    inputs = root / "inputs"
    inputs.mkdir(parents=True)
    shutil.copy2(matrix_path, inputs / "qualification-matrix.json")
    shutil.copytree(rq001, inputs / "rq001-portable")
    matrix = json.loads(matrix_path.read_text("utf-8"))
    destination = inputs / "rq002-evidence"
    for lane in matrix["lanes"]:
        if lane["reference"] != "CVRS_REFERENCE_002":
            continue
        relative = Path(lane["evidence"])
        source = rq002_root / relative
        if not source.is_file():
            raise FileNotFoundError(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    dino_root = Path("qualification/evidence/dinov2-public-2026-09-20/qualification")
    for name in ("report.json", "features.npz"):
        source = rq002_root / dino_root / name
        target = destination / dino_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--rq001-portable", type=Path, required=True)
    parser.add_argument("--rq002-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        raise ValueError("clean-room output must be new")
    out.mkdir(parents=True)
    _copy_inputs(args.matrix.resolve(), args.rq001_portable.resolve(), args.rq002_root.resolve(), out)
    environment = out / "venv"
    venv.EnvBuilder(with_pip=True, clear=False).create(environment)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    subprocess.run(
        [str(python), "-m", "pip", "install", "--disable-pip-version-check", str(args.wheel.resolve())],
        check=True,
        cwd=out,
    )
    probe = out / "probe.py"
    probe.write_text(PROBE, "utf-8")
    env = {**os.environ, "PYTHONPATH": "", "PYTHONNOUSERSITE": "1"}
    result = subprocess.run(
        [str(python), "-I", str(probe), str(out)],
        check=False,
        cwd=out,
        env=env,
        text=True,
        capture_output=True,
    )
    (out / "probe.stdout.log").write_text(result.stdout, "utf-8")
    (out / "probe.stderr.log").write_text(result.stderr, "utf-8")
    if result.returncode:
        print(result.stderr, file=sys.stderr)
        return result.returncode
    print(result.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
