"""Bounded official SAM 3 spatial-prompt qualification on Modal."""
from __future__ import annotations

import json
from pathlib import Path

import modal


SOURCE_REVISION = "2345a4ad109ac29c569da749c91d84f10dc08c40"
SOURCE_URL = f"https://codeload.github.com/facebookresearch/sam3/tar.gz/{SOURCE_REVISION}"
MODEL_REPO = "facebook/sam3"
MODEL_REVISION = "3c879f39826c281e95690f02c7821c4de09afae7"
CHECKPOINT = "sam3.pt"
EXPECTED_CHECKPOINT_SHA256 = "9999e2341ceef5e136daa386eecb55cb414446a00ac2b55eb2dfd2f7c3cf8c9e"
MODEL_FILES = ["sam3.pt", "config.json", "README.md"]
SECRET_NAME = "cvrs-huggingface-read"
IMAGES = [
    {"id": "139", "file_name": "000000000139.jpg", "url": "http://images.cocodataset.org/val2017/000000000139.jpg", "sha256": "ffe0f0cec3b2e27aab1967229cdf0a0d7751dcdd5800322f0b8ac0dffb3b8a8d"},
    {"id": "285", "file_name": "000000000285.jpg", "url": "http://images.cocodataset.org/val2017/000000000285.jpg", "sha256": "f3a2974ce3686332609124c70e3e6a2e3aca43fccf1cd1bd7c5c03820977f57d"},
]

app = modal.App("cvrs-rq002-sam3-spatial")
assets = modal.Volume.from_name("cvrs-rq002-sam3-assets", create_if_missing=True)
hf_secret = modal.Secret.from_name(SECRET_NAME)
probe_image = modal.Image.debian_slim(python_version="3.12").pip_install("huggingface_hub==0.36.0")
runtime_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("libgl1", "libglib2.0-0")
    .pip_install("torch==2.7.1", "torchvision==0.22.1", index_url="https://download.pytorch.org/whl/cu126")
    .pip_install(
        "timm==1.0.20", "numpy==1.26.4", "Pillow==12.0.0", "tqdm==4.67.1",
        "ftfy==6.1.1", "regex==2025.9.18", "iopath==0.1.10",
        "huggingface_hub==0.36.0", "pydantic==2.11.9", "safetensors==0.6.2",
    )
    .add_local_dir("src/cvsubstrate", "/root/cvrs-src/cvsubstrate", copy=True)
    .env({"PYTHONPATH": "/root/cvrs-src", "HF_HUB_OFFLINE": "1"})
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
    timeout=1800,
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
        source_archive = temp / "sam3-source.tar.gz"
        source_identity = _download(SOURCE_URL, source_archive, 50 * 1024 * 1024)
        if source_root.exists():
            shutil.rmtree(source_root)
        source_root.mkdir(parents=True)
        with tarfile.open(source_archive, "r:gz") as archive:
            archive.extractall(source_root, filter="data")
        extracted = [path for path in source_root.iterdir() if path.is_dir()]
        if len(extracted) != 1:
            raise RuntimeError("SOURCE_ARCHIVE_LAYOUT_UNEXPECTED")
        (root / "sam3-source.tar.gz").write_bytes(source_archive.read_bytes())

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
        "schema": "cvrs.rq002.sam3-acquisition.v1",
        "status": "PASS_AUTHENTICATED_ACCESS_AND_FROZEN_ASSETS",
        "authenticated_access": True,
        "credential_recorded": False,
        "source": {"repo": "facebookresearch/sam3", "revision": SOURCE_REVISION, **source_identity},
        "model": {"repo": MODEL_REPO, "revision": MODEL_REVISION, "files": observed},
        "controls": {"inference": False, "training": False, "protected_data_access": 0},
    }


