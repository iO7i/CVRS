"""Bounded public DINOv2 ViT-S/14 feature fallback on Modal."""
from __future__ import annotations

import json
from pathlib import Path

import modal


SOURCE_REVISION = "7764ea0f912e53c92e82eb78a2a1631e92725fc8"
SOURCE_URL = f"https://codeload.github.com/facebookresearch/dinov2/tar.gz/{SOURCE_REVISION}"
MODEL_REPO = "facebook/dinov2-small"
MODEL_REVISION = "ed25f3a31f01632728cabb09d1542f84ab7b0056"
CHECKPOINT = "model.safetensors"
EXPECTED_CHECKPOINT_SHA256 = "ae1e99fcefd534ed978cdeb8326f08030c96e28b7a81ffcbc98a857c84d14be1"
MODEL_FILES = ["model.safetensors", "config.json", "preprocessor_config.json"]
DENSE_INDICES = [0, 15, 119, 120, 135, 136, 240, 255]
IMAGES = [
    {"id": "139", "file_name": "000000000139.jpg", "url": "http://images.cocodataset.org/val2017/000000000139.jpg", "sha256": "ffe0f0cec3b2e27aab1967229cdf0a0d7751dcdd5800322f0b8ac0dffb3b8a8d"},
    {"id": "285", "file_name": "000000000285.jpg", "url": "http://images.cocodataset.org/val2017/000000000285.jpg", "sha256": "f3a2974ce3686332609124c70e3e6a2e3aca43fccf1cd1bd7c5c03820977f57d"},
]

app = modal.App("cvrs-rq002-dinov2-public")
assets = modal.Volume.from_name("cvrs-rq002-dinov2-public-assets", create_if_missing=True)
probe_image = modal.Image.debian_slim(python_version="3.12").pip_install("huggingface_hub==0.36.0")
runtime_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch==2.7.1", "torchvision==0.22.1", index_url="https://download.pytorch.org/whl/cu126")
    .pip_install("transformers==4.57.1", "huggingface_hub==0.36.0", "safetensors==0.6.2", "numpy==1.26.4", "Pillow==12.0.0")
    .env({"HF_HUB_OFFLINE": "1"})
)


def _sha(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _download(url: str, destination: Path, maximum: int) -> dict:
    import urllib.request

    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "CVRS-RQ002/1.0"})
    total = 0
    with urllib.request.urlopen(request, timeout=300) as response, destination.open("wb") as handle:
        for block in iter(lambda: response.read(1024 * 1024), b""):
            total += len(block)
            if total > maximum:
                raise RuntimeError("DOWNLOAD_BYTE_BUDGET_EXCEEDED:" + destination.name)
            handle.write(block)
    return {"sha256": _sha(destination), "bytes": total}


@app.function(image=probe_image, volumes={"/assets": assets}, cpu=2.0, memory=4096, timeout=1200, retries=0)
def acquire() -> dict:
    import shutil
    import tempfile
    from huggingface_hub import HfApi, hf_hub_download

    info = HfApi().model_info(MODEL_REPO, revision=MODEL_REVISION, files_metadata=True)
    if info.sha != MODEL_REVISION or info.private or info.gated:
        raise RuntimeError("PUBLIC_MODEL_IDENTITY_OR_ACCESS_MISMATCH")
    root = Path("/assets") / MODEL_REVISION
    model_root = root / "model"
    model_root.mkdir(parents=True, exist_ok=True)
    observed = {}
    for name in MODEL_FILES:
        cached = Path(hf_hub_download(MODEL_REPO, name, revision=MODEL_REVISION))
        target = model_root / name
        shutil.copyfile(cached, target)
        observed[name] = {"sha256": _sha(target), "bytes": target.stat().st_size}
    if observed[CHECKPOINT]["sha256"] != EXPECTED_CHECKPOINT_SHA256:
        raise RuntimeError("CHECKPOINT_SHA256_MISMATCH")
    with tempfile.TemporaryDirectory() as td:
        archive = Path(td) / "dinov2-source.tar.gz"
        source_identity = _download(SOURCE_URL, archive, 200 * 1024 * 1024)
        shutil.copyfile(archive, root / "dinov2-source.tar.gz")
    assets.commit()
    return {
        "schema": "cvrs.rq002.dinov2-public-acquisition.v1",
        "status": "PASS_PUBLIC_UNGATED_FROZEN_ASSETS",
        "source": {"repo": "facebookresearch/dinov2", "revision": SOURCE_REVISION, **source_identity},
        "model": {"repo": MODEL_REPO, "revision": MODEL_REVISION, "files": observed},
        "runtime": {"transformers": "4.57.1", "torch": "2.7.1", "python": "3.12"},
        "dense_subset_indices": DENSE_INDICES,
        "controls": {"inference": False, "training": False, "protected_data_access": 0, "credentials_used": False},
    }


