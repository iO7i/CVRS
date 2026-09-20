"""Native COCO evaluation without canonical geometry rewriting.

This path is for evidence-preserving reproduction of existing COCO-style
artifacts whose native geometry cannot be represented by strict CVRS
DatasetManifest contracts. It never clips, renumbers, or repairs geometry.
"""
from __future__ import annotations

import contextlib
import importlib.metadata
import io
import math
from pathlib import Path
from typing import Any

from cvsubstrate.contracts.models import EvaluationProtocol
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import digest, file_digest, read_json


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def audit_coco_geometry(payload: dict[str, Any], *, example_limit: int = 25) -> dict[str, Any]:
    images = {row["id"]: row for row in payload.get("images", []) if isinstance(row, dict) and "id" in row}
    counts = {"total": 0, "nonfinite": 0, "degenerate": 0, "x1<0": 0, "y1<0": 0, "x2>width": 0, "y2>height": 0}
    examples: list[dict[str, Any]] = []
    for ann in payload.get("annotations", []):
        counts["total"] += 1
        bbox = ann.get("bbox") if isinstance(ann, dict) else None
        reasons: list[str] = []
        if not isinstance(bbox, list) or len(bbox) != 4 or not all(_finite_number(v) for v in bbox):
            counts["nonfinite"] += 1
            reasons.append("nonfinite_or_malformed")
        else:
            x, y, w, h = map(float, bbox)
            image = images.get(ann.get("image_id"))
            if w <= 0 or h <= 0:
                counts["degenerate"] += 1
                reasons.append("degenerate")
            if x < 0:
                counts["x1<0"] += 1
                reasons.append("x1<0")
            if y < 0:
                counts["y1<0"] += 1
                reasons.append("y1<0")
            if image is not None:
                if x + w > float(image["width"]):
                    counts["x2>width"] += 1
                    reasons.append("x2>width")
                if y + h > float(image["height"]):
                    counts["y2>height"] += 1
                    reasons.append("y2>height")
        if reasons and len(examples) < example_limit:
            examples.append({"id": ann.get("id"), "image_id": ann.get("image_id"), "bbox": bbox, "reasons": reasons})
    return {"counts": counts, "examples": examples, "has_noncanonical_geometry": any(counts[k] for k in counts if k != "total"),
            "example_count": len(examples), "note": "Counts may overlap when one box violates multiple bounds; no geometry was changed."}


def _protocol(value: EvaluationProtocol | dict[str, Any] | None) -> EvaluationProtocol:
    if value is None:
        return EvaluationProtocol()
    if isinstance(value, EvaluationProtocol):
        return value
    return EvaluationProtocol.model_validate(value)


