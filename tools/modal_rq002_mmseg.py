"""Bounded MMSegmentation 1.2.2 / FCN R50 ADE20K qualification on Modal."""
from __future__ import annotations

import json
from pathlib import Path

import modal


REVISION = "c685fe6767c4cadf6b051983ca6208f1b9d1ccb8"
SOURCE_URL = f"https://codeload.github.com/open-mmlab/mmsegmentation/tar.gz/{REVISION}"
LICENSE_URL = f"https://raw.githubusercontent.com/open-mmlab/mmsegmentation/{REVISION}/LICENSE"
CONFIG_RELATIVE = "configs/fcn/fcn_r50-d8_4xb4-80k_ade20k-512x512.py"
CHECKPOINT_URL = (
    "https://download.openmmlab.com/mmsegmentation/v0.5/fcn/"
    "fcn_r50-d8_512x512_80k_ade20k/"
    "fcn_r50-d8_512x512_80k_ade20k_20200614_144016-f8ac5082.pth"
)
ADE_REVISION = "df5ee67bfe143f3e0cbd5d3929aeeb817a256cbc"
IMAGE = {
    "id": "ADE_train_00016869",
    "file_name": "ADE_train_00016869.jpg",
    "url": (
        "https://raw.githubusercontent.com/CSAILVision/ADE20K/"
        f"{ADE_REVISION}/dataset/ADE20K_2021_17_01/images/ADE/training/urban/street/"
        "ADE_train_00016869.jpg"
    ),
}
ADE_README_URL = f"https://raw.githubusercontent.com/CSAILVision/ADE20K/{ADE_REVISION}/README.md"

app = modal.App("cvrs-rq002-mmseg122-fcn-ade20k")
probe_image = modal.Image.debian_slim(python_version="3.10")
runtime_image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("libgl1", "libglib2.0-0")
    .pip_install("torch==2.1.2", "torchvision==0.16.2", index_url="https://download.pytorch.org/whl/cu121")
    .pip_install("mmcv==2.1.0", find_links="https://download.openmmlab.com/mmcv/dist/cu121/torch2.1/index.html")
    .pip_install(
        "mmengine==0.10.7", "mmsegmentation==1.2.2", "numpy==1.26.4",
        "opencv-python-headless==4.8.1.78", "Pillow==10.4.0", "ftfy==6.3.1",
        "regex==2024.11.6",
    )
    .add_local_dir("src/cvsubstrate", "/root/cvrs-src/cvsubstrate", copy=True)
    .env({"PYTHONPATH": "/root/cvrs-src"})
)


def _download(url: str, destination: Path, maximum: int) -> dict:
    import hashlib
    import urllib.request

    digest = hashlib.sha256(); total = 0
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
        root = Path(td); archive = root / "source.tar.gz"
        source = _download(SOURCE_URL, archive, 200 * 1024 * 1024)
        source_root = _extract(archive, root / "source")
        config = source_root / CONFIG_RELATIVE
        checkpoint = _download(CHECKPOINT_URL, root / "checkpoint.pth", 400 * 1024 * 1024)
        image = _download(IMAGE["url"], root / IMAGE["file_name"], 20 * 1024 * 1024)
        license_identity = _download(LICENSE_URL, root / "LICENSE", 128 * 1024)
        ade_readme = _download(ADE_README_URL, root / "ADE20K-README.md", 2 * 1024 * 1024)
        return {
            "schema": "cvrs.rq002.mmseg-probe.v1", "status": "ASSETS_OBSERVED_NOT_INFERRED",
            "source": {"version": "1.2.2", "revision": REVISION, "url": SOURCE_URL, **source},
            "config": {"relative_path": CONFIG_RELATIVE, "sha256": hashlib.sha256(config.read_bytes()).hexdigest()},
            "checkpoint": {"url": CHECKPOINT_URL, **checkpoint},
            "image": {**IMAGE, "source_revision": ADE_REVISION, **image},
            "license": {"identifier": "Apache-2.0 repository license", "url": LICENSE_URL, **license_identity},
            "data_terms": {"url": ADE_README_URL, **ade_readme},
            "data_rights_note": "One publicly exposed ADE20K repository example image; upstream README requires registration for full-dataset access and terms. No bulk acquisition or redistribution claim.",
            "controls": {"inference": False, "training": False, "gpu": False, "protected_data_access": 0},
        }