@app.function(image=runtime_image, volumes={"/assets": assets}, gpu="T4", cpu=4.0, memory=8192, timeout=1200, retries=0)
def qualify(lock: dict) -> bytes:
    import io
    import sys
    import tempfile
    import time
    import zipfile

    import numpy as np
    import torch
    from PIL import Image
    from transformers import AutoImageProcessor, AutoModel

    started = time.perf_counter()
    root = Path("/assets") / MODEL_REVISION
    if _sha(root / "dinov2-source.tar.gz") != lock["source"]["sha256"]:
        raise RuntimeError("SOURCE_SHA256_MISMATCH")
    for name, expected in lock["model"]["files"].items():
        if _sha(root / "model" / name) != expected["sha256"]:
            raise RuntimeError("MODEL_FILE_SHA256_MISMATCH:" + name)
    processor = AutoImageProcessor.from_pretrained(root / "model", local_files_only=True)
    model = AutoModel.from_pretrained(root / "model", local_files_only=True).to("cuda:0").eval()

    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        image_root = out / "images"
        image_root.mkdir()
        images = []
        metadata = []
        for item in IMAGES:
            target = image_root / item["file_name"]
            identity = _download(item["url"], target, 2 * 1024 * 1024)
            if identity["sha256"] != item["sha256"]:
                raise RuntimeError("IMAGE_SHA256_MISMATCH:" + item["id"])
            with Image.open(target) as opened:
                image = opened.convert("RGB")
                metadata.append({**item, "width": image.width, "height": image.height})
                images.append(image.copy())
        inputs = processor(images=images, return_tensors="pt")
        with torch.inference_mode():
            outputs = model(**{key: value.to("cuda:0") for key, value in inputs.items()})
        tokens = outputs.last_hidden_state.float().cpu().numpy()
        global_features = tokens[:, 0, :]
        dense_full = tokens[:, 1:, :]
        if dense_full.shape[1] != 256 or dense_full.shape[2] != 384:
            raise RuntimeError("DENSE_FEATURE_SHAPE_UNEXPECTED")
        dense_subset = dense_full[:, DENSE_INDICES, :]
        feature_path = out / "features.npz"
        np.savez_compressed(feature_path, global_embeddings=global_features, dense_subset=dense_subset, dense_indices=np.asarray(DENSE_INDICES, dtype=np.int64), sample_ids=np.asarray([item["id"] for item in metadata]))
        reloaded = np.load(feature_path)
        reload_exact = np.array_equal(reloaded["global_embeddings"], global_features) and np.array_equal(reloaded["dense_subset"], dense_subset) and np.array_equal(reloaded["dense_indices"], np.asarray(DENSE_INDICES, dtype=np.int64))
        normalized = reloaded["global_embeddings"] / np.linalg.norm(reloaded["global_embeddings"], axis=1, keepdims=True)
        similarities = normalized @ normalized.T
        nearest = similarities.argmax(axis=1).tolist()
        self_retrieval = nearest == list(range(len(metadata)))
        report = {
            "schema": "cvrs.rq002.dinov2-public-features.v1",
            "status": "PASS_DINOV2_PUBLIC_GLOBAL_DENSE_RELOAD_RETRIEVAL" if reload_exact and self_retrieval else "FAIL_DINOV2_PUBLIC_FEATURE_QUALIFICATION",
            "claim_boundary": "DINOv2 ViT-S/14 representations only; not DINOv3 qualification",
            "assets": lock, "inputs": metadata,
            "features": {"tokens_shape": list(tokens.shape), "global_shape": list(global_features.shape), "dense_full_shape": list(dense_full.shape), "dense_subset_shape": list(dense_subset.shape), "dense_indices": DENSE_INDICES, "artifact_sha256": _sha(feature_path)},
            "reload": {"exact": reload_exact, "model_rerun": False},
            "retrieval_from_reloaded_artifact": {"cosine_similarity": similarities.tolist(), "nearest_indices": nearest, "self_retrieval": self_retrieval, "model_rerun": False},
            "preprocessing": processor.to_dict(),
            "environment": {"python": sys.version, "torch": torch.__version__, "transformers": "4.57.1", "device": torch.cuda.get_device_name(0)},
            "controls": {"training": False, "optimizer_steps": 0, "protected_data_access": 0, "sealed_test_access": 0, "gpu_concurrency": 1, "automatic_paid_retry": False},
            "runtime_seconds": time.perf_counter() - started,
        }
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
        (out / "checksums.sha256").write_text(f"{_sha(feature_path)}  features.npz\n{_sha(out / 'report.json')}  report.json\n", "utf-8")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(out.rglob("*")):
                if path.is_file() and path.name not in {item["file_name"] for item in IMAGES}:
                    bundle.write(path, path.relative_to(out).as_posix())
        return buffer.getvalue()


@app.local_entrypoint()
def main(mode: str, out: str, lock_json: str = "") -> None:
    destination = Path(out)
    if destination.exists():
        raise RuntimeError(f"refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if mode == "acquire":
        destination.write_text(json.dumps(acquire.remote(), indent=2) + "\n", "utf-8")
    elif mode == "qualify":
        destination.write_bytes(qualify.remote(json.loads(Path(lock_json).read_text("utf-8"))))
    else:
        raise ValueError("mode must be acquire or qualify")
    print(json.dumps({"mode": mode, "output": str(destination), "bytes": destination.stat().st_size}))
