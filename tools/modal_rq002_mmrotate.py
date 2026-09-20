"""Bounded MMRotate 0.3.4 / Oriented R-CNN RQ002 qualification on Modal."""
from __future__ import annotations

import json
from pathlib import Path

import modal


REVISION = "7755aa53b6e2d9c61fd765e67a60daa7ed8a1e05"
SOURCE_URL = f"https://codeload.github.com/open-mmlab/mmrotate/tar.gz/{REVISION}"
LICENSE_URL = f"https://raw.githubusercontent.com/open-mmlab/mmrotate/{REVISION}/LICENSE"
CONFIG_RELATIVE = "configs/oriented_rcnn/oriented_rcnn_r50_fpn_1x_dota_le90.py"
CHECKPOINT_URL = (
    "https://download.openmmlab.com/mmrotate/v0.1.0/oriented_rcnn/"
    "oriented_rcnn_r50_fpn_1x_dota_le90/oriented_rcnn_r50_fpn_1x_dota_le90-6d2b2ce0.pth"
)
IMAGE = {
    "id": "mmrotate-dota-demo",
    "file_name": "demo.jpg",
    "url": f"https://raw.githubusercontent.com/open-mmlab/mmrotate/{REVISION}/demo/demo.jpg",
}
DOTA_CLASSES = [
    "plane", "baseball-diamond", "bridge", "ground-track-field", "small-vehicle",
    "large-vehicle", "ship", "tennis-court", "basketball-court", "storage-tank",
    "soccer-ball-field", "roundabout", "harbor", "swimming-pool", "helicopter",
]

app = modal.App("cvrs-rq002-mmrotate034-oriented-rcnn")
probe_image = modal.Image.debian_slim(python_version="3.10")
runtime_image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("libgl1", "libglib2.0-0")
    .pip_install("torch==1.13.1", "torchvision==0.14.1", index_url="https://download.pytorch.org/whl/cu117")
    .pip_install("mmcv-full==1.7.1", find_links="https://download.openmmlab.com/mmcv/dist/cu117/torch1.13/index.html")
    .pip_install("mmdet==2.28.2", "mmrotate==0.3.4", "numpy==1.23.5", "opencv-python==4.8.1.78", "Pillow==9.5.0", "yapf==0.40.1")
    .add_local_dir("src/cvsubstrate", "/root/cvrs-src/cvsubstrate", copy=True)
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
            digest.update(block); handle.write(block)
    return {"sha256": digest.hexdigest(), "bytes": total}


def _extract(archive: Path, destination: Path) -> Path:
    import tarfile

    destination.mkdir(); root = destination.resolve()
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
        checkpoint = _download(CHECKPOINT_URL, root / "checkpoint.pth", 300 * 1024 * 1024)
        image = _download(IMAGE["url"], root / IMAGE["file_name"], 10 * 1024 * 1024)
        license_identity = _download(LICENSE_URL, root / "LICENSE", 128 * 1024)
        return {
            "schema": "cvrs.rq002.mmrotate-probe.v1", "status": "ASSETS_OBSERVED_NOT_INFERRED",
            "source": {"version": "0.3.4", "revision": REVISION, "url": SOURCE_URL, **source},
            "config": {"relative_path": CONFIG_RELATIVE, "sha256": hashlib.sha256(config.read_bytes()).hexdigest()},
            "checkpoint": {"url": CHECKPOINT_URL, **checkpoint},
            "image": {**IMAGE, **image},
            "license": {"identifier": "Apache-2.0 repository license", "url": LICENSE_URL, **license_identity},
            "data_rights_note": "Official public MMRotate DOTA demo tile; DOTA upstream terms remain separately applicable and redistribution interpretation is not claimed.",
            "controls": {"inference": False, "training": False, "gpu": False, "protected_data_access": 0},
        }


def _flatten(result) -> tuple[list[list[float]], list[float], list[int]]:
    boxes, scores, labels = [], [], []
    for label, per_class in enumerate(result):
        for row in per_class:
            values = [float(v) for v in row]
            boxes.append(values[:5]); scores.append(values[5]); labels.append(label)
    return boxes, scores, labels


