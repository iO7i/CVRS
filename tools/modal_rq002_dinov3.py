"""Bounded official DINOv3 ViT-S/16 feature qualification on Modal."""
from __future__ import annotations

import json
from pathlib import Path

import modal


SOURCE_REVISION = "6876159a11b4df116f30f667f8c9888617df0751"
SOURCE_URL = f"https://codeload.github.com/facebookresearch/dinov3/tar.gz/{SOURCE_REVISION}"
MODEL_REPO = "facebook/dinov3-vits16-pretrain-lvd1689m"
MODEL_REVISION = "114c1379950215c8b35dfcd4e90a5c251dde0d32"
CHECKPOINT = "model.safetensors"
EXPECTED_CHECKPOINT_SHA256 = "4610ad75edef83e75afdebf162d148dc628045ea6cbb83d67d4708c709c4f91d"
MODEL_FILES = ["model.safetensors", "config.json", "preprocessor_config.json", "README.md"]
DENSE_INDICES = [0, 15, 119, 120, 135, 136, 240, 255]
SECRET_NAME = "cvrs-huggingface-read"
IMAGES = [
    {"id": "139", "file_name": "000000000139.jpg", "url": "http://images.cocodataset.org/val2017/000000000139.jpg", "sha256": "ffe0f0cec3b2e27aab1967229cdf0a0d7751dcdd5800322f0b8ac0dffb3b8a8d"},
    {"id": "285", "file_name": "000000000285.jpg", "url": "http://images.cocodataset.org/val2017/000000000285.jpg", "sha256": "f3a2974ce3686332609124c70e3e6a2e3aca43fccf1cd1bd7c5c03820977f57d"},
]

app = modal.App("cvrs-rq002-dinov3-vits16")
assets = modal.Volume.from_name("cvrs-rq002-dinov3-assets", create_if_missing=True)
hf_secret = modal.Secret.from_name(SECRET_NAME)
probe_image = modal.Image.debian_slim(python_version="3.11").pip_install("huggingface_hub==0.36.0")
runtime_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch==2.7.1", "torchvision==0.22.1", index_url="https://download.pytorch.org/whl/cu126")
    .pip_install("numpy==2.1.3", "Pillow==12.0.0", "safetensors==0.6.2")
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


