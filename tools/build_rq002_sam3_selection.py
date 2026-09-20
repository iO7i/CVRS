"""Freeze detached top-score detector boxes for the bounded SAM 3 lane."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def select(path: Path, producer: str, label_key: str) -> tuple[list[dict], dict]:
    source_sha = sha256(path)
    rows = json.loads(path.read_text("utf-8"))
    prompts = []
    for row in rows:
        candidates = []
        labels = row[label_key]
        for index, (box, score, label) in enumerate(zip(row["boxes"], row["scores"], labels)):
            candidates.append((float(score), index, box, label))
        selected = sorted(candidates, key=lambda item: (-item[0], item[1]))[:8]
        for rank, (score, index, box, label) in enumerate(selected, 1):
            prompts.append({
                "prompt_id": f"{producer}-{row['sample_id']}-{rank:02d}",
                "sample_id": str(row["sample_id"]),
                "producer": producer,
                "native_detection_index": index,
                "native_score": score,
                "native_label": label,
                "box_xyxy": [float(value) for value in box],
                "source_artifact_sha256": source_sha,
            })
    return prompts, {"producer": producer, "path": path.as_posix(), "sha256": source_sha}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grounding", type=Path, required=True)
    parser.add_argument("--ultralytics", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise RuntimeError(f"refusing to overwrite {args.out}")
    grounding, grounding_source = select(args.grounding, "grounding-dino-tiny", "phrases")
    ultralytics, ultralytics_source = select(args.ultralytics, "ultralytics-yolo26n", "labels")
    payload = {
        "schema": "cvrs.rq002.sam3-detector-box-selection.v1",
        "status": "FROZEN_BEFORE_SAM3_INFERENCE",
        "policy": "top_8_by_native_score_per_producer_per_image_stable_native_index_tiebreak",
        "geometry": "raw_xyxy_pixels_preserved_no_clipping_no_rewrite",
        "source_artifacts": [grounding_source, ultralytics_source],
        "prompts": grounding + ultralytics,
        "counts": {
            "grounding-dino-tiny": len(grounding),
            "ultralytics-yolo26n": len(ultralytics),
            "total": len(grounding) + len(ultralytics),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", "utf-8")
    print(json.dumps({"output": str(args.out), "sha256": sha256(args.out), "counts": payload["counts"]}))


if __name__ == "__main__":
    main()