def evaluate_native_coco(
    annotations: Path,
    detections: Path,
    *,
    protocol: EvaluationProtocol | dict[str, Any] | None = None,
    image_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Evaluate native COCO JSON without constructing strict CVRS geometry contracts."""
    protocol = _protocol(protocol)
    if protocol.evaluator != "pycocotools":
        raise CVRSError("EVALUATOR", "native COCO reproduction requires pycocotools")
    try:
        import numpy as np
        from pycocotools.coco import COCO
        from pycocotools.cocoeval import COCOeval
    except ImportError as exc:
        raise CVRSError("COCO_DEPENDENCY", "pycocotools==2.0.11 and numpy are required") from exc
    version = importlib.metadata.version("pycocotools")
    if version != protocol.evaluator_version:
        raise CVRSError("EVALUATOR_VERSION", f"expected {protocol.evaluator_version}, found {version}")
    annotation_payload = read_json(annotations)
    detection_payload = read_json(detections)
    if not isinstance(annotation_payload, dict) or not isinstance(detection_payload, list):
        raise CVRSError("COCO_FORMAT", "expected COCO annotation object and detection list")
    image_rows = annotation_payload.get("images", [])
    image_map = {row["id"]: row for row in image_rows if isinstance(row, dict) and "id" in row}
    known_categories = {row["id"] for row in annotation_payload.get("categories", []) if isinstance(row, dict) and "id" in row}
    selected = set(image_ids) if image_ids is not None else set(image_map)
    if not selected or not selected <= set(image_map):
        raise CVRSError("IMAGE_UNIVERSE", "selected image IDs must be a nonempty subset of annotation images")
    filtered: list[dict[str, Any]] = []
    for row in detection_payload:
        if not isinstance(row, dict) or row.get("image_id") not in image_map:
            raise CVRSError("DETECTION_IMAGE", "detection references an unknown image")
        if row.get("category_id") not in known_categories:
            raise CVRSError("DETECTION_CATEGORY", "detection references an unknown category")
        bbox = row.get("bbox")
        score = row.get("score")
        if not isinstance(bbox, list) or len(bbox) != 4 or not all(_finite_number(v) for v in bbox):
            raise CVRSError("DETECTION_GEOMETRY", "detection bbox must contain four finite numbers")
        if not _finite_number(score) or not 0 <= float(score) <= 1:
            raise CVRSError("DETECTION_SCORE", "detection score must be finite and within [0,1]")
        if row["image_id"] in selected and float(score) >= protocol.score_threshold:
            filtered.append(row)
    with contextlib.redirect_stdout(io.StringIO()):
        gt = COCO(str(annotations))
        if filtered:
            dt = gt.loadRes(filtered)
        else:
            dt = COCO()
            dt.dataset = {"images": [image_map[i] for i in sorted(selected)], "categories": annotation_payload["categories"], "annotations": []}
            dt.createIndex()
        ev = COCOeval(gt, dt, "bbox")
        ev.params.imgIds = sorted(selected)
        ev.params.catIds = sorted(known_categories)
        ev.params.iouThrs = np.asarray(protocol.iou_thresholds)
        ev.params.recThrs = np.asarray(protocol.recall_thresholds)
        ev.params.maxDets = list(protocol.max_detections)
        ev.params.areaRng = list(protocol.area_ranges.values())
        ev.params.areaRngLbl = list(protocol.area_ranges)
        ev.params.useCats = 1
        ev.evaluate()
        ev.accumulate()

    metrics: dict[str, float | None] = {}
    for ai, area in enumerate(protocol.area_ranges):
        for mi, maximum in enumerate(protocol.max_detections):
            for label, values in (
                ("AP", ev.eval["precision"][:, :, :, ai, mi]),
                ("AR", ev.eval["recall"][:, :, ai, mi]),
            ):
                valid = values[values > -1]
                metrics[f"{label}/{area}/maxDets={maximum}"] = None if not valid.size else float(valid.mean())
    audit_payload = {
        "images": [image_map[i] for i in sorted(selected)],
        "annotations": [row for row in annotation_payload.get("annotations", []) if row.get("image_id") in selected],
    }
    geometry = audit_coco_geometry(audit_payload)
    identity = {
        "annotations_sha256": file_digest(annotations),
        "detections_sha256": file_digest(detections),
        "evaluator": "pycocotools",
        "evaluator_version": version,
        "image_ids": sorted(selected),
        "protocol": protocol.model_dump(mode="json"),
        "native_geometry_preserved": True,
        "normalization_applied": False,
    }
    return {
        "status": "PASS",
        "mode": "NATIVE_COCO_PRESERVED",
        "identity": identity,
        "identity_digest": digest(identity),
        "metrics": metrics,
        "support": {
            "images": len(selected),
            "annotations": len(audit_payload["annotations"]),
            "detections": len(filtered),
            "categories": len(known_categories),
        },
        "geometry_audit": geometry,
        "limits": [
            "Native COCO geometry is evaluated as supplied; this is not a canonical CVRS DatasetManifest.",
            "No clipping, category renumbering, or coordinate normalization is performed.",
            "Successful artifact evaluation does not certify model execution or scientific validity.",
        ],
    }