@app.function(
    image=probe_image,
    volumes={"/assets": assets},
    secrets=[hf_secret],
    cpu=2.0,
    memory=4096,
    timeout=1200,
    retries=0,
)
def acquire() -> dict:
    import os
    import shutil
    import tarfile
    import tempfile
    from huggingface_hub import HfApi, hf_hub_download

    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN_MISSING")
    api = HfApi(token=token)
    api.whoami(token=token)
    info = api.model_info(MODEL_REPO, revision=MODEL_REVISION, token=token)
    if info.sha != MODEL_REVISION:
        raise RuntimeError("MODEL_REVISION_MISMATCH")
    root = Path("/assets") / MODEL_REVISION
    model_root = root / "model"
    source_root = root / "source"
    with tempfile.TemporaryDirectory() as td:
        temp = Path(td)
        source_archive = temp / "dinov3-source.tar.gz"
        source_identity = _download(SOURCE_URL, source_archive, 100 * 1024 * 1024)
        if source_root.exists():
            shutil.rmtree(source_root)
        source_root.mkdir(parents=True)
        with tarfile.open(source_archive, "r:gz") as archive:
            archive.extractall(source_root, filter="data")
        extracted = [path for path in source_root.iterdir() if path.is_dir()]
        if len(extracted) != 1:
            raise RuntimeError("SOURCE_ARCHIVE_LAYOUT_UNEXPECTED")
        (root / "dinov3-source.tar.gz").write_bytes(source_archive.read_bytes())
        model_root.mkdir(parents=True, exist_ok=True)
        observed = {}
        for name in MODEL_FILES:
            cached = Path(hf_hub_download(MODEL_REPO, name, revision=MODEL_REVISION, token=token))
            target = model_root / name
            shutil.copyfile(cached, target)
            observed[name] = {"sha256": _sha(target), "bytes": target.stat().st_size}
        if observed[CHECKPOINT]["sha256"] != EXPECTED_CHECKPOINT_SHA256:
            raise RuntimeError("CHECKPOINT_SHA256_MISMATCH")
    assets.commit()
    return {
        "schema": "cvrs.rq002.dinov3-acquisition.v1",
        "status": "PASS_AUTHENTICATED_ACCESS_AND_FROZEN_ASSETS",
        "authenticated_access": True,
        "credential_recorded": False,
        "source": {"repo": "facebookresearch/dinov3", "revision": SOURCE_REVISION, **source_identity},
        "model": {"repo": MODEL_REPO, "revision": MODEL_REVISION, "files": observed},
        "preprocessing": {"resize": [256, 256], "antialias": True, "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]},
        "dense_subset_indices": DENSE_INDICES,
        "controls": {"inference": False, "training": False, "protected_data_access": 0},
    }


@app.function(
    image=runtime_image,
    volumes={"/assets": assets},
    gpu="T4",
    cpu=4.0,
    memory=16384,
    timeout=1200,
    retries=0,
)
def qualify(lock: dict) -> bytes:
    import io
    import sys
    import tempfile
    import time
    import zipfile

    import numpy as np
    import torch
    from PIL import Image
    from safetensors.torch import load_file
    from torchvision.transforms import v2

    started = time.perf_counter()
    root = Path("/assets") / MODEL_REVISION
    if _sha(root / "dinov3-source.tar.gz") != lock["source"]["sha256"]:
        raise RuntimeError("SOURCE_SHA256_MISMATCH")
    for name, expected in lock["model_files"].items():
        if _sha(root / "model" / name) != expected:
            raise RuntimeError("MODEL_FILE_SHA256_MISMATCH:" + name)
    source_dirs = [path for path in (root / "source").iterdir() if path.is_dir()]
    if len(source_dirs) != 1:
        raise RuntimeError("SOURCE_DIRECTORY_UNEXPECTED")
    sys.path.insert(0, str(source_dirs[0]))
    from dinov3.hub.backbones import dinov3_vits16

    transform = v2.Compose([
        v2.ToImage(), v2.Resize((256, 256), antialias=True),
        v2.ToDtype(torch.float32, scale=True),
        v2.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ])
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        image_root = out / "images"
        image_root.mkdir()
        tensors = []
        metadata = []
        for item in IMAGES:
            target = image_root / item["file_name"]
            identity = _download(item["url"], target, 2 * 1024 * 1024)
            if identity["sha256"] != item["sha256"]:
                raise RuntimeError("IMAGE_SHA256_MISMATCH:" + item["id"])
            with Image.open(target) as opened:
                image = opened.convert("RGB")
                width, height = image.size
                tensors.append(transform(image))
            metadata.append({**item, "width": width, "height": height})

        model = dinov3_vits16(pretrained=False)
        state = load_file(str(root / "model" / CHECKPOINT), device="cpu")
        incompatible = model.load_state_dict(state, strict=True)
        if incompatible.missing_keys or incompatible.unexpected_keys:
            raise RuntimeError("STRICT_STATE_DICT_LOAD_FAILED")
        model = model.to("cuda:0").eval()
        batch = torch.stack(tensors).to("cuda:0")
        with torch.inference_mode():
            features = model.forward_features(batch)
        global_features = features["x_norm_clstoken"].float().cpu().numpy()
        dense_full = features["x_norm_patchtokens"].float().cpu().numpy()
        if dense_full.shape[1] != 256:
            raise RuntimeError("DENSE_TOKEN_COUNT_UNEXPECTED")
        dense_subset = dense_full[:, DENSE_INDICES, :]
        feature_path = out / "features.npz"
        np.savez_compressed(
            feature_path, global_embeddings=global_features, dense_subset=dense_subset,
            dense_indices=np.asarray(DENSE_INDICES, dtype=np.int64), sample_ids=np.asarray([item["id"] for item in metadata]),
        )
        reloaded = np.load(feature_path)
        reload_exact = (
            np.array_equal(reloaded["global_embeddings"], global_features)
            and np.array_equal(reloaded["dense_subset"], dense_subset)
            and np.array_equal(reloaded["dense_indices"], np.asarray(DENSE_INDICES, dtype=np.int64))
        )
        norms = np.linalg.norm(reloaded["global_embeddings"], axis=1, keepdims=True)
        normalized = reloaded["global_embeddings"] / norms
        similarities = normalized @ normalized.T
        nearest = similarities.argmax(axis=1).tolist()
        self_retrieval = nearest == list(range(len(metadata)))
        report = {
            "schema": "cvrs.rq002.dinov3-vits16-features.v1",
            "status": "PASS_DINOV3_GLOBAL_DENSE_RELOAD_RETRIEVAL" if reload_exact and self_retrieval else "FAIL_DINOV3_FEATURE_QUALIFICATION",
            "assets": lock, "inputs": metadata,
            "features": {"global_shape": list(global_features.shape), "dense_full_shape_observed": list(dense_full.shape), "dense_subset_shape": list(dense_subset.shape), "dense_indices": DENSE_INDICES, "artifact_sha256": _sha(feature_path)},
            "reload": {"exact": reload_exact, "model_rerun": False},
            "retrieval_from_reloaded_artifact": {"cosine_similarity": similarities.tolist(), "nearest_indices": nearest, "self_retrieval": self_retrieval, "model_rerun": False},
            "preprocessing": {"resize": [256, 256], "antialias": True, "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]},
            "environment": {"python": sys.version, "torch": torch.__version__, "device": torch.cuda.get_device_name(0), "dinov3_source_revision": SOURCE_REVISION},
            "controls": {"training": False, "optimizer_steps": 0, "protected_data_access": 0, "sealed_test_access": 0, "gpu_concurrency": 1, "automatic_paid_retry": False, "model_substitution": False},
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
