"""Bounded MMDetection 2.28.2 / RetinaNet RQ002 qualification on Modal."""
from __future__ import annotations

import json
from pathlib import Path

import modal


REVISION = "e9cae2d0787cd5c2fc6165a6061f92fa09e48fb1"
SOURCE_URL = f"https://codeload.github.com/open-mmlab/mmdetection/tar.gz/{REVISION}"
LICENSE_URL = f"https://raw.githubusercontent.com/open-mmlab/mmdetection/{REVISION}/LICENSE"
CONFIG_RELATIVE = "configs/retinanet/retinanet_r50_fpn_1x_coco.py"
CHECKPOINT_URL = (
    "https://download.openmmlab.com/mmdetection/v2.0/retinanet/"
    "retinanet_r50_fpn_1x_coco/retinanet_r50_fpn_1x_coco_20200130-c2398f9e.pth"
)
IMAGES = [
    {"id": "139", "file_name": "000000000139.jpg", "url": "http://images.cocodataset.org/val2017/000000000139.jpg", "sha256": "ffe0f0cec3b2e27aab1967229cdf0a0d7751dcdd5800322f0b8ac0dffb3b8a8d"},
    {"id": "285", "file_name": "000000000285.jpg", "url": "http://images.cocodataset.org/val2017/000000000285.jpg", "sha256": "f3a2974ce3686332609124c70e3e6a2e3aca43fccf1cd1bd7c5c03820977f57d"},
]

app = modal.App("cvrs-rq002-mmdet2-retinanet")
probe_image = modal.Image.debian_slim(python_version="3.10")
runtime_image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("libgl1", "libglib2.0-0")
    .pip_install("torch==1.13.1", "torchvision==0.14.1", index_url="https://download.pytorch.org/whl/cu117")
    .pip_install("mmcv-full==1.7.1", find_links="https://download.openmmlab.com/mmcv/dist/cu117/torch1.13/index.html")
    .pip_install("mmdet==2.28.2", "numpy==1.23.5", "opencv-python==4.8.1.78", "pydantic==2.11.9", "Pillow==9.5.0", "yapf==0.40.1")
    .add_local_dir("src/cvsubstrate", "/root/cvrs-src/cvsubstrate", copy=True)
    .add_local_file("qualification/inputs/coco2017-val-128-official-http/annotations/instances_val2017_subset.json", "/root/inputs/instances_val2017_subset.json", copy=True)
    .env({"PYTHONPATH": "/root/cvrs-src"})
)


def _download(url: str, destination: Path, maximum: int) -> dict:
    import hashlib
    import urllib.request

    digest = hashlib.sha256()
    total = 0
    request = urllib.request.Request(url, headers={"User-Agent": "CVRS-RQ002/1.0"})
    with urllib.request.urlopen(request, timeout=180) as response, destination.open("wb") as handle:
        for block in iter(lambda: response.read(1024 * 1024), b""):
            total += len(block)
            if total > maximum:
                raise RuntimeError("DOWNLOAD_BYTE_BUDGET_EXCEEDED")
            digest.update(block)
            handle.write(block)
    return {"sha256": digest.hexdigest(), "bytes": total}


