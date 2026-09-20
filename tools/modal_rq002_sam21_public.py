"""Bounded public SAM 2.1 Hiera Tiny spatial-prompt fallback on Modal."""
from __future__ import annotations

import json
from pathlib import Path

import modal


SOURCE_REVISION = "2b90b9f5ceec907a1c18123530e92e794ad901a4"
SOURCE_URL = f"https://codeload.github.com/facebookresearch/sam2/tar.gz/{SOURCE_REVISION}"
MODEL_REPO = "facebook/sam2.1-hiera-tiny"
MODEL_REVISION = "de431c4043854a71d8101e17995dfe596bf101a5"
CHECKPOINT = "model.safetensors"
EXPECTED_CHECKPOINT_SHA256 = "48c14467e5cf9e51870511feb72c89688e82dd74523142c0538b663e193ac2a7"
MODEL_FILES = ["model.safetensors", "config.json", "preprocessor_config.json", "processor_config.json"]
IMAGES = [
    {"id": "139", "file_name": "000000000139.jpg", "url": "http://images.cocodataset.org/val2017/000000000139.jpg", "sha256": "ffe0f0cec3b2e27aab1967229cdf0a0d7751dcdd5800322f0b8ac0dffb3b8a8d"},
    {"id": "285", "file_name": "000000000285.jpg", "url": "http://images.cocodataset.org/val2017/000000000285.jpg", "sha256": "f3a2974ce3686332609124c70e3e6a2e3aca43fccf1cd1bd7c5c03820977f57d"},
]