@app.function(
    image=runtime_image,
    volumes={"/assets": assets},
    gpu="A10G",
    cpu=4.0,
    memory=32768,
    timeout=1800,
    retries=0,
)
def qualify(lock: dict, selection: dict) -> bytes:
    import io
    import math
    import sys
    import tempfile
    import time
    import zipfile

    import numpy as np
    import torch
    from PIL import Image

    started = time.perf_counter()
    root = Path("/assets") / MODEL_REVISION
    if _sha(root / "sam3-source.tar.gz") != lock["source"]["sha256"]:
        raise RuntimeError("SOURCE_SHA256_MISMATCH")
    for name, expected in lock["model_files"].items():
        if _sha(root / "model" / name) != expected:
            raise RuntimeError("MODEL_FILE_SHA256_MISMATCH:" + name)
    source_dirs = [path for path in (root / "source").iterdir() if path.is_dir()]
    if len(source_dirs) != 1:
        raise RuntimeError("SOURCE_DIRECTORY_UNEXPECTED")
    sys.path.insert(0, str(source_dirs[0]))
    from sam3.model.sam3_image_processor import Sam3Processor
    from sam3.model_builder import build_sam3_image_model
    from cvsubstrate.contracts.frontier import MaskInstance, MaskPrediction, PromptSpec
    from cvsubstrate.vision.masks import encode_mask

    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        image_root = out / "images"
        native_root = out / "native"
        image_root.mkdir(); native_root.mkdir()
        metadata = []
        for item in IMAGES:
            target = image_root / item["file_name"]
            identity = _download(item["url"], target, 2 * 1024 * 1024)
            if identity["sha256"] != item["sha256"]:
                raise RuntimeError("IMAGE_SHA256_MISMATCH:" + item["id"])
            with Image.open(target) as image:
                width, height = image.size
            metadata.append({**item, "width": width, "height": height})

        model = build_sam3_image_model(
            device="cuda", eval_mode=True, checkpoint_path=str(root / "model" / CHECKPOINT),
            load_from_HF=False, enable_segmentation=True, enable_inst_interactivity=False,
        )
        processor = Sam3Processor(model, device="cuda", confidence_threshold=0.5)
        canonical_rows = []
        lineage = []
        total_masks = 0
        for item in metadata:
            with Image.open(image_root / item["file_name"]) as opened:
                image = opened.convert("RGB")
            state = processor.set_image(image)
            prompts = []
            instances = []
            image_selection = [row for row in selection["prompts"] if row["sample_id"] == item["id"]]
            for row in image_selection:
                raw_box = [float(v) for v in row["box_xyxy"]]
                x1, y1, x2, y2 = raw_box
                if not all(math.isfinite(v) for v in raw_box) or x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1 or x2 > item["width"] or y2 > item["height"]:
                    raise RuntimeError("STRICT_PROMPT_BOX_VALIDATION_FAILED:" + row["prompt_id"])
                normalized = [
                    ((x1 + x2) / 2.0) / item["width"],
                    ((y1 + y2) / 2.0) / item["height"],
                    (x2 - x1) / item["width"],
                    (y2 - y1) / item["height"],
                ]
                prompt = PromptSpec(
                    id=row["prompt_id"], sample_id=item["id"], kind="box", box=raw_box,
                    source="upstream_model", source_artifact_sha256=row["source_artifact_sha256"],
                )
                prompts.append(prompt)
                processor.reset_all_prompts(state)
                result = processor.add_geometric_prompt(normalized, True, state)
                masks = result["masks"].detach().cpu().numpy().astype(bool)
                scores = result["scores"].detach().cpu().numpy().astype(np.float32)
                boxes = result["boxes"].detach().cpu().numpy().astype(np.float32)
                native_path = native_root / f'{row["prompt_id"]}.npz'
                np.savez_compressed(native_path, masks=masks, scores=scores, boxes=boxes)
                native_sha = _sha(native_path)
                if masks.ndim == 4 and masks.shape[1] == 1:
                    masks = masks[:, 0]
                if masks.ndim != 3 or masks.shape[1:] != (item["height"], item["width"]):
                    raise RuntimeError("NATIVE_MASK_SHAPE_MISMATCH:" + row["prompt_id"])
                for index, (mask, score) in enumerate(zip(masks, scores)):
                    instances.append(MaskInstance(
                        id=f'{row["prompt_id"]}-mask-{index}', mask=encode_mask(mask),
                        score=float(score), score_kind="native_quality", prompt_id=row["prompt_id"],
                    ))
                total_masks += len(masks)
                lineage.append({
                    **row, "box_transform_for_documented_api": "xyxy_pixels_to_normalized_cxcywh",
                    "normalized_cxcywh": normalized, "geometry_clipped_or_rewritten": False,
                    "native_output_sha256": native_sha, "native_masks": len(masks),
                })
            canonical_rows.append(MaskPrediction(
                sample_id=item["id"], width=item["width"], height=item["height"],
                instances=instances, prompts=prompts, selection_policy="all_candidates",
            ).model_dump(mode="json"))

        (out / "selection.json").write_text(json.dumps(selection, indent=2) + "\n", "utf-8")
        (out / "lineage.json").write_text(json.dumps(lineage, indent=2) + "\n", "utf-8")
        (out / "predictions.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in canonical_rows), "utf-8")
        report = {
            "schema": "cvrs.rq002.sam3-spatial.v1",
            "status": "PASS_SAM3_SPATIAL_PROMPT_CVRS_COMPOSITION" if total_masks > 0 else "FAIL_SAM3_ZERO_NATIVE_MASKS",
            "assets": lock, "inputs": metadata,
            "selection": {"policy": selection["policy"], "prompts": len(selection["prompts"]), "source_artifacts": selection["source_artifacts"]},
            "native": {"prompts_executed": len(lineage), "masks": total_masks, "confidence_threshold": 0.5},
            "cvrs": {"mask_predictions": len(canonical_rows), "instances": sum(len(row["instances"]) for row in canonical_rows), "contract_validation": "PASS"},
            "lineage": {"complete": len(lineage) == len(selection["prompts"]), "path": "prompt -> detached detector box -> explicit API coordinate transform -> native mask -> CVRS RLE"},
            "controls": {"training": False, "optimizer_steps": 0, "protected_data_access": 0, "sealed_test_access": 0, "gpu_concurrency": 1, "automatic_paid_retry": False, "geometry_clipping": False, "model_substitution": False},
            "environment": {"python": sys.version, "torch": torch.__version__, "device": torch.cuda.get_device_name(0), "sam3_source_revision": SOURCE_REVISION},
            "runtime_seconds": time.perf_counter() - started,
        }
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
        checksums = []
        for path in sorted(out.rglob("*")):
            if path.is_file() and path.name not in {item["file_name"] for item in IMAGES}:
                checksums.append(f"{_sha(path)}  {path.relative_to(out).as_posix()}")
        (out / "checksums.sha256").write_text("\n".join(checksums) + "\n", "utf-8")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(out.rglob("*")):
                if path.is_file() and path.name not in {item["file_name"] for item in IMAGES}:
                    bundle.write(path, path.relative_to(out).as_posix())
        return buffer.getvalue()


@app.local_entrypoint()
def main(mode: str, out: str, lock_json: str = "", selection_json: str = "") -> None:
    destination = Path(out)
    if destination.exists():
        raise RuntimeError(f"refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if mode == "acquire":
        destination.write_text(json.dumps(acquire.remote(), indent=2) + "\n", "utf-8")
    elif mode == "qualify":
        lock = json.loads(Path(lock_json).read_text("utf-8"))
        selection = json.loads(Path(selection_json).read_text("utf-8"))
        destination.write_bytes(qualify.remote(lock, selection))
    else:
        raise ValueError("mode must be acquire or qualify")
    print(json.dumps({"mode": mode, "output": str(destination), "bytes": destination.stat().st_size}))
