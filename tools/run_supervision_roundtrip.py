"""Run a bounded native Supervision COCO roundtrip on the staged public subset."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import supervision as sv


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error(f"refusing to overwrite output: {args.out}")
    args.out.mkdir(parents=True)
    image_out = args.out / "images"
    annotation_out = args.out / "annotations.json"
    dataset = sv.DetectionDataset.from_coco(
        images_directory_path=str(args.images),
        annotations_path=str(args.annotations),
        show_progress=False,
    )
    exported_image_count, exported_annotation_count = dataset.as_coco(
        images_directory_path=str(image_out),
        annotations_path=str(annotation_out),
        show_progress=False,
    )
    source = json.loads(args.annotations.read_text(encoding="utf-8"))
    exported = json.loads(annotation_out.read_text(encoding="utf-8"))
    source_image_count = len(source.get("images", []))
    source_annotation_count = len(source.get("annotations", []))
    source_category_count = len(source.get("categories", []))
    exported_category_count = len(exported.get("categories", []))
    report = {
        "schema": "cvrs.rq002.supervision-roundtrip.v1",
        "status": "PASS_NATIVE_SDK_ROUNDTRIP_SMOKE",
        "sdk": "supervision",
        "sdk_version": sv.__version__,
        "source_annotations_sha256": sha256(args.annotations),
        "exported_annotations_sha256": sha256(annotation_out),
        "source": {"images": source_image_count, "annotations": source_annotation_count, "categories": source_category_count},
        "exported": {"images": len(exported.get("images", [])), "annotations": len(exported.get("annotations", [])), "categories": exported_category_count},
        "sdk_returned": {"image_id": exported_image_count, "annotation_id": exported_annotation_count},
        "loss_report": {
            "image_count_equal": source_image_count == len(exported.get("images", [])),
            "annotation_count_equal": source_annotation_count == len(exported.get("annotations", [])),
            "category_count_equal": source_category_count == exported_category_count,
            "source_coordinate_frame": "COCO_xywh_original_image",
            "export_coordinate_frame": "COCO_xywh_roundtrip",
            "silent_normalization_claimed": False,
        },
        "limits": [
            "This is a native SDK roundtrip smoke on public COCO bytes, not a model result.",
            "A full RQ002 lane also needs independent CVRS-path evidence and a reviewed loss disposition.",
            "The staged COCO transport limitation is recorded in the input selection manifest.",
        ],
    }
    structural_checks = (
        report["loss_report"]["image_count_equal"],
        report["loss_report"]["annotation_count_equal"],
        report["loss_report"]["category_count_equal"],
    )
    report["status"] = "PASS_NATIVE_SDK_ROUNDTRIP_SMOKE" if all(structural_checks) else "FAIL_FIDELITY"
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (args.out / "checksums.sha256").write_text(
        "\n".join(
            f"{sha256(path)}  {path.relative_to(args.out).as_posix()}"
            for path in sorted(args.out.rglob("*"))
            if path.is_file() and path.name != "checksums.sha256"
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": report["status"], "loss_report": report["loss_report"]}))
    return 0 if report["status"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
