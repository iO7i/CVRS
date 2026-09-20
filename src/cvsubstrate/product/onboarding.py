"""Guided inspect → configure → approve → run, without speculative execution."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from cvsubstrate.adoption.common import output_tree, write_text, load_config
from cvsubstrate.adoption.inspect import inspect_repository
from cvsubstrate.adoption.wrapping import wrap_repository, validate_paper, run_paper
from cvsubstrate.adoption.contracts import PaperRunSpec
from cvsubstrate.provenance.io import read_json, write_json, digest, file_digest
from cvsubstrate.errors import CVRSError
from cvsubstrate.product.environments import EnvironmentManager


def prepare_paper(repo: Path, destination: Path, *, python: str | None = None,
                  store: Path | None = None, environment: str | None = None,
                  decisions: dict | None = None) -> dict:
    """Write explicit decisions, source evidence and unresolved prerequisites.

    A scanner's `train.py` candidate is never promoted into an approved command.
    `decisions` supplies exact argv, outputs, input bindings and operation names.
    """
    if store or environment:
        if not (store and environment) or python:
            raise ValueError("use --python or both --store and --environment")
        python = EnvironmentManager(store).interpreter(environment)
    decisions = decisions or {}
    allowed = {"operations", "inputs", "purpose", "notes"}
    if set(decisions) - allowed:
        raise ValueError("unknown paper preparation decision keys")
    result = wrap_repository(repo, destination, python=python or sys.executable,
        commands=decisions.get("operations"), purpose=decisions.get("purpose", "research"))
    out = Path(destination)
    spec = PaperRunSpec.model_validate(read_json(out / "paper.json"))
    spec.inputs = decisions.get("inputs", {})
    spec.input_digests = {}
    issues = []
    for key, value in spec.inputs.items():
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", key):
            raise ValueError("invalid input binding name")
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = (Path(repo) / path).resolve()
        spec.inputs[key] = str(path)
        if path.is_file():
            spec.input_digests[key] = file_digest(path)
        elif path.is_dir():
            issues.append({"code": "DIRECTORY_CLOSURE_REQUIRED", "input": key,
                           "action": "Bind a versioned dataset manifest; a directory name alone is not content identity."})
        else:
            issues.append({"code": "INPUT_MISSING", "input": key})
    spec.trust_code = False
    spec.unresolved = [] if spec.operations else ["Review candidate argv and explicitly configure at least one operation."]
    if any(x["code"] == "INPUT_MISSING" for x in issues):
        spec.unresolved.append("Some explicitly requested inputs are missing.")
    write_json(out / "paper.json", spec)
    report = read_json(out / "repository-report.json")
    write_json(out / "decisions.json", decisions)
    write_json(out / "onboarding.json", {"source_digest": report["root_identity"],
        "frameworks": report["frameworks"], "candidates": report["command_candidates"],
        "issues": issues, "approval": "NOT_APPROVED", "command_source": "USER_REVIEWED" if spec.operations else "UNRESOLVED"})
    write_text(out / "NEXT_STEPS.md", "# Native paper handoff\n\n"
        "1. Read `repository-report.json`, then fill exact operations and named outputs in `paper.json`.\n"
        "2. Bind local assets using a decisions file. Directory inputs need their own data manifest.\n"
        "3. Run `cvrs paper readiness paper.json`. Resolve blockers; warnings remain visible.\n"
        "4. Run `cvrs paper approve paper.json --actor YOUR_ID --out approval.json`.\n"
        "5. Execute `cvrs paper execute paper.json --approval approval.json --operation predict --out NEW_OUTPUT --trust`.\n\n"
        "Approval is bound to the exact spec and source identity. It is an authorization receipt, not proof that code is safe.\n")
    return {**result, "readiness": readiness(out / "paper.json"), "source_modified": False}


def readiness(spec_path: Path) -> dict:
    spec = PaperRunSpec.model_validate(load_config(spec_path))
    result = validate_paper(spec_path)
    blockers = list(result.get("issues", []))
    # Older validation uses status/requirements; retain it verbatim, don't infer a pass.
    if not spec.operations:
        blockers.append("No reviewed native operations.")
    for key, value in spec.inputs.items():
        if not Path(value).exists():
            blockers.append("Missing bound asset: " + key)
    for operation, command in spec.operations.items():
        if not command.outputs:
            blockers.append(operation + ": declare at least one output for evidence capture.")
    warnings = ["Native source/config/checkpoint execution requires explicit trust."]
    if any(Path(v).is_dir() for v in spec.inputs.values()):
        warnings.append("Directory inputs are partially identified; bind a content-addressed dataset manifest.")
    ready = result.get("status") in {"READY", "VALID", "READY_FOR_TRUSTED_EXECUTION"} and not blockers
    # validate_paper's native status is AUTHOR_REVIEW/READY; handled explicitly.
    if not blockers and result.get("status") == "READY":
        ready = True
    return {"status": "READY_FOR_APPROVAL" if ready else "NOT_READY", "validation": result,
            "blockers": sorted(set(blockers)), "warnings": warnings, "spec_digest": digest(spec),
            "operations": sorted(spec.operations)}


def approve_paper(spec_path: Path, actor: str, destination: Path) -> dict:
    if not actor.strip():
        raise ValueError("approval needs an explicit actor identifier")
    report = readiness(spec_path)
    if report["status"] != "READY_FOR_APPROVAL":
        raise CVRSError("PAPER_NOT_READY", "resolve readiness blockers before approving")
    if destination.exists():
        raise CVRSError("OUTPUT_EXISTS", "approval receipts are never overwritten")
    spec = PaperRunSpec.model_validate(load_config(spec_path))
    # Preserve the unapproved specification. Approval creates a separate derived
    # native-execution specification so --trust is never silently assumed.
    approved = spec.model_copy(update={"trust_code": True})
    approved_path = destination.with_name(destination.stem + ".approved-paper.json")
    if approved_path.exists():
        raise CVRSError("OUTPUT_EXISTS", "derived approval specification already exists")
    receipt = {"schema_version": "1.0", "actor": actor, "spec_digest": digest(spec),
               "approved_spec_digest": digest(approved), "approved_spec_file": approved_path.name,
               "repository_digest": spec.repository_digest, "operations": sorted(spec.operations),
               "scope": "authorization to invoke the exact reviewed native commands; no safety certification"}
    receipt["receipt_digest"] = digest(receipt)
    write_json(approved_path, approved)
    try:
        write_json(destination, receipt)
    except BaseException:
        approved_path.unlink(missing_ok=True)
        raise
    return receipt


def execute_approved(spec_path: Path, approval_path: Path, operation: str, destination: Path,
                     *, trust: bool = False) -> dict:
    receipt = read_json(approval_path)
    if receipt.get("receipt_digest") != digest({k: v for k, v in receipt.items() if k != "receipt_digest"}):
        raise CVRSError("APPROVAL_TAMPERED", "approval receipt changed")
    spec = PaperRunSpec.model_validate(load_config(spec_path))
    if receipt["spec_digest"] != digest(spec) or operation not in receipt["operations"]:
        raise CVRSError("APPROVAL_STALE", "paper spec/operation differs from approved decisions")
    if not trust:
        raise CVRSError("TRUST_REQUIRED", "explicit --trust is still required for native code")
    from cvsubstrate.provenance.io import safe_join
    approved_path = safe_join(approval_path.parent, receipt["approved_spec_file"])
    approved = PaperRunSpec.model_validate(read_json(approved_path))
    if digest(approved) != receipt["approved_spec_digest"] or approved.model_copy(update={"trust_code": spec.trust_code}) != spec:
        raise CVRSError("APPROVAL_TAMPERED", "derived approved specification changed")
    result = run_paper(approved_path, operation, destination, trust=True)
    return {**result, "approval_digest": receipt["receipt_digest"]}
