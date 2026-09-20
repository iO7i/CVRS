"""Reference Qualification 002 control-plane helper.

This tool validates the frozen qualification contract and materializes evidence
bookkeeping. It never downloads models, changes environments, or starts paid work.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "reference-cases" / "CVRS_REFERENCE_002.json"
EXPECTED_LANES = {
    "OML-LEGACY", "OML-MODERN", "OML-ROTATED", "OML-SEG", "OML-DEPLOY",
    "ULTRALYTICS", "GROUNDING", "SAM3", "DINOV3", "TORCHGEO",
    "SUPERVISION", "FIFTYONE", "CLEANROOM",
}
LANE_STATUSES = {"UNLOCKED", "NOT_RUN", "PASS", "FAIL", "BLOCKED_EXTERNAL"}


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    if plan.get("schema_version") != "cvrs.reference-qualification.v1":
        raise ValueError("unexpected qualification schema")
    if plan.get("id") != "CVRS_REFERENCE_002":
        raise ValueError("wrong qualification ID")
    reference_001 = ROOT / "docs" / "reference-cases" / "CVRS_REFERENCE_001_DESERTSYNTH.md"
    if plan.get("reference_001_sha256") != sha256_file(reference_001):
        raise ValueError("Reference Qualification 001 changed")
    lanes = plan.get("lanes")
    if not isinstance(lanes, list):
        raise ValueError("lanes must be a list")
    lane_ids = [row.get("id") for row in lanes]
    if set(lane_ids) != EXPECTED_LANES or len(lane_ids) != len(set(lane_ids)):
        raise ValueError("mandatory lane set changed")
    if any(row.get("status") not in LANE_STATUSES for row in lanes):
        raise ValueError("invalid lane status")
    gates = plan.get("gates")
    expected_gates = {f"R2.{index:02d}" for index in range(1, 26)}
    gate_ids = [row.get("id") for row in gates] if isinstance(gates, list) else []
    if set(gate_ids) != expected_gates or len(gate_ids) != len(set(gate_ids)):
        raise ValueError("R2.01-R2.25 gate set changed")
    constraints = plan.get("constraints", {})
    for key in (
        "paid_compute_authorized",
        "large_downloads_authorized",
        "gated_model_access_authorized",
        "mock_outputs_satisfy_native_gate",
        "silent_geometry_normalization_allowed",
        "protected_data_allowed",
    ):
        if constraints.get(key) is not False:
            raise ValueError(f"frozen constraint changed: {key}")
    if constraints.get("native_reference_required") is not True:
        raise ValueError("native reference requirement cannot be relaxed")
    return {"status": "VALID", "lanes": len(lanes), "gates": len(gates)}


def command_path(name: str) -> str | None:
    return shutil.which(name)


def git_state() -> dict[str, Any]:
    try:
        revision = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
        dirty = bool(subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True).strip())
        return {"revision": revision, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"revision": None, "dirty": None}


def inventory() -> dict[str, Any]:
    from cvsubstrate.adoption.environments import list_packs

    root_usage = shutil.disk_usage(ROOT)
    home_usage = shutil.disk_usage(Path.home())
    tools = {name: command_path(name) for name in ("git", "uv", "docker", "conda", "apptainer", "nvidia-smi")}
    return {
        "status": "OBSERVED_NO_EXECUTION",
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "platform": platform.platform(),
        "git": git_state(),
        "tools": tools,
        "storage": {
            "workspace_free_bytes": root_usage.free,
            "home_free_bytes": home_usage.free,
            "workspace_drive": str(ROOT.anchor),
            "home_drive": str(Path.home().anchor),
        },
        "declared_packs": list_packs(),
        "limits": [
            "Command presence is not runtime compatibility or native execution proof.",
            "No model/data download, framework import, GPU job, or paid compute was started.",
        ],
    }


def h0_packet(destination: Path) -> dict[str, Any]:
    plan = read_json(PLAN)
    validate_plan(plan)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("H0 destination must be absent or empty")
    destination.mkdir(parents=True, exist_ok=True)
    observed = inventory()
    packet = {
        "qualification": plan["id"],
        "plan_sha256": sha256_file(PLAN),
        "approval_status": "HUMAN_APPROVAL_REQUIRED",
        "observed": observed,
        "decisions_required": [
            "approve exact model/source/checkpoint locks after they are resolved",
            "approve dataset downloads and storage plan",
            "approve any gated model access",
            "approve any paid GPU/cloud cap",
            "approve H1 expansion after small-stage visual review",
        ],
    }
    write_json(destination / "h0-inventory.json", packet)
    return packet


def validate_lane_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    lane_id = receipt.get("lane_id")
    status = receipt.get("status")
    if lane_id not in EXPECTED_LANES:
        raise ValueError("receipt uses unknown lane")
    if status not in {"PASS", "FAIL", "BLOCKED_EXTERNAL"}:
        raise ValueError("receipt status must be PASS, FAIL, or BLOCKED_EXTERNAL")
    if receipt.get("mock_output") is True:
        raise ValueError("mock output cannot qualify a lane")
    if status == "PASS":
        native = receipt.get("native_reference", {})
        cvrs = receipt.get("cvrs_path", {})
        source = receipt.get("source", {})
        artifacts = receipt.get("artifacts", {})
        if native.get("executed") is not True or cvrs.get("executed") is not True:
            raise ValueError("PASS requires native and CVRS execution")
        if not source.get("revision"):
            raise ValueError("PASS requires a pinned source revision")
        digest_value = artifacts.get("manifest_sha256")
        if not isinstance(digest_value, str) or len(digest_value) != 64:
            raise ValueError("PASS requires an artifact manifest SHA-256")
    if status == "BLOCKED_EXTERNAL" and not receipt.get("reason"):
        raise ValueError("blocked receipt requires a reason")
    return {"status": "VALID", "lane_id": lane_id, "lane_status": status}


def summarize(evidence_dir: Path) -> dict[str, Any]:
    receipts: dict[str, dict[str, Any]] = {}
    for path in sorted(evidence_dir.glob("lane-*.json")):
        value = read_json(path)
        validate_lane_receipt(value)
        if value["lane_id"] in receipts:
            raise ValueError("duplicate lane receipt")
        receipts[value["lane_id"]] = value
    matrix = {
        lane: receipts.get(lane, {"lane_id": lane, "status": "NOT_RUN"})["status"]
        for lane in sorted(EXPECTED_LANES)
    }
    overall = "PASS" if all(value == "PASS" for value in matrix.values()) else "INCOMPLETE"
    return {"status": overall, "lanes": matrix, "receipts": len(receipts)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-plan")
    h0 = sub.add_parser("h0")
    h0.add_argument("--out", type=Path, required=True)
    receipt = sub.add_parser("validate-receipt")
    receipt.add_argument("receipt", type=Path)
    status = sub.add_parser("status")
    status.add_argument("evidence_dir", type=Path)
    args = parser.parse_args(argv)

    if args.command == "validate-plan":
        result = validate_plan(read_json(PLAN))
    elif args.command == "h0":
        result = h0_packet(args.out)
    elif args.command == "validate-receipt":
        result = validate_lane_receipt(read_json(args.receipt))
    else:
        result = summarize(args.evidence_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