def _extract(archive: Path, destination: Path) -> Path:
    import tarfile

    destination.mkdir()
    root = destination.resolve()
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.getmembers():
            target = (destination / member.name).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError("SOURCE_ARCHIVE_PATH_ESCAPE")
        bundle.extractall(destination)
    roots = [path for path in destination.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise RuntimeError("SOURCE_ARCHIVE_ROOT_AMBIGUOUS")
    return roots[0]


@app.function(image=probe_image, cpu=2.0, memory=2048, timeout=900, retries=0)
def probe() -> dict:
    import hashlib
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        archive = root / "source.tar.gz"
        source = _download(SOURCE_URL, archive, 100 * 1024 * 1024)
        source_root = _extract(archive, root / "source")
        config = source_root / CONFIG_RELATIVE
        checkpoint = _download(CHECKPOINT_URL, root / "checkpoint.pth", 250 * 1024 * 1024)
        license_identity = _download(LICENSE_URL, root / "LICENSE", 128 * 1024)
        images = []
        for item in IMAGES:
            identity = _download(item["url"], root / item["file_name"], 2 * 1024 * 1024)
            if identity["sha256"] != item["sha256"]:
                raise RuntimeError("IMAGE_SHA256_MISMATCH:" + item["id"])
            images.append({**item, **identity})
        return {
            "schema": "cvrs.rq002.mmdet2-retinanet-probe.v1",
            "status": "ASSETS_OBSERVED_NOT_INFERRED",
            "source": {"version": "2.28.2", "revision": REVISION, "url": SOURCE_URL, **source},
            "config": {"relative_path": CONFIG_RELATIVE, "sha256": hashlib.sha256(config.read_bytes()).hexdigest()},
            "checkpoint": {"url": CHECKPOINT_URL, **checkpoint},
            "license": {"identifier": "Apache-2.0", "url": LICENSE_URL, **license_identity},
            "images": images,
            "controls": {"inference": False, "training": False, "gpu": False, "protected_data_access": 0},
        }


def _bounds(rows: list[dict], sizes: dict[str, tuple[int, int]]) -> dict:
    import math

    total = finite = ordered = out = 0
    reasons = {"x1<0": 0, "y1<0": 0, "x2>width": 0, "y2>height": 0}
    maxima = {"left": 0.0, "top": 0.0, "right": 0.0, "bottom": 0.0}
    by_image = []
    for row in rows:
        width, height = sizes[row["sample_id"]]
        image_out = 0
        for per_class in row["result"]:
            for value in per_class:
                total += 1
                x1, y1, x2, y2 = map(float, value[:4])
                is_finite = all(math.isfinite(v) for v in (x1, y1, x2, y2, float(value[4])))
                finite += int(is_finite)
                is_ordered = x2 >= x1 and y2 >= y1
                ordered += int(is_ordered)
                flags = [x1 < 0, y1 < 0, x2 > width, y2 > height]
                if any(flags):
                    out += 1
                    image_out += 1
                for key, flag in zip(reasons, flags):
                    reasons[key] += int(flag)
                maxima["left"] = max(maxima["left"], max(0.0, -x1))
                maxima["top"] = max(maxima["top"], max(0.0, -y1))
                maxima["right"] = max(maxima["right"], max(0.0, x2 - width))
                maxima["bottom"] = max(maxima["bottom"], max(0.0, y2 - height))
        by_image.append({"sample_id": row["sample_id"], "detections": sum(len(v) for v in row["result"]), "out_of_bounds": image_out})
    return {"detections": total, "finite": finite, "ordered": ordered, "out_of_bounds": out, "out_of_bounds_fraction": out / total if total else 0.0, "reason_counts": reasons, "maximum_excess_pixels": maxima, "by_image": by_image}


@app.function(image=runtime_image, gpu="T4", cpu=2.0, memory=8192, timeout=1200, retries=0)
def qualify(lock: dict, saved_native_text: str = "") -> bytes:
    import hashlib
    import importlib.metadata
    import io
    import subprocess
    import sys
    import tempfile
    import time
    import zipfile

    import mmcv
    import mmdet
    import numpy as np
    import torch
    from PIL import Image
    from mmdet.apis import inference_detector, init_detector

    from cvsubstrate.heritage.importer import import_predictions

    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        archive = root / "source.tar.gz"
        if _download(SOURCE_URL, archive, 100 * 1024 * 1024)["sha256"] != lock["source_sha256"]:
            raise RuntimeError("SOURCE_SHA256_MISMATCH")
        source_root = _extract(archive, root / "source")
        config = source_root / CONFIG_RELATIVE
        if digest(config) != lock["config_sha256"]:
            raise RuntimeError("CONFIG_SHA256_MISMATCH")
        checkpoint = root / "checkpoint.pth"
        if _download(CHECKPOINT_URL, checkpoint, 250 * 1024 * 1024)["sha256"] != lock["checkpoint_sha256"]:
            raise RuntimeError("CHECKPOINT_SHA256_MISMATCH")
        image_root = root / "images"
        image_root.mkdir()
        metadata = []
        for item in IMAGES:
            path = image_root / item["file_name"]
            identity = _download(item["url"], path, 2 * 1024 * 1024)
            if identity["sha256"] != item["sha256"]:
                raise RuntimeError("IMAGE_SHA256_MISMATCH:" + item["id"])
            with Image.open(path) as image:
                width, height = image.size
            metadata.append({**item, "width": width, "height": height})

        annotations = json.loads(Path("/root/inputs/instances_val2017_subset.json").read_text("utf-8"))
        categories = annotations["categories"]
        category_map = {str(i): item["id"] for i, item in enumerate(categories)}
        manifest = {
            "schema_version": "1.0", "name": "rq002-coco-two-image-smoke", "version": "2017", "purpose": "research_dataset",
            "categories": [{"id": item["id"], "name": item["name"]} for item in categories],
            "samples": [{"id": item["id"], "image": "images/" + item["file_name"], "sha256": item["sha256"], "width": item["width"], "height": item["height"], "source_kind": "real"} for item in metadata],
            "splits": {"dev": {"role": "dev", "sample_ids": [item["id"] for item in metadata]}},
            "licenses": {"data": "COCO source-image license varies; parent terms recorded", "annotations": "CC BY 4.0", "code": "N/A", "redistribution": "unknown"},
        }
        manifest_path = root / "dataset.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", "utf-8")

        native_rows = []
        native_source = "REUSED_SAVED_NATIVE_ARTIFACT" if saved_native_text else "DIRECT_INFERENCE_THIS_RUN"
        if saved_native_text:
            native_rows = [json.loads(line) for line in saved_native_text.splitlines() if line.strip()]
        else:
            model = init_detector(str(config), str(checkpoint), device="cuda:0")
            for item in metadata:
                result = inference_detector(model, str(image_root / item["file_name"]))
                bbox_result = result[0] if isinstance(result, tuple) else result
                native_rows.append({"sample_id": item["id"], "result": [np.asarray(per_class).tolist() for per_class in bbox_result]})
        native_path = root / "native-direct.jsonl"
        native_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in native_rows), "utf-8")
        sizes = {item["id"]: (item["width"], item["height"]) for item in metadata}
        bounds = _bounds(native_rows, sizes)

        conversion_status, conversion_report, conversion_error = "PASS", None, None
        try:
            conversion_report = import_predictions(native_path, manifest_path, "dev", category_map, root / "converted-native", native_format="mmdet2_bbox")
        except Exception as exc:
            conversion_status = "FAIL"
            conversion_error = f"{type(exc).__name__}: {exc}"

        request = {
            "schema_version": "1.0", "protocol_version": "1.0", "operation": "predict",
            "experiment": {"adapter": {"name": "mmdetection", "config": {"config_path": str(config), "config_sha256": digest(config), "trust_executable_config": True, "category_map": category_map, "upstream": "open-mmlab/mmdetection", "revision": REVISION, "profile": "mmdet2", "device": "cuda:0"}}, "eval_split": "dev"},
            "manifest": manifest,
            "checkpoint": {"path": str(checkpoint), "sha256": digest(checkpoint), "trust": "trusted_legacy_pickle"},
            "output_dir": str(root / "wrapped-execution"), "data_root": str(root),
        }
        request_path, response_path = root / "worker-request.json", root / "worker-response.json"
        request_path.write_text(json.dumps(request, indent=2) + "\n", "utf-8")
        subprocess.run([sys.executable, "/root/cvrs-src/cvsubstrate/worker_shims/mmdetection_worker.py", "--request", str(request_path), "--response", str(response_path)], check=True)
        response = json.loads(response_path.read_text("utf-8"))
        wrapped_rows = [json.loads(line) for line in (root / "wrapped-execution/upstream_predictions.jsonl").read_text("utf-8").splitlines()] if (root / "wrapped-execution/upstream_predictions.jsonl").is_file() else []

        flattened = []
        for row in native_rows:
            boxes, scores, labels = [], [], []
            for label, per_class in enumerate(row["result"]):
                for value in per_class:
                    boxes.append(value[:4]); scores.append(value[4]); labels.append(label)
            flattened.append({"sample_id": row["sample_id"], "boxes": boxes, "scores": scores, "labels": labels})
        repeatability = []
        for direct, wrapped in zip(flattened, wrapped_rows):
            repeatability.append({
                "sample_id": direct["sample_id"],
                "labels_and_order_exact": direct["labels"] == wrapped["zero_based_labels"],
                "boxes_atol_1e_6": bool(np.allclose(direct["boxes"], wrapped["boxes"], rtol=0.0, atol=1e-6)),
                "scores_atol_1e_7": bool(np.allclose(direct["scores"], wrapped["scores"], rtol=0.0, atol=1e-7)),
            })
        repeatability_pass = len(repeatability) == len(native_rows) and all(all(v for k, v in row.items() if k != "sample_id") for row in repeatability)
        wrapped_pass = response["status"] == "SUCCEEDED"
        passed = conversion_status == "PASS" and wrapped_pass and repeatability_pass
        report = {
            "schema": "cvrs.rq002.mmdet2-retinanet.v1",
            "status": "PASS_MMDET2_RETINANET_NATIVE_AND_CVRS" if passed else "FAIL_MMDET2_RETINANET_NATIVE_AND_CVRS",
            "assets": lock, "images": metadata,
            "native": {"images": len(native_rows), "detections": bounds["detections"], "sha256": digest(native_path), "source": native_source, "geometry_audit": bounds},
            "saved_native_conversion": {"status": conversion_status, "report": conversion_report, "error": conversion_error},
            "wrapped_execution": {"response": response, "repeatability": repeatability, "repeatability_pass": repeatability_pass},
            "environment": {"python": sys.version, "torch": torch.__version__, "cuda_runtime": torch.version.cuda, "cuda_device": torch.cuda.get_device_name(0), "mmdet": mmdet.__version__, "mmcv": mmcv.__version__, "numpy": np.__version__, "torchvision": importlib.metadata.version("torchvision")},
            "criteria": {"box_atol": 1e-6, "score_atol": 1e-7, "labels_and_order": "exact"},
            "separate_statuses": {"native_inference": "REUSED_PRIOR_PASS" if saved_native_text else "PASS", "transport_fidelity": "PASS" if repeatability_pass else "FAIL", "conversion_fidelity": conversion_status, "runtime_repeatability": "PASS" if repeatability_pass else "FAIL", "evaluator_equivalence": "NOT_RUN_NOT_REQUIRED_FOR_INTEROPERABILITY_SMOKE"},
            "controls": {"training": False, "optimizer_steps": 0, "checkpoint_writes": 0, "protected_data_access": 0, "sealed_test_access": 0, "gpu_concurrency": 1, "geometry_modification": "NONE"},
            "runtime_seconds": time.perf_counter() - started,
            "limits": ["Two-image interoperability smoke only; no accuracy claim.", "Every native detection is preserved; no clipping, filtering, or normalization."],
        }
        (root / "report.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
        checksums = []
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(root)
            if path.is_file() and path.name not in {"checkpoint.pth", "source.tar.gz"} and "source" not in rel.parts and "images" not in rel.parts:
                checksums.append(f"{digest(path)}  {rel.as_posix()}")
        (root / "checksums.sha256").write_text("\n".join(checksums) + "\n", "utf-8")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(root.rglob("*")):
                rel = path.relative_to(root)
                if path.is_file() and path.name not in {"checkpoint.pth", "source.tar.gz"} and "source" not in rel.parts and "images" not in rel.parts:
                    bundle.write(path, rel.as_posix())
        return buffer.getvalue()


@app.local_entrypoint()
def main(mode: str, out: str, lock_json: str = "", native_jsonl: str = "") -> None:
    destination = Path(out)
    if destination.exists():
        raise RuntimeError(f"refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if mode == "probe":
        destination.write_text(json.dumps(probe.remote(), indent=2) + "\n", "utf-8")
    elif mode == "qualify":
        destination.write_bytes(qualify.remote(json.loads(Path(lock_json).read_text("utf-8"))))
    elif mode == "wrapped-from-saved":
        destination.write_bytes(qualify.remote(json.loads(Path(lock_json).read_text("utf-8")), Path(native_jsonl).read_text("utf-8")))
    else:
        raise ValueError("mode must be probe, qualify, or wrapped-from-saved")
    print(json.dumps({"mode": mode, "output": str(destination), "bytes": destination.stat().st_size}))
