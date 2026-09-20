"""Bounded MMDetection 3.3/RTMDet RQ002 qualification on Modal."""
from __future__ import annotations

import json
from pathlib import Path

import modal


MMDET_REVISION = "44ebd17b145c2372c4b700bfb9cb20dbd28ab64a"
SOURCE_URL = f"https://codeload.github.com/open-mmlab/mmdetection/tar.gz/{MMDET_REVISION}"
LICENSE_URL = f"https://raw.githubusercontent.com/open-mmlab/mmdetection/{MMDET_REVISION}/LICENSE"
CHECKPOINT_URL = (
    "https://download.openmmlab.com/mmdetection/v3.0/rtmdet/"
    "rtmdet_tiny_8xb32-300e_coco/"
    "rtmdet_tiny_8xb32-300e_coco_20220902_112414-78e30dcc.pth"
)
CONFIG_RELATIVE = "configs/rtmdet/rtmdet_tiny_8xb32-300e_coco.py"
IMAGES = [
    {
        "id": "139",
        "file_name": "000000000139.jpg",
        "url": "http://images.cocodataset.org/val2017/000000000139.jpg",
        "sha256": "ffe0f0cec3b2e27aab1967229cdf0a0d7751dcdd5800322f0b8ac0dffb3b8a8d",
    },
    {
        "id": "285",
        "file_name": "000000000285.jpg",
        "url": "http://images.cocodataset.org/val2017/000000000285.jpg",
        "sha256": "f3a2974ce3686332609124c70e3e6a2e3aca43fccf1cd1bd7c5c03820977f57d",
    },
]

app = modal.App("cvrs-rq002-mmdet3-rtmdet-tiny")

probe_image = modal.Image.debian_slim(python_version="3.10")
inference_image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("libgl1", "libglib2.0-0")
    .pip_install(
        "torch==2.1.2",
        "torchvision==0.16.2",
        index_url="https://download.pytorch.org/whl/cu121",
    )
    .pip_install(
        "mmcv==2.1.0",
        find_links="https://download.openmmlab.com/mmcv/dist/cu121/torch2.1/index.html",
    )
    .pip_install(
        "mmengine==0.10.7",
        "mmdet==3.3.0",
        "numpy==1.26.4",
        "pydantic==2.11.9",
        "Pillow==11.3.0",
    )
    .add_local_dir("src/cvsubstrate", "/root/cvrs-src/cvsubstrate", copy=True)
    .add_local_file(
        "qualification/inputs/coco2017-val-128-official-http/annotations/instances_val2017_subset.json",
        "/root/inputs/instances_val2017_subset.json",
        copy=True,
    )
    .env({"PYTHONPATH": "/root/cvrs-src"})
)


