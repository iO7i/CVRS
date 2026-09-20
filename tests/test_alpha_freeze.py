import json
from pathlib import Path

import pytest

from cvsubstrate.contracts.models import Box, DetectionPrediction, EvaluationProtocol
from cvsubstrate.data.coco import import_coco
from cvsubstrate.evaluation.native_coco import audit_coco_geometry, evaluate_native_coco
from cvsubstrate.provenance.io import read_json


def native_coco_fixture(tmp_path: Path) -> tuple[Path, Path]:
    annotations = {
        "info": {"description": "native geometry fixture"},
        "licenses": [],
        "images": [{"id": 1, "file_name": "x.png", "width": 10, "height": 10}],
        "categories": [{"id": 1, "name": "object"}],
        "annotations": [
            {"id": 1, "image_id": 1, "category_id": 1, "bbox": [-2.0, 2.0, 4.0, 4.0], "area": 16.0, "iscrowd": 0}
        ],
    }
    detections = [{"image_id": 1, "category_id": 1, "bbox": [-2.0, 2.0, 4.0, 4.0], "score": 0.99}]
    ann = tmp_path / "annotations.json"
    det = tmp_path / "detections.json"
    ann.write_text(json.dumps(annotations), encoding="utf-8")
    det.write_text(json.dumps(detections), encoding="utf-8")
    return ann, det


def test_canonical_geometry_remains_strict(tmp_path):
    with pytest.raises(ValueError, match="nonnegative origin"):
        Box(xyxy=[-2.0, 2.0, 2.0, 6.0], category_id=1)
    with pytest.raises(ValueError):
        DetectionPrediction(
            sample_id="x", width=10, height=10,
            boxes=[[-2.0, 2.0, 2.0, 6.0]], scores=[0.9], category_ids=[1],
        )
    ann, _ = native_coco_fixture(tmp_path)
    with pytest.raises(ValueError):
        import_coco(ann, tmp_path, "strict-fixture")


def test_native_geometry_audit_does_not_normalize(tmp_path):
    ann, _ = native_coco_fixture(tmp_path)
    payload = json.loads(ann.read_text(encoding="utf-8"))
    result = audit_coco_geometry(payload)
    assert result["counts"]["x1<0"] == 1
    assert result["has_noncanonical_geometry"] is True
    assert result["examples"][0]["bbox"] == [-2.0, 2.0, 4.0, 4.0]
    assert json.loads(ann.read_text(encoding="utf-8")) == payload


@pytest.mark.coco
def test_native_coco_evaluates_preserved_oob_geometry(tmp_path):
    pytest.importorskip("pycocotools")
    ann, det = native_coco_fixture(tmp_path)
    result = evaluate_native_coco(ann, det)
    assert result["status"] == "PASS"
    assert result["mode"] == "NATIVE_COCO_PRESERVED"
    assert result["geometry_audit"]["counts"]["x1<0"] == 1
    assert result["identity"]["native_geometry_preserved"] is True
    assert result["identity"]["normalization_applied"] is False
    assert result["metrics"]["AP/all/maxDets=100"] == pytest.approx(1.0)


@pytest.mark.coco
def test_native_coco_identity_binds_artifacts(tmp_path):
    pytest.importorskip("pycocotools")
    ann, det = native_coco_fixture(tmp_path)
    first = evaluate_native_coco(ann, det)
    rows = json.loads(det.read_text(encoding="utf-8"))
    rows[0]["score"] = 0.75
    det.write_text(json.dumps(rows), encoding="utf-8")
    second = evaluate_native_coco(ann, det)
    assert first["identity"]["annotations_sha256"] == second["identity"]["annotations_sha256"]
    assert first["identity"]["detections_sha256"] != second["identity"]["detections_sha256"]
    assert first["identity_digest"] != second["identity_digest"]


@pytest.mark.coco
def test_native_coco_cli_roundtrip(tmp_path, capsys):
    pytest.importorskip("pycocotools")
    from cvsubstrate.cli import main

    ann, det = native_coco_fixture(tmp_path)
    out = tmp_path / "result.json"
    assert main(["native-coco-evaluate", str(ann), str(det), "--out", str(out)]) == 0
    result = read_json(out)
    assert result["mode"] == "NATIVE_COCO_PRESERVED"
    assert result["support"]["images"] == 1
    assert main(["native-coco-evaluate", str(ann), str(det), "--out", str(out)]) == 2
    assert "OUTPUT_EXISTS" in capsys.readouterr().err


def test_native_coco_rejects_non_coco_protocol(tmp_path):
    ann, det = native_coco_fixture(tmp_path)
    protocol = EvaluationProtocol(evaluator="diagnostic_detection", evaluator_version="1", iou_thresholds=[0.5])
    with pytest.raises(Exception, match="pycocotools"):
        evaluate_native_coco(ann, det, protocol=protocol)


def test_rq002_plan_and_reference_001_guard(tmp_path, monkeypatch):
    import importlib.util

    spec = importlib.util.spec_from_file_location("rq002_tool", Path(__file__).parents[1] / "tools" / "rq002.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    plan = module.read_json(module.PLAN)
    result = module.validate_plan(plan)
    assert result == {"status": "VALID", "lanes": 13, "gates": 25}
    changed = dict(plan)
    changed["reference_001_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="Reference Qualification 001"):
        module.validate_plan(changed)


def test_rq002_receipt_cannot_self_certify(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("rq002_tool_receipt", Path(__file__).parents[1] / "tools" / "rq002.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    with pytest.raises(ValueError, match="native and CVRS"):
        module.validate_lane_receipt({"lane_id": "OML-MODERN", "status": "PASS"})
    receipt = {
        "lane_id": "OML-MODERN", "status": "PASS", "mock_output": False,
        "source": {"revision": "abc123"},
        "native_reference": {"executed": True}, "cvrs_path": {"executed": True},
        "artifacts": {"manifest_sha256": "a" * 64},
    }
    assert module.validate_lane_receipt(receipt)["lane_status"] == "PASS"
