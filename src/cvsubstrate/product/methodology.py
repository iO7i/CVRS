"""Auditable research-method checks; findings are not scientific verdicts.

The rule engine compares explicit evidence, not inferred intent. In particular,
using a dataset's class vocabulary is legitimate for many zero-shot protocols;
per-image target labels/boxes create a different, oracle-assisted task.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Any, Literal
from cvsubstrate.adoption.methodology import evaluation_equivalence, experiment_diff
from cvsubstrate.product.contracts import ProductFinding
from cvsubstrate.provenance.io import digest

RULESET_VERSION = "2.0"


def review_methodology(value: dict[str, Any]) -> dict:
    allowed = {"schema_version", "arms", "baseline", "evaluation", "baseline_evaluation",
               "prompts", "assets", "lineage", "split_policy", "test_accesses", "selection",
               "declared_interventions", "hypothesis", "seeds", "exclusions", "protocol"}
    if set(value) - allowed:
        raise ValueError("unrecognized methodology fields: " + ", ".join(sorted(set(value) - allowed)))
    findings: list[ProductFinding] = []
    coverage: dict[str, str] = {}

    def add(rule: str, severity: Literal["INFO", "WARN", "BLOCK", "UNKNOWN"], text: str, evidence: Any = None, remedy: str | None = None):
        records = evidence if isinstance(evidence, list) else ([] if evidence is None else [evidence])
        records = [r if isinstance(r, dict) else {"value": r} for r in records]
        findings.append(ProductFinding(rule_id=rule, severity=severity, message=text,
                                       evidence=records, remediation=remedy, rule_version=RULESET_VERSION))

    arms = value.get("arms", [])
    ids = [a.get("id") for a in arms]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("campaign arms need unique nonempty IDs")
    interventions = set(value.get("declared_interventions", []))
    coverage["training_budgets"] = "OBSERVED_OR_DECLARED" if arms else "MISSING"
    if len(arms) > 1:
        for field in ("real_exposures", "synthetic_exposures", "optimizer_updates", "total_samples", "compute_seconds"):
            known = []
            for arm in arms:
                record = arm.get(field)
                if record is None:
                    continue
                if isinstance(record, (int, float)):
                    record = {"value": record, "origin": "declared"}
                if not isinstance(record, dict) or set(record) - {"value", "origin", "evidence_digest"}:
                    raise ValueError("budget values require value/origin and optional evidence_digest")
                v = record.get("value")
                if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0 or not __import__('math').isfinite(v):
                    raise ValueError("budgets must be finite nonnegative numbers")
                origin = record.get("origin", "unknown")
                if origin not in {"observed", "planned", "declared", "unknown"}:
                    raise ValueError("invalid budget origin")
                if origin == "observed" and not record.get("evidence_digest"):
                    add("OBSERVATION_WITHOUT_RECEIPT", "UNKNOWN", "A measured budget has no evidence reference.", {"arm": arm["id"], "field": field})
                known.append({"arm": arm["id"], **record})
            if len(known) != len(arms):
                add("BUDGET_INCOMPLETE", "UNKNOWN", f"{field} is not recorded for every arm.", {"field": field, "present": len(known), "arms": len(arms)})
            if any(x.get("origin") != "observed" for x in known):
                add("PLANNED_NOT_OBSERVED", "INFO", f"{field} is not wholly based on measured execution.", known)
            if len({x["value"] for x in known}) > 1:
                intentional = field in interventions
                add("BUDGET_DIFFERENCE", "INFO" if intentional else "WARN",
                    f"{field} differs across arms" + (" as a declared intervention." if intentional else "; this may confound the stated comparison."),
                    known, "Use an exposure-matched control or disclose the differing budget; not every budget can be matched simultaneously.")
    elif not arms:
        add("BUDGETS_MISSING", "UNKNOWN", "No training-budget evidence was supplied.")

    if value.get("evaluation") and value.get("baseline_evaluation"):
        eq = evaluation_equivalence(value["baseline_evaluation"], value["evaluation"])
        coverage["evaluation"] = eq["status"]
        if eq["status"] != "EQUIVALENT_DECLARED_PROTOCOL":
            add("EVALUATION_PROTOCOL", "BLOCK" if eq["status"] == "INCOMPATIBLE" else "UNKNOWN",
                "A common metric name does not establish evaluation equivalence.", eq,
                "Resolve differences before publishing a directly ranked comparison; otherwise report descriptive results separately.")
    else:
        coverage["evaluation"] = "MISSING"
        add("EVALUATION_MISSING", "UNKNOWN", "Both exact evaluation protocols are required to assess equivalence.")

    prompts = value.get("prompts", [])
    coverage["prompt_provenance"] = "REVIEWED" if "prompts" in value else "MISSING"
    for prompt in prompts:
        source = prompt.get("source", "unknown")
        track = prompt.get("track", "unspecified")
        if source in {"dataset_class_vocabulary", "predeclared_vocabulary"}:
            add("DECLARED_CLASS_VOCABULARY", "INFO", "Using the declared class vocabulary is not by itself label leakage.", prompt)
        elif source in {"ground_truth_box", "ground_truth_mask", "per_image_ground_truth_label", "ground_truth", "oracle"}:
            allowed_track = track in {"oracle", "oracle_assisted", "prompted_gt_box"}
            add("ORACLE_ASSISTANCE", "INFO" if allowed_track else "BLOCK",
                "Ground-truth-derived prompts change the task; keep an explicitly declared oracle-assisted track.", prompt,
                "Do not compare this directly to fully automatic detection without disclosing the oracle inputs.")
        elif source in {"external", "generated", "human_annotated"}:
            if not prompt.get("provenance_digest"):
                add("PROMPT_PROVENANCE_MISSING", "UNKNOWN", "The declared prompt source lacks a pinned provenance reference.", prompt)
        else:
            add("PROMPT_ORIGIN_UNKNOWN", "UNKNOWN", "Prompt origin is not recorded in a recognized form.", prompt)
    for asset in value.get("assets", []):
        sha = asset.get("sha256", "")
        if not __import__('re').fullmatch(r"[0-9a-f]{64}", sha):
            add("ASSET_NOT_CONTENT_PINNED", "WARN", "Asset lacks an exact content digest.", asset, "Lock both model and processor/tokenizer components.")
        if asset.get("revision") in {"main", "master", "latest"}:
            add("FLOATING_REVISION", "WARN", "The asset revision can change between runs.", asset, "Resolve and retain an immutable source revision and selected-file hashes.")
    coverage["asset_identity"] = "REVIEWED" if "assets" in value else "MISSING"

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    protected_kinds = set(value.get("split_policy", {}).get("must_not_cross", ["parent_frame", "source_scene", "photogrammetry_source", "source_raster"]))
    for row in value.get("lineage", []):
        for kind, ident in row.get("parents", {}).items():
            if ident is not None:
                groups[(kind, str(ident))].append({"sample_id": row.get("sample_id"), "split": row.get("split")})
    for (kind, ident), rows in groups.items():
        splits = {x["split"] for x in rows}
        if splits & {"train", "pretrain"} and splits & {"test", "locked_test", "validation", "dev", "selection"}:
            prohibited = kind in protected_kinds
            add("SHARED_LINEAGE", "BLOCK" if prohibited else "WARN",
                "Declared shared lineage violates the split policy." if prohibited else "Shared asset lineage crosses splits; its acceptability depends on the generalization claim.",
                {"kind": kind, "identity": ident, "samples": rows}, "Review the split policy and intended population; sharing a reusable mesh is not universally contamination.")
    coverage["lineage"] = "REVIEWED" if "lineage" in value else "MISSING"
    for access in value.get("test_accesses", []):
        if access.get("purpose") in {"tuning", "selection"} or access.get("before_selection") is True:
            add("PROTECTED_TEST_SELECTION", "BLOCK", "The access record shows protected-test use in selection or tuning.", access)
        elif not access.get("authorization_digest"):
            add("TEST_ACCESS_UNBOUND", "UNKNOWN", "Final test access lacks an authorization reference.", access)
    coverage["test_access"] = "REVIEWED" if "test_accesses" in value else "MISSING"
    seeds = value.get("seeds", {})
    if seeds:
        declared, included = set(seeds.get("declared", [])), set(seeds.get("included", []))
        excluded = declared - included
        reasons = {e.get("seed"): e.get("reason") for e in value.get("exclusions", [])}
        unexplained = sorted(x for x in excluded if not reasons.get(x))
        if unexplained:
            add("UNEXPLAINED_SEED_OMISSION", "BLOCK", "Some predeclared seeds are absent without a recorded reason.", {"seeds": unexplained})
        if included - declared:
            add("UNDECLARED_SEEDS", "WARN", "Included seeds extend the preregistered selection.", {"seeds": sorted(included - declared)})
    severity = {"INFO": 0, "UNKNOWN": 1, "WARN": 2, "BLOCK": 3}
    largest = max((severity[x.severity] for x in findings), default=0)
    return {"schema_version": "1.0", "ruleset": RULESET_VERSION, "input_digest": digest(value),
            "status": {0: "NO_DECLARED_CONFLICTS", 1: "INSUFFICIENT_EVIDENCE", 2: "REVIEW_REQUIRED", 3: "PROTOCOL_BLOCKERS"}[largest],
            "findings": [x.model_dump(mode="json") for x in findings], "coverage": coverage,
            "limits": "Checks apply only to the supplied declarations and receipts. No absence-of-leakage, misconduct, causal validity or scientific truth claim is inferred."}


def review_report(value: dict) -> str:
    report = review_methodology(value)
    rows = ["# Research methodology review", "", f"Status: **{report['status']}**", "",
            f"Ruleset: `{report['ruleset']}` · Input: `{report['input_digest']}`", ""]
    for f in report["findings"]:
        rows.extend([f"## {f['severity']} — {f['rule_id']}", f["message"], f.get("remediation") or "", ""])
    rows += ["## Coverage", *[f"- {k}: {v}" for k, v in report["coverage"].items()], "", report["limits"]]
    return "\n".join(rows)
