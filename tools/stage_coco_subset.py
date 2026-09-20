"""Stage a bounded COCO 2017 validation subset from the official host.

The selection is deterministic: the first N val2017 image IDs in ascending
numeric order. This is data acquisition, not model execution or benchmark
evaluation. Existing output is never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ANNOTATION_URL = "https://images.cocodataset.org/annotations/annotations_trainval2017.zip"
IMAGE_BASE_URL = "https://images.cocodataset.org/val2017/"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, destination: Path) -> dict[str, str | None]:
    if destination.exists():
        return {"etag": None, "content_length": str(destination.stat().st_size)}
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "CVRS-RQ002-local-stager/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as handle:
        headers = {"etag": response.headers.get("ETag"), "content_length": response.headers.get("Content-Length")}
        shutil.copyfileobj(response, handle, length=1024 * 1024)
    return headers


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=128)
    parser.add_argument("--allow-official-http", action="store_true")
    args = parser.parse_args()
    if args.limit <= 0 or args.limit > 128:
        parser.error("limit must be between 1 and 128")
    if args.out.exists() and any(path.name in {"selection.json", "checksums.sha256"} for path in args.out.iterdir()):
        parser.error(f"refusing to overwrite finalized output: {args.out}")
    args.out.mkdir(parents=True, exist_ok=True)

    raw = args.out / "raw"
    raw.mkdir(exist_ok=True)
    archive = raw / "annotations_trainval2017.zip"
    annotation_url = ANNOTATION_URL
    image_base_url = IMAGE_BASE_URL
    transport = "HTTPS"
    if args.allow_official_http:
        annotation_url = annotation_url.replace("https://", "http://", 1)
        image_base_url = image_base_url.replace("https://", "http://", 1)
        transport = "OFFICIAL_HTTP_TLS_ENDPOINT_BLOCKED_SHA256_AND_ETAG_RECORDED"
    print(f"download_annotations={annotation_url}", flush=True)
    annotation_headers = download(annotation_url, archive)
    with zipfile.ZipFile(archive) as bundle:
        member = "annotations/instances_val2017.json"
        with bundle.open(member) as source, (raw / "instances_val2017.json").open("wb") as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)

    payload = json.loads((raw / "instances_val2017.json").read_text(encoding="utf-8"))
    images = sorted(payload["images"], key=lambda row: int(row["id"]))[: args.limit]
    image_ids = {int(row["id"]) for row in images}
    subset = {
        "info": payload.get("info", {}),
        "licenses": payload.get("licenses", []),
        "images": images,
        "annotations": [row for row in payload["annotations"] if int(row["image_id"]) in image_ids],
        "categories": payload["categories"],
    }
    annotations = args.out / "annotations" / "instances_val2017_subset.json"
    annotations.parent.mkdir(exist_ok=True)
    annotations.write_text(json.dumps(subset, indent=2) + "\n", encoding="utf-8")

    image_root = args.out / "images"
    image_root.mkdir(exist_ok=True)
    rows: list[dict[str, object]] = []

    def fetch(row: dict[str, object]) -> dict[str, object]:
        filename = str(row["file_name"])
        target = image_root / filename
        url = image_base_url + filename
        download(url, target)
        return {
            "image_id": int(row["id"]),
            "file_name": filename,
            "url": url,
            "bytes": target.stat().st_size,
            "sha256": sha256(target),
        }

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(fetch, row) for row in images]
        for index, future in enumerate(as_completed(futures), start=1):
            rows.append(future.result())
            if index % 16 == 0 or index == len(futures):
                print(f"images={index}/{len(futures)}", flush=True)
    rows.sort(key=lambda row: int(row["image_id"]))
    manifest = {
        "schema": "cvrs.rq002.coco-selection.v1",
        "dataset": "COCO 2017 validation",
        "split": "val2017",
        "selection_rule": "first N image IDs sorted ascending",
        "limit": args.limit,
        "source": "https://cocodataset.org/#home",
        "terms_source": "https://cocodataset.org/#termsofuse",
        "annotation_archive_url": annotation_url,
        "annotation_archive_sha256": sha256(archive),
        "annotation_archive_etag": annotation_headers.get("etag"),
        "annotation_subset_sha256": sha256(annotations),
        "images": rows,
        "rights_status": "PUBLIC_SOURCE_TERMS_RECORDED_REVIEW_REQUIRED",
        "transport": transport,
        "protected_data_access": False,
        "test_or_sealed_access": False,
    }
    manifest["selection_digest"] = hashlib.sha256(
        json.dumps(rows, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    (args.out / "selection.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    checksum_lines = [
        f"{sha256(path)}  {path.relative_to(args.out).as_posix()}"
        for path in sorted(args.out.rglob("*"))
        if path.is_file() and path.name != "checksums.sha256"
    ]
    (args.out / "checksums.sha256").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS_STAGED", "images": len(rows), "selection_digest": manifest["selection_digest"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