@app.function(image=runtime_image, gpu="T4", cpu=4.0, memory=8192, timeout=1200, retries=0)
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
    import mmengine
    import mmseg
    import numpy as np
    import torch
    from PIL import Image
    from mmseg.apis import inference_model, init_model

    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); archive = root / "source.tar.gz"
        if _download(SOURCE_URL, archive, 200 * 1024 * 1024)["sha256"] != lock["source_sha256"]:
            raise RuntimeError("SOURCE_SHA256_MISMATCH")
        source_root = _extract(archive, root / "source")
        config = source_root / CONFIG_RELATIVE
        if digest(config) != lock["config_sha256"]:
            raise RuntimeError("CONFIG_SHA256_MISMATCH")
        checkpoint = root / "checkpoint.pth"
        if _download(CHECKPOINT_URL, checkpoint, 400 * 1024 * 1024)["sha256"] != lock["checkpoint_sha256"]:
            raise RuntimeError("CHECKPOINT_SHA256_MISMATCH")
        image_path = root / IMAGE["file_name"]
        if _download(IMAGE["url"], image_path, 20 * 1024 * 1024)["sha256"] != lock["image"]["sha256"]:
            raise RuntimeError("IMAGE_SHA256_MISMATCH")
        with Image.open(image_path) as image:
            width, height = image.size

        model = init_model(str(config), str(checkpoint), device="cuda:0")
        direct = inference_model(model, str(image_path)).pred_sem_seg.data.detach().cpu().numpy()[0].astype(np.int32)
        if direct.shape != (height, width):
            raise RuntimeError("NATIVE_OUTPUT_NOT_ORIGINAL_IMAGE_SHAPE")
        native_path = root / "native-direct.npy"; np.save(native_path, direct, allow_pickle=False)
        npz_path = root / "native-direct.npz"; np.savez_compressed(npz_path, maps=direct[None, ...])

        request = {
            "protocol_version": "1.0", "operation": "predict", "output_dir": str(root / "wrapped-execution"),
            "payload": {
                "family": "mmseg1", "trust_code": True, "config": str(config), "config_sha256": digest(config),
                "checkpoint": str(checkpoint), "checkpoint_sha256": digest(checkpoint), "device": "cuda:0",
                "images": [{"id": IMAGE["id"], "path": str(image_path), "sha256": digest(image_path)}],
                "category_mapping": {str(i): i for i in range(150)}, "ignore_index": 255, "reduce_zero_label": False,
            },
        }
        request_path, response_path = root / "worker-request.json", root / "worker-response.json"
        request_path.write_text(json.dumps(request, indent=2) + "\n", "utf-8")
        worker = "/root/cvrs-src/cvsubstrate/worker_shims/stack_worker.py"
        subprocess.run([sys.executable, worker, "--request", str(request_path), "--response", str(response_path)], check=True)
        response = json.loads(response_path.read_text("utf-8"))
        wrapped_path = root / "wrapped-execution/labels-0.npy"
        wrapped = np.load(wrapped_path, allow_pickle=False)
        exact = bool(np.array_equal(direct, wrapped))
        labels = [int(value) for value in np.unique(direct)]
        valid = direct.dtype == np.int32 and all(0 <= value < 150 for value in labels)
        passed = response["status"] == "SUCCEEDED" and exact and valid
        report = {
            "schema": "cvrs.rq002.mmseg-fcn-ade20k.v1",
            "status": "PASS_MMSEG_NATIVE_WRAPPED_PENDING_CVRS" if passed else "FAIL_MMSEG_NATIVE_OR_WRAPPED",
            "assets": lock,
            "image": {**IMAGE, "width": width, "height": height},
            "native": {"sha256": digest(native_path), "npz_sha256": digest(npz_path), "shape": list(direct.shape), "dtype": str(direct.dtype), "unique_labels": labels},
            "saved_native_conversion": {"status": "PENDING_LOCAL_CVRS_ARRAY_DECODER", "geometry": "original_image_semantic_label_map"},
            "wrapped_execution": {"response": response, "array_exact": exact, "wrapped_sha256": digest(wrapped_path)},
            "environment": {"python": sys.version, "torch": torch.__version__, "cuda_runtime": torch.version.cuda, "device": str(next(model.parameters()).device), "mmcv": mmcv.__version__, "mmengine": mmengine.__version__, "mmsegmentation": mmseg.__version__, "numpy": np.__version__, "torchvision": importlib.metadata.version("torchvision")},
            "preprocessing": "published MMSegmentation config test_pipeline; source bytes passed by path; output restored to original image shape",
            "label_semantics": {"classes": 150, "native_indices": "0..149", "ignore_index": 255, "reduce_zero_label": False},
            "separate_statuses": {"native_inference": "PASS", "transport_fidelity": "PASS" if exact else "FAIL", "conversion_fidelity": "PENDING_LOCAL_CVRS_ARRAY_DECODER", "runtime_repeatability": "PASS_EXACT" if exact else "FAIL", "evaluator_equivalence": "NOT_RUN_NO_REGISTERED_ADE20K_GROUND_TRUTH"},
            "controls": {"training": False, "optimizer_steps": 0, "checkpoint_writes": 0, "protected_data_access": 0, "sealed_test_access": 0, "gpu_concurrency": 1, "label_modification": "NONE"},
            "runtime_seconds": time.perf_counter() - started,
            "limits": ["One public ADE20K repository example image; no mIoU or scientific-quality claim.", "No ground-truth annotation downloaded or inferred."],
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