def _download(url: str, destination: Path, maximum: int) -> dict:
    import hashlib
    import urllib.request

    digest = hashlib.sha256()
    total = 0
    request = urllib.request.Request(url, headers={"User-Agent": "CVRS-RQ002/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as handle:
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            total += len(block)
            if total > maximum:
                raise RuntimeError("DOWNLOAD_BYTE_BUDGET_EXCEEDED")
            digest.update(block)
            handle.write(block)
    return {"sha256": digest.hexdigest(), "bytes": total}


def _extract_source(archive: Path, destination: Path) -> Path:
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


@app.function(image=probe_image, cpu=2.0, memory=2048, timeout=600, retries=0)
def probe() -> dict:
    import hashlib
    import tempfile

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source_archive = root / "mmdetection.tar.gz"
        source = _download(SOURCE_URL, source_archive, 100 * 1024 * 1024)
        source_root = _extract_source(source_archive, root / "source")
        config = source_root / CONFIG_RELATIVE
        checkpoint = _download(CHECKPOINT_URL, root / "checkpoint.pth", 100 * 1024 * 1024)
        license_identity = _download(LICENSE_URL, root / "LICENSE", 128 * 1024)
        image_records = []
        for item in IMAGES:
            destination = root / item["file_name"]
            identity = _download(item["url"], destination, 2 * 1024 * 1024)
            if identity["sha256"] != item["sha256"]:
                raise RuntimeError(f"IMAGE_SHA256_MISMATCH:{item['id']}")
            image_records.append({**item, **identity})
        return {
            "schema": "cvrs.rq002.mmdet3-rtmdet-probe.v1",
            "status": "ASSETS_OBSERVED_NOT_INFERRED",
            "mmdetection": {"version": "3.3.0", "revision": MMDET_REVISION, "source_url": SOURCE_URL, **source},
            "config": {
                "relative_path": CONFIG_RELATIVE,
                "sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
            },
            "checkpoint": {"url": CHECKPOINT_URL, **checkpoint},
            "license": {"identifier": "Apache-2.0", "url": LICENSE_URL, **license_identity},
            "images": image_records,
            "controls": {"inference": False, "training": False, "gpu": False, "protected_data_access": 0},
        }


@app.function(image=inference_image, gpu="T4", cpu=2.0, memory=8192, timeout=900, retries=0)
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
    import mmengine
    import numpy as np
    import torch
    from PIL import Image
    from mmdet.apis import inference_detector, init_detector

    from cvsubstrate.heritage.importer import import_predictions

    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source_archive = root / "mmdetection.tar.gz"
        source_identity = _download(SOURCE_URL, source_archive, 100 * 1024 * 1024)
        if source_identity["sha256"] != lock["source_sha256"]:
            raise RuntimeError("SOURCE_SHA256_MISMATCH")
        source_root = _extract_source(source_archive, root / "source")
        config = source_root / CONFIG_RELATIVE
        if digest(config) != lock["config_sha256"]:
            raise RuntimeError("CONFIG_SHA256_MISMATCH")
        checkpoint = root / "checkpoint.pth"
        checkpoint_identity = _download(CHECKPOINT_URL, checkpoint, 100 * 1024 * 1024)
        if checkpoint_identity["sha256"] != lock["checkpoint_sha256"]:
            raise RuntimeError("CHECKPOINT_SHA256_MISMATCH")
        image_root = root / "images"
        image_root.mkdir()
        image_meta = []
        for item in IMAGES:
            path = image_root / item["file_name"]
            identity = _download(item["url"], path, 2 * 1024 * 1024)
            if identity["sha256"] != item["sha256"]:
                raise RuntimeError(f"IMAGE_SHA256_MISMATCH:{item['id']}")
            with Image.open(path) as image:
                width, height = image.size
            image_meta.append({**item, "width": width, "height": height})

        annotations = json.loads(Path("/root/inputs/instances_val2017_subset.json").read_text("utf-8"))
        categories = annotations["categories"]
        model = init_detector(str(config), str(checkpoint), device="cuda:0")
        native_rows = []
        for item in image_meta:
            result = inference_detector(model, str(image_root / item["file_name"]))
            pred = result.pred_instances
            native_rows.append(
                {
                    "sample_id": item["id"],
                    "boxes": pred.bboxes.detach().cpu().tolist(),
                    "scores": pred.scores.detach().cpu().tolist(),
                    "labels": [int(value) for value in pred.labels.detach().cpu().tolist()],
                }
            )
        native_path = root / "native-direct.jsonl"
        native_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in native_rows), "utf-8")

        classes = list(model.dataset_meta["classes"])
        if classes != [item["name"] for item in categories]:
            raise RuntimeError("COCO_CATEGORY_ORDER_MISMATCH")
        category_map = {str(index): item["id"] for index, item in enumerate(categories)}
        manifest = {
            "schema_version": "1.0",
            "name": "rq002-coco-two-image-smoke",
            "version": "2017",
            "purpose": "research_dataset",
            "categories": [{"id": item["id"], "name": item["name"]} for item in categories],
            "samples": [
                {
                    "id": item["id"],
                    "image": item["file_name"],
                    "sha256": item["sha256"],
                    "width": item["width"],
                    "height": item["height"],
                    "source_kind": "real",
                }
                for item in image_meta
            ],
            "splits": {"dev": {"role": "dev", "sample_ids": [item["id"] for item in image_meta]}},
            "licenses": {
                "data": "COCO image license varies by source image; official COCO terms recorded in the parent lock",
                "annotations": "CC BY 4.0",
                "code": "N/A",
                "redistribution": "unknown",
            },
        }
        manifest_path = root / "dataset.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", "utf-8")
        conversion_status = "PASS"
        conversion_error = None
        try:
            conversion = import_predictions(
                native_path,
                manifest_path,
                "dev",
                category_map,
                root / "converted-native",
                native_format="mmdet3_instances",
            )
        except Exception as exc:
            conversion_status = "FAIL"
            conversion_error = f"{type(exc).__name__}: {exc}"
            conversion = None

        request = {
            "schema_version": "1.0",
            "protocol_version": "1.0",
            "operation": "predict",
            "experiment": {
                "adapter": {
                    "name": "mmdetection",
                    "config": {
                        "config_path": str(config),
                        "config_sha256": digest(config),
                        "trust_executable_config": True,
                        "category_map": category_map,
                        "upstream": "open-mmlab/mmdetection",
                        "revision": MMDET_REVISION,
                        "profile": "mmdet3",
                        "device": "cuda:0",
                    },
                },
                "eval_split": "dev",
            },
            "manifest": manifest,
            "checkpoint": {"path": str(checkpoint), "sha256": digest(checkpoint), "trust": "trusted_legacy_pickle"},
            "output_dir": str(root / "wrapped-execution"),
            "data_root": str(image_root),
        }
        request_path = root / "worker-request.json"
        response_path = root / "worker-response.json"
        request_path.write_text(json.dumps(request, indent=2) + "\n", "utf-8")
        worker = Path("/root/cvrs-src/cvsubstrate/worker_shims/mmdetection_worker.py")
        subprocess.run(
            [sys.executable, str(worker), "--request", str(request_path), "--response", str(response_path)],
            check=True,
        )
        response = json.loads(response_path.read_text("utf-8"))
        wrapped_rows = []
        wrapped_native = root / "wrapped-execution/upstream_predictions.jsonl"
        if wrapped_native.is_file():
            wrapped_rows = [json.loads(line) for line in wrapped_native.read_text("utf-8").splitlines()]
        repeatability = []
        if len(wrapped_rows) == len(native_rows):
            for direct, wrapped in zip(native_rows, wrapped_rows):
                labels_equal = direct["labels"] == wrapped["zero_based_labels"]
                boxes_close = np.shape(direct["boxes"]) == np.shape(wrapped["boxes"]) and np.allclose(
                    direct["boxes"], wrapped["boxes"], rtol=0.0, atol=1e-6
                )
                scores_close = np.shape(direct["scores"]) == np.shape(wrapped["scores"]) and np.allclose(
                    direct["scores"], wrapped["scores"], rtol=0.0, atol=1e-7
                )
                repeatability.append(
                    {"sample_id": direct["sample_id"], "labels_and_order_exact": labels_equal, "boxes_atol_1e_6": bool(boxes_close), "scores_atol_1e_7": bool(scores_close)}
                )
        repeatability_pass = len(repeatability) == len(native_rows) and all(
            all(value for key, value in item.items() if key != "sample_id") for item in repeatability
        )
        wrapped_pass = response["status"] == "SUCCEEDED"
        passed = conversion_status == "PASS" and wrapped_pass and repeatability_pass
        report = {
            "schema": "cvrs.rq002.mmdet3-rtmdet.v1",
            "status": "PASS_MMDET3_RTMDET_NATIVE_AND_CVRS" if passed else "FAIL_MMDET3_RTMDET_NATIVE_AND_CVRS",
            "assets": lock,
            "images": image_meta,
            "native": {"images": len(native_rows), "detections": sum(len(row["boxes"]) for row in native_rows), "sha256": digest(native_path)},
            "saved_native_conversion": {"status": conversion_status, "report": conversion, "error": conversion_error},
            "wrapped_execution": {"response": response, "repeatability": repeatability, "repeatability_pass": repeatability_pass},
            "environment": {
                "python": sys.version,
                "torch": torch.__version__,
                "cuda_runtime": torch.version.cuda,
                "cuda_device": torch.cuda.get_device_name(0),
                "mmdet": mmdet.__version__,
                "mmcv": mmcv.__version__,
                "mmengine": mmengine.__version__,
                "numpy": np.__version__,
                "packages": {name: importlib.metadata.version(name) for name in ("torchvision", "pydantic")},
            },
            "criteria": {"box_atol": 1e-6, "score_atol": 1e-7, "label_and_order": "exact"},
            "controls": {"training": False, "optimizer_steps": 0, "checkpoint_writes": 0, "protected_data_access": 0, "sealed_test_access": 0, "gpu_concurrency": 1},
            "runtime_seconds": time.perf_counter() - started,
            "limits": ["Two-image interoperability smoke only; no accuracy or COCO metric claim.", "Native output is preserved before either CVRS conversion path."],
        }
        (root / "report.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
        checksums = []
        excluded = {"checkpoint.pth", "mmdetection.tar.gz"}
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name not in excluded and "source" not in path.relative_to(root).parts and "images" not in path.relative_to(root).parts:
                checksums.append(f"{digest(path)}  {path.relative_to(root).as_posix()}")
        (root / "checksums.sha256").write_text("\n".join(checksums) + "\n", "utf-8")
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(root.rglob("*")):
                relative = path.relative_to(root)
                if path.is_file() and path.name not in excluded and "source" not in relative.parts and "images" not in relative.parts:
                    bundle.write(path, relative.as_posix())
        return archive.getvalue()


@app.function(image=inference_image, cpu=2.0, memory=4096, timeout=300, retries=0)
def convert_saved_native(native_text: str) -> bytes:
    import hashlib
    import io
    import tempfile
    import zipfile

    from PIL import Image

    from cvsubstrate.heritage.importer import import_predictions

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        image_root = root / "images"
        image_root.mkdir()
        image_meta = []
        for item in IMAGES:
            path = image_root / item["file_name"]
            identity = _download(item["url"], path, 2 * 1024 * 1024)
            if identity["sha256"] != item["sha256"]:
                raise RuntimeError(f"IMAGE_SHA256_MISMATCH:{item['id']}")
            with Image.open(path) as image:
                width, height = image.size
            image_meta.append({**item, "width": width, "height": height})
        annotations = json.loads(Path("/root/inputs/instances_val2017_subset.json").read_text("utf-8"))
        categories = annotations["categories"]
        category_map = {str(index): item["id"] for index, item in enumerate(categories)}
        manifest = {
            "schema_version": "1.0",
            "name": "rq002-coco-two-image-smoke",
            "version": "2017",
            "purpose": "research_dataset",
            "categories": [{"id": item["id"], "name": item["name"]} for item in categories],
            "samples": [
                {"id": item["id"], "image": item["file_name"], "sha256": item["sha256"], "width": item["width"], "height": item["height"], "source_kind": "real"}
                for item in image_meta
            ],
            "splits": {"dev": {"role": "dev", "sample_ids": [item["id"] for item in image_meta]}},
            "licenses": {"data": "COCO source-image license varies", "annotations": "CC BY 4.0", "code": "N/A", "redistribution": "unknown"},
        }
        manifest_path = image_root / "dataset.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", "utf-8")
        native_path = root / "native-direct.jsonl"
        native_path.write_text(native_text, "utf-8")
        report = import_predictions(native_path, manifest_path, "dev", category_map, root / "converted-native", native_format="mmdet3_instances")
        result = {
            "schema": "cvrs.rq002.mmdet3-saved-native-conversion.v1",
            "status": "PASS_SAVED_NATIVE_CVRS_CONVERSION",
            "source_native_sha256": hashlib.sha256(native_text.encode("utf-8")).hexdigest(),
            "conversion": report,
            "controls": {"inference": False, "training": False, "gpu": False, "protected_data_access": 0, "sealed_test_access": 0},
        }
        (root / "conversion-only-report.json").write_text(json.dumps(result, indent=2) + "\n", "utf-8")
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(root.rglob("*")):
                relative = path.relative_to(root)
                if path.is_file() and "images" not in relative.parts:
                    bundle.write(path, relative.as_posix())
        return archive.getvalue()


@app.local_entrypoint()
def main(mode: str, out: str, lock_json: str = "", native_jsonl: str = "") -> None:
    destination = Path(out)
    if destination.exists():
        raise RuntimeError(f"refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if mode == "probe":
        destination.write_text(json.dumps(probe.remote(), indent=2) + "\n", "utf-8")
    elif mode == "qualify":
        lock = json.loads(Path(lock_json).read_text("utf-8"))
        destination.write_bytes(qualify.remote(lock))
    elif mode == "convert-saved-native":
        native_text = Path(native_jsonl).read_text("utf-8")
        destination.write_bytes(convert_saved_native.remote(native_text))
    else:
        raise ValueError("mode must be probe, qualify, or convert-saved-native")
    print(json.dumps({"mode": mode, "output": str(destination), "bytes": destination.stat().st_size}))
