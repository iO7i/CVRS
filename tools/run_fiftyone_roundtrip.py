"""Run a bounded native FiftyOne COCO import/export roundtrip."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import fiftyone as fo


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=32)
    args = parser.parse_args()
    if args.out.exists():
        parser.error(f"refusing to overwrite output: {args.out}")
    args.out.mkdir(parents=True)
    source = json.loads(args.annotations.read_text(encoding="utf-8"))
    selected_ids = {item["id"] for item in sorted(source["images"], key=lambda item: item["id"])[: args.limit]}
    selected = {
        "images": [item for item in source["images"] if item["id"] in selected_ids],
        "annotations": [item for item in source["annotations"] if item["image_id"] in selected_ids],
        "categories": source["categories"],
    }
    source_subset = args.out / "source_subset.json"
    source_subset.write_text(json.dumps(selected, indent=2) + "\n", encoding="utf-8")
    dataset = fo.Dataset.from_dir(
        dataset_dir=str(args.out / "database"),
        dataset_type=fo.types.COCODetectionDataset,
        data_path=str(args.images.resolve()),
        labels_path=str(source_subset.resolve()),
        label_field="ground_truth",
        name="cvrs_rq002_fiftyone_roundtrip",
        persistent=False,
    )
    detection_field = "ground_truth_detections"
    segmentation_field = "ground_truth_segmentations"
    exported_dir = args.out / "export"
    dataset.export(
        export_dir=str(exported_dir),
        dataset_type=fo.types.COCODetectionDataset,
        label_field=detection_field,
        export_media=False,
        overwrite=True,
    )
    exported_annotations = exported_dir / "labels.json"
    exported = json.loads(exported_annotations.read_text(encoding="utf-8"))
    imported_detection_count = sum(len(sample[detection_field].detections) for sample in dataset)
    source_category_names = {item["id"]: item["name"] for item in selected["categories"]}
    source_used_category_names = {source_category_names[item["category_id"]] for item in selected["annotations"]}
    exported_category_names = {item["id"]: item["name"] for item in exported.get("categories", [])}
    exported_used_category_names = {
        exported_category_names[item["category_id"]] for item in exported.get("annotations", [])
    }
    report = {
        "schema": "cvrs.rq002.fiftyone-roundtrip.v1",
        "status": "PASS_NATIVE_SDK_ROUNDTRIP_SMOKE",
        "sdk": "fiftyone",
        "sdk_version": fo.__version__,
        "source_annotations_sha256": sha256(args.annotations),
        "source_subset_sha256": sha256(source_subset),
        "exported_annotations_sha256": sha256(exported_annotations),
        "source": {
            "images": len(selected["images"]),
            "annotations": len(selected["annotations"]),
            "categories": len(selected["categories"]),
        },
        "imported": {"samples": len(dataset), "detections": imported_detection_count},
        "imported_fields": {
            "detection_field": detection_field,
            "segmentation_field": segmentation_field,
            "segmentation_field_present": segmentation_field in dataset.get_field_schema(),
        },
        "exported": {
            "images": len(exported.get("images", [])),
            "annotations": len(exported.get("annotations", [])),
            "categories": len(exported.get("categories", [])),
        },
        "loss_report": {
            "image_count_equal": len(selected["images"]) == len(exported.get("images", [])),
            "annotation_count_equal": len(selected["annotations"]) == len(exported.get("annotations", [])),
            "category_count_equal": len(selected["categories"]) == len(exported.get("categories", [])),
            "used_category_name_set_equal": source_used_category_names == exported_used_category_names,
            "unused_category_definitions_omitted": len(selected["categories"]) != len(exported.get("categories", [])),
            "source_coordinate_frame": "COCO_xywh_original_image",
            "export_coordinate_frame": "COCO_xywh_roundtrip",
            "silent_normalization_claimed": False,
        },
        "limits": [
            "This is a native SDK roundtrip smoke on a bounded public COCO subset, not a model result.",
            "The FiftyOne database is ephemeral; the exported COCO artifact and hashes are authoritative.",
            "This smoke exports the detection field; segmentation import presence is recorded but mask fidelity is not claimed.",
            "The staged COCO transport limitation is recorded in the input selection manifest.",
        ],
    }
    checks = (
        report["loss_report"]["image_count_equal"],
        report["loss_report"]["annotation_count_equal"],
        report["loss_report"]["used_category_name_set_equal"],
    )
    report["status"] = "PASS_NATIVE_SDK_ROUNDTRIP_SMOKE" if all(checks) else "FAIL_FIDELITY"
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    files = sorted(path for path in args.out.rglob("*") if path.is_file() and path.name != "checksums.sha256")
    (args.out / "checksums.sha256").write_text(
        "\n".join(f"{sha256(path)}  {path.relative_to(args.out).as_posix()}" for path in files) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": report["status"], "imported": report["imported"], "exported": report["exported"]}))
    return 0 if report["status"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
