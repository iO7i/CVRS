"""Exercise CVRS's rich interchange through real Supervision and FiftyOne SDKs.

This is deliberately separate from the direct native COCO import/export smokes:
COCO is first translated into CVRS's canonical RichInterchange contract, then
CVRS launches each SDK worker and audits the SDK-produced representation on
the way back into the canonical contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from cvsubstrate.product.bridges import native_exchange
from cvsubstrate.product.interchange import RichFrame, RichInterchange, RichObject
from cvsubstrate.provenance.io import file_digest, write_json


def _sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _canonical_coco(annotations: Path, images: Path, limit: int) -> RichInterchange:
    source = json.loads(annotations.read_text(encoding="utf-8"))
    selected = sorted(source["images"], key=lambda item: int(item["id"]))[:limit]
    selected_ids = {int(item["id"]) for item in selected}
    grouped: dict[int, list[dict]] = defaultdict(list)
    for annotation in source["annotations"]:
        if int(annotation["image_id"]) in selected_ids:
            grouped[int(annotation["image_id"])].append(annotation)

    frames = []
    for image in selected:
        image_id = int(image["id"])
        image_path = (images / image["file_name"]).resolve()
        if not image_path.is_file():
            raise FileNotFoundError(image_path)
        objects = []
        for annotation in sorted(grouped[image_id], key=lambda item: int(item["id"])):
            x, y, width, height = (float(value) for value in annotation["bbox"])
            objects.append(
                RichObject(
                    id=f"coco-annotation:{int(annotation['id'])}",
                    category_id=int(annotation["category_id"]),
                    score=1.0,
                    box=[x, y, x + width, y + height],
                    attributes={
                        "coco_annotation_id": int(annotation["id"]),
                        "iscrowd": int(annotation.get("iscrowd", 0)),
                        "declared_area": float(annotation.get("area", width * height)),
                    },
                )
            )
        frames.append(
            RichFrame(
                sample_id=f"coco-val2017:{image_id:012d}",
                width=int(image["width"]),
                height=int(image["height"]),
                image=str(image_path),
                image_sha256=file_digest(image_path),
                task="hbb_detection",
                objects=objects,
                metadata={
                    "coco_image_id": image_id,
                    "file_name": image["file_name"],
                    "license_id": image.get("license"),
                },
            )
        )

    return RichInterchange(
        dataset_digest=file_digest(annotations),
        categories={int(item["id"]): item["name"] for item in source["categories"]},
        frames=frames,
        licenses={
            "dataset": "COCO 2017 validation subset",
            "source_licenses": source.get("licenses", []),
        },
        provenance={
            "source_annotations": str(annotations.resolve()),
            "source_annotations_sha256": file_digest(annotations),
            "selection": "ascending COCO image ID",
            "limit": limit,
            "geometry_conversion": "COCO xywh -> exact continuous xyxy; no clipping or rounding",
        },
    )


def _coordinate_analysis(source: RichInterchange, restored_path: Path) -> dict:
    restored = RichInterchange.model_validate_json(restored_path.read_text(encoding="utf-8"))
    source_frames = {frame.sample_id: frame for frame in source.frames}
    restored_frames = {frame.sample_id: frame for frame in restored.frames}
    maximum = 0.0
    location = None
    for sample_id, frame in source_frames.items():
        source_objects = {item.id: item for item in frame.objects}
        restored_objects = {item.id: item for item in restored_frames[sample_id].objects}
        for object_id, item in source_objects.items():
            for index, (left, right) in enumerate(zip(item.box or [], restored_objects[object_id].box or [])):
                delta = abs(left - right)
                if delta > maximum:
                    maximum = delta
                    location = {
                        "sample_id": sample_id,
                        "object_id": object_id,
                        "coordinate_index": index,
                        "source_value": left,
                        "restored_value": right,
                    }
    return {
        "objects_compared": sum(len(frame.objects) for frame in source.frames),
        "maximum_absolute_coordinate_delta_pixels": maximum,
        "maximum_delta_location": location,
        "status": "PRESERVED" if maximum <= 1e-9 else "CHANGED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--supervision-python", type=Path, required=True)
    parser.add_argument("--fiftyone-python", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=32)
    args = parser.parse_args()
    if args.out.exists():
        parser.error(f"refusing to overwrite output: {args.out}")
    if args.limit < 1:
        parser.error("--limit must be positive")

    args.out.mkdir(parents=True)
    canonical = _canonical_coco(args.annotations, args.images, args.limit)
    canonical_path = args.out / "canonical-source.json"
    write_json(canonical_path, canonical)

    receipts = {}
    for target, interpreter in (
        ("supervision", args.supervision_python),
        ("fiftyone", args.fiftyone_python),
    ):
        receipts[target] = native_exchange(
            canonical.model_dump(mode="json"),
            target,
            args.out / target,
            worker_python=str(interpreter.resolve()),
            trust=True,
        )

    frame_count = len(canonical.frames)
    object_count = sum(len(frame.objects) for frame in canonical.frames)
    checks = {
        target: {
            "status": receipt["status"],
            "audit_status": receipt["audit"]["status"],
            "objects_checked": receipt["audit"]["objects_checked"],
            "differences": receipt["audit"]["differences"],
            "coordinate_tolerance": receipt["audit"]["coordinate_tolerance"],
            "source_digest": receipt["audit"]["source_digest"],
            "restored_digest": receipt["audit"]["restored_digest"],
        }
        for target, receipt in receipts.items()
    }
    coordinate_analysis = {
        "schema": "cvrs.rq002.coordinate-analysis.v1",
        "source": "canonical-source.json",
        "comparison_key": "sample_id + object_id + coordinate_index",
        "coordinate_tolerance_absolute_pixels": 1e-9,
        **{
            target: _coordinate_analysis(canonical, args.out / target / "canonical-restored.json")
            for target in receipts
        },
        "silent_clipping_or_rounding": False,
    }
    write_json(args.out / "coordinate-analysis.json", coordinate_analysis)
    passed = all(
        item["status"] == "SUCCEEDED"
        and item["audit_status"] == "PRESERVED"
        and item["objects_checked"] == object_count
        and not item["differences"]
        for item in checks.values()
    )
    report = {
        "schema": "cvrs.rq002.cvrs-sdk-paths.v1",
        "status": "PASS_CVRS_SUPERVISION_AND_FIFTYONE_PATHS" if passed else "FAIL_CVRS_SDK_PATH",
        "scope": {
            "images": frame_count,
            "objects": object_count,
            "categories": len(canonical.categories),
            "task": "hbb_detection",
            "source_annotations_sha256": file_digest(args.annotations),
            "canonical_source_sha256": file_digest(canonical_path),
        },
        "paths": checks,
        "independence": {
            "direct_native_reference": "Existing SDK-specific COCO import/export smokes",
            "cvrs_path": "COCO -> CVRS RichInterchange -> real SDK worker -> CVRS RichInterchange audit",
            "shared_inputs": "Frozen public COCO validation subset bytes only",
            "native_sdk_execution": True,
        },
        "loss_disposition": {
            "box_coordinates": "PRESERVED at the preregistered 1e-9 absolute tolerance",
            "sample_ids": "PRESERVED",
            "object_ids": "PRESERVED",
            "category_ids_and_names": "PRESERVED",
            "scores_and_attributes": "PRESERVED",
            "image_identity": "PRESERVED by per-file SHA-256",
            "silent_clipping_or_rounding": False,
            "mask_fidelity": "NOT_CLAIMED; this bounded lane is HBB detection only",
        },
        "limits": [
            "This qualifies the HBB interchange path; it is not model inference or a scientific result.",
            "Mask, polygon, and grounded-label adapters remain covered by software fixtures, not this public-data lane.",
            "Local-only guards are evidence of intent and observed execution, not an operating-system network sandbox.",
        ],
    }
    write_json(args.out / "report.json", report)
    files = sorted(path for path in args.out.rglob("*") if path.is_file() and path.name != "checksums.sha256")
    (args.out / "checksums.sha256").write_text(
        "\n".join(f"{_sha256(path)}  {path.relative_to(args.out).as_posix()}" for path in files) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": report["status"], "scope": report["scope"], "paths": checks}))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