def _polygon_bounds(polygons: list[list[list[float]]], width: int, height: int) -> dict:
    import math

    vertices = [point for polygon in polygons for point in polygon]
    outside = sum(not (0 <= x <= width and 0 <= y <= height) for x, y in vertices)
    return {
        "detections": len(polygons), "vertices": len(vertices),
        "finite_vertices": sum(math.isfinite(x) and math.isfinite(y) for x, y in vertices),
        "out_of_image_vertices": outside,
        "maximum_excess_pixels": {
            "left": max([max(0.0, -x) for x, _ in vertices], default=0.0),
            "top": max([max(0.0, -y) for _, y in vertices], default=0.0),
            "right": max([max(0.0, x - width) for x, _ in vertices], default=0.0),
            "bottom": max([max(0.0, y - height) for _, y in vertices], default=0.0),
        },
    }


def _polygon(box: list[float]) -> list[list[float]]:
    import math

    cx, cy, width, height, angle = map(float, box)
    cosine, sine = math.cos(angle), math.sin(angle)
    return [[cx + x * cosine - y * sine, cy + x * sine + y * cosine] for x, y in ((-width / 2, -height / 2), (width / 2, -height / 2), (width / 2, height / 2), (-width / 2, height / 2))]


@app.function(image=runtime_image, cpu=4.0, memory=8192, timeout=1200, retries=0)
def qualify(lock: dict) -> bytes:
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
    import mmrotate
    import numpy as np
    import torch
    from PIL import Image
    from mmdet.apis import inference_detector, init_detector

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
        if _download(CHECKPOINT_URL, checkpoint, 300 * 1024 * 1024)["sha256"] != lock["checkpoint_sha256"]:
            raise RuntimeError("CHECKPOINT_SHA256_MISMATCH")
        image_path = root / IMAGE["file_name"]
        if _download(IMAGE["url"], image_path, 10 * 1024 * 1024)["sha256"] != lock["image"]["sha256"]:
            raise RuntimeError("IMAGE_SHA256_MISMATCH")
        with Image.open(image_path) as image:
            width, height = image.size

        model = init_detector(str(config), str(checkpoint), device="cpu")
        direct_result = inference_detector(model, str(image_path))
        boxes, scores, labels = _flatten(direct_result)
        native = [{"sample_id": IMAGE["id"], "boxes": boxes, "scores": scores, "labels": labels}]
        native_path = root / "native-direct.json"
        native_path.write_text(json.dumps(native, indent=2) + "\n", "utf-8")
        category_map = {str(i): i for i in range(len(DOTA_CLASSES))}
        conversion_status = "PENDING_LOCAL_CVRS_SAVED_NATIVE_CONVERSION"
        conversion = None
        conversion_error = None
        polygons = [_polygon(box) for box in boxes]
        geometry = _polygon_bounds(polygons, width, height)

        request = {
            "protocol_version": "1.0", "operation": "predict", "output_dir": str(root / "wrapped-execution"),
            "payload": {
                "family": "mmrotate", "trust_code": True, "config": str(config), "config_sha256": digest(config),
                "checkpoint": str(checkpoint), "checkpoint_sha256": digest(checkpoint), "device": "cpu",
                "images": [{"id": IMAGE["id"], "path": str(image_path), "sha256": digest(image_path)}],
                "category_mapping": category_map, "angle_convention": "le90", "angle_unit": "radians",
            },
        }
        request_path, response_path = root / "worker-request.json", root / "worker-response.json"
        request_path.write_text(json.dumps(request, indent=2) + "\n", "utf-8")
        worker = "/root/cvrs-src/cvsubstrate/worker_shims/stack_worker.py"
        subprocess.run([sys.executable, worker, "--request", str(request_path), "--response", str(response_path)], check=True)
        response = json.loads(response_path.read_text("utf-8"))
        wrapped_native_path = root / "wrapped-execution/native-predictions.jsonl"
        wrapped = json.loads(wrapped_native_path.read_text("utf-8").splitlines()[0]) if wrapped_native_path.is_file() else None
        repeatability = {
            "labels_and_order_exact": bool(wrapped and labels == wrapped["labels"]),
            "boxes_atol_1e_6": bool(wrapped and np.allclose(boxes, wrapped["boxes"], rtol=0.0, atol=1e-6)),
            "scores_atol_1e_7": bool(wrapped and np.allclose(scores, wrapped["scores"], rtol=0.0, atol=1e-7)),
        }
        repeatability_pass = all(repeatability.values())
        wrapped_pass = response["status"] == "SUCCEEDED"
        passed = wrapped_pass and repeatability_pass
        report = {
            "schema": "cvrs.rq002.mmrotate-oriented-rcnn.v1",
            "status": "PASS_MMROTATE_NATIVE_WRAPPED_PENDING_CVRS" if passed else "FAIL_MMROTATE_NATIVE_OR_WRAPPED",
            "assets": lock, "image": {**IMAGE, "width": width, "height": height},
            "native": {"detections": len(boxes), "sha256": digest(native_path), "geometry_audit": geometry, "angle_convention": "le90", "angle_unit": "radians"},
            "saved_native_conversion": {"status": conversion_status, "report": conversion, "error": conversion_error, "geometry": "xywha_to_clockwise_convex_quadrilateral"},
            "wrapped_execution": {"response": response, "repeatability": repeatability, "repeatability_pass": repeatability_pass},
            "environment": {"python": sys.version, "torch": torch.__version__, "cuda_runtime": torch.version.cuda, "execution_device": "cpu", "mmdet": mmdet.__version__, "mmcv": mmcv.__version__, "mmrotate": mmrotate.__version__, "numpy": np.__version__, "torchvision": importlib.metadata.version("torchvision")},
            "separate_statuses": {"native_inference": "PASS", "transport_fidelity": "PASS" if repeatability_pass else "FAIL", "conversion_fidelity": conversion_status, "runtime_repeatability": "PASS" if repeatability_pass else "FAIL", "evaluator_equivalence": "NOT_RUN_NO_GROUND_TRUTH_IN_DEMO_TILE"},
            "criteria": {"box_atol": 1e-6, "score_atol": 1e-7, "labels_and_order": "exact"},
            "controls": {"training": False, "optimizer_steps": 0, "checkpoint_writes": 0, "protected_data_access": 0, "sealed_test_access": 0, "gpu_concurrency": 0, "geometry_modification": "NONE"},
            "runtime_seconds": time.perf_counter() - started,
            "limits": ["One official MMRotate DOTA demo tile; no DOTA metric claim.", "Out-of-image vertices are counted and preserved, never clipped."],
        }
        (root / "report.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
        checksums = []
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(root)
            if path.is_file() and path.name not in {"checkpoint.pth", "source.tar.gz", IMAGE["file_name"]} and "source" not in rel.parts:
                checksums.append(f"{digest(path)}  {rel.as_posix()}")
        (root / "checksums.sha256").write_text("\n".join(checksums) + "\n", "utf-8")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(root.rglob("*")):
                rel = path.relative_to(root)
                if path.is_file() and path.name not in {"checkpoint.pth", "source.tar.gz", IMAGE["file_name"]} and "source" not in rel.parts:
                    bundle.write(path, rel.as_posix())
        return buffer.getvalue()


@app.local_entrypoint()
def main(mode: str, out: str, lock_json: str = "") -> None:
    destination = Path(out)
    if destination.exists():
        raise RuntimeError(f"refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if mode == "probe":
        destination.write_text(json.dumps(probe.remote(), indent=2) + "\n", "utf-8")
    elif mode == "qualify":
        destination.write_bytes(qualify.remote(json.loads(Path(lock_json).read_text("utf-8"))))
    else:
        raise ValueError("mode must be probe or qualify")
    print(json.dumps({"mode": mode, "output": str(destination), "bytes": destination.stat().st_size}))