app = modal.App("cvrs-rq002-sam21-public")
assets = modal.Volume.from_name("cvrs-rq002-sam21-public-assets", create_if_missing=True)
probe_image = modal.Image.debian_slim(python_version="3.12").pip_install("huggingface_hub==0.36.0")
runtime_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("libgl1", "libglib2.0-0")
    .pip_install("torch==2.7.1", "torchvision==0.22.1", index_url="https://download.pytorch.org/whl/cu126")
    .pip_install(
        "transformers==4.57.1", "huggingface_hub==0.36.0", "safetensors==0.6.2",
        "numpy==1.26.4", "Pillow==12.0.0", "pydantic==2.11.9",
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
        archive = Path(td) / "sam2-source.tar.gz"
        source_identity = _download(SOURCE_URL, archive, 100 * 1024 * 1024)
        shutil.copyfile(archive, root / "sam2-source.tar.gz")
    assets.commit()
    return {
        "schema": "cvrs.rq002.sam21-public-acquisition.v1",
        "status": "PASS_PUBLIC_UNGATED_FROZEN_ASSETS",
        "source": {"repo": "facebookresearch/sam2", "revision": SOURCE_REVISION, **source_identity},
        "model": {"repo": MODEL_REPO, "revision": MODEL_REVISION, "files": observed},
        "runtime": {"transformers": "4.57.1", "torch": "2.7.1", "python": "3.12"},
        "controls": {"inference": False, "training": False, "protected_data_access": 0, "credentials_used": False},
    }


@app.function(image=runtime_image, volumes={"/assets": assets}, gpu="T4", cpu=4.0, memory=16384, timeout=1200, retries=0)
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
    from transformers import Sam2Model, Sam2Processor
    from cvsubstrate.contracts.frontier import MaskInstance, MaskPrediction, PromptSpec
    from cvsubstrate.vision.masks import encode_mask

    started = time.perf_counter()
    root = Path("/assets") / MODEL_REVISION
    if _sha(root / "sam2-source.tar.gz") != lock["source"]["sha256"]:
        raise RuntimeError("SOURCE_SHA256_MISMATCH")
    for name, expected in lock["model"]["files"].items():
        if _sha(root / "model" / name) != expected["sha256"]:
            raise RuntimeError("MODEL_FILE_SHA256_MISMATCH:" + name)
    model = Sam2Model.from_pretrained(root / "model", local_files_only=True).to("cuda:0").eval()
    processor = Sam2Processor.from_pretrained(root / "model", local_files_only=True)

    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        image_root = out / "images"
        native_root = out / "native"
        image_root.mkdir(); native_root.mkdir()
        canonical_rows = []
        lineage = []
        metadata = []
        for item in IMAGES:
            target = image_root / item["file_name"]
            identity = _download(item["url"], target, 2 * 1024 * 1024)
            if identity["sha256"] != item["sha256"]:
                raise RuntimeError("IMAGE_SHA256_MISMATCH:" + item["id"])
            with Image.open(target) as opened:
                image = opened.convert("RGB")
                width, height = image.size
            rows = [row for row in selection["prompts"] if row["sample_id"] == item["id"]]
            boxes = [[float(value) for value in row["box_xyxy"]] for row in rows]
            for row, box in zip(rows, boxes):
                x1, y1, x2, y2 = box
                if not all(math.isfinite(value) for value in box) or x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1 or x2 > width or y2 > height:
                    raise RuntimeError("STRICT_PROMPT_BOX_VALIDATION_FAILED:" + row["prompt_id"])
            inputs = processor(images=image, input_boxes=[boxes], return_tensors="pt")
            gpu_inputs = {key: value.to("cuda:0") if hasattr(value, "to") else value for key, value in inputs.items() if key not in {"original_sizes", "reshaped_input_sizes"}}
            with torch.inference_mode():
                outputs = model(**gpu_inputs, multimask_output=False)
            masks = processor.post_process_masks(
                outputs.pred_masks.cpu(), inputs["original_sizes"], inputs["reshaped_input_sizes"], binarize=True
            )[0].numpy().astype(bool)
            scores = outputs.iou_scores.detach().cpu().numpy()[0, :, 0].astype(np.float32)
            if masks.ndim == 4 and masks.shape[1] == 1:
                masks = masks[:, 0]
            if masks.shape != (len(rows), height, width) or scores.shape != (len(rows),):
                raise RuntimeError("NATIVE_OUTPUT_SHAPE_MISMATCH:" + item["id"])
            native_path = native_root / f'{item["id"]}.npz'
            np.savez_compressed(native_path, masks=masks, scores=scores, boxes=np.asarray(boxes, dtype=np.float32))
            native_sha = _sha(native_path)
            prompts = []
            instances = []
            for row, box, mask, score in zip(rows, boxes, masks, scores):
                prompt = PromptSpec(id=row["prompt_id"], sample_id=item["id"], kind="box", box=box, source="upstream_model", source_artifact_sha256=row["source_artifact_sha256"])
                prompts.append(prompt)
                instances.append(MaskInstance(id=row["prompt_id"] + "-mask", mask=encode_mask(mask), score=float(score), score_kind="predicted_iou", prompt_id=row["prompt_id"]))
                lineage.append({**row, "geometry_clipped_or_rewritten": False, "native_output_sha256": native_sha, "native_mask_pixels": int(mask.sum()), "predicted_iou": float(score)})
            canonical_rows.append(MaskPrediction(sample_id=item["id"], width=width, height=height, instances=instances, prompts=prompts, selection_policy="single_native_output", native_output_sha256=native_sha).model_dump(mode="json"))
            metadata.append({**item, "width": width, "height": height, "prompts": len(rows)})

        (out / "selection.json").write_text(json.dumps(selection, indent=2) + "\n", "utf-8")
        (out / "lineage.json").write_text(json.dumps(lineage, indent=2) + "\n", "utf-8")
        (out / "predictions.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in canonical_rows), "utf-8")
        report = {
            "schema": "cvrs.rq002.sam21-public-spatial.v1",
            "status": "PASS_SAM21_PUBLIC_SPATIAL_PROMPT_CVRS_COMPOSITION" if len(lineage) == len(selection["prompts"]) else "FAIL_SAM21_LINEAGE_COUNT",
            "claim_boundary": "SAM 2.1 spatial prompting only; not SAM 3 text or concept segmentation",
            "assets": lock, "inputs": metadata,
            "selection": {"policy": selection["policy"], "prompts": len(selection["prompts"]), "source_artifacts": selection["source_artifacts"]},
            "native": {"prompts_executed": len(lineage), "masks": len(lineage), "multimask_output": False},
            "cvrs": {"mask_predictions": len(canonical_rows), "instances": sum(len(row["instances"]) for row in canonical_rows), "contract_validation": "PASS"},
            "lineage": {"complete": len(lineage) == len(selection["prompts"]), "path": "prompt -> detached detector box -> processor coordinate transform -> native SAM2.1 mask -> CVRS RLE"},
            "environment": {"python": sys.version, "torch": torch.__version__, "transformers": "4.57.1", "device": torch.cuda.get_device_name(0)},
            "controls": {"training": False, "optimizer_steps": 0, "protected_data_access": 0, "sealed_test_access": 0, "gpu_concurrency": 1, "automatic_paid_retry": False, "geometry_clipping": False},
            "runtime_seconds": time.perf_counter() - started,
        }
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
        checksums = [f"{_sha(path)}  {path.relative_to(out).as_posix()}" for path in sorted(out.rglob("*")) if path.is_file() and path.name not in {item["file_name"] for item in IMAGES}]
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
        destination.write_bytes(qualify.remote(json.loads(Path(lock_json).read_text("utf-8")), json.loads(Path(selection_json).read_text("utf-8"))))
    else:
        raise ValueError("mode must be acquire or qualify")
    print(json.dumps({"mode": mode, "output": str(destination), "bytes": destination.stat().st_size}))
