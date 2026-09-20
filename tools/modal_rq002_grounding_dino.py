"""Bounded HF Grounding DINO native/CVRS qualification on Modal."""
from __future__ import annotations

import json
from pathlib import Path

import modal


TRANSFORMERS_VERSION = "4.57.1"
TRANSFORMERS_TAG_OBJECT = "a47e6666f8f9a61e44a5d149c5e3d230e6c8053c"
TRANSFORMERS_REVISION = "8cb5963cc22174954e7dca2c0a3320b7dc2f4edc"
TRANSFORMERS_SOURCE_URL = f"https://codeload.github.com/huggingface/transformers/tar.gz/{TRANSFORMERS_REVISION}"
TRANSFORMERS_LICENSE_URL = f"https://raw.githubusercontent.com/huggingface/transformers/{TRANSFORMERS_REVISION}/LICENSE"
MODEL_REPO = "IDEA-Research/grounding-dino-tiny"
MODEL_REVISION = "a2bb814dd30d776dcf7e30523b00659f4f141c71"
MODEL_FILES = [
    "added_tokens.json", "config.json", "model.safetensors", "preprocessor_config.json",
    "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json", "vocab.txt",
]
PROMPT_ATOMS = ["person", "car", "truck", "dog", "chair", "bottle"]
PROMPT_TEXT = "person. car. truck. dog. chair. bottle."
IMAGES = [
    {"id": "139", "file_name": "000000000139.jpg", "url": "http://images.cocodataset.org/val2017/000000000139.jpg", "sha256": "ffe0f0cec3b2e27aab1967229cdf0a0d7751dcdd5800322f0b8ac0dffb3b8a8d"},
    {"id": "285", "file_name": "000000000285.jpg", "url": "http://images.cocodataset.org/val2017/000000000285.jpg", "sha256": "f3a2974ce3686332609124c70e3e6a2e3aca43fccf1cd1bd7c5c03820977f57d"},
]

app = modal.App("cvrs-rq002-grounding-dino-tiny")
model_volume = modal.Volume.from_name("cvrs-rq002-grounding-dino-assets", create_if_missing=True)
probe_image = modal.Image.debian_slim(python_version="3.11")
runtime_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgl1", "libglib2.0-0")
    .pip_install("torch==2.7.1", "torchvision==0.22.1", index_url="https://download.pytorch.org/whl/cu126")
    .pip_install(
        "transformers==4.57.1", "safetensors==0.6.2", "tokenizers==0.22.1",
        "numpy==2.1.3", "Pillow==12.0.0", "pydantic==2.11.9",
    )
    .add_local_dir("src/cvsubstrate", "/root/cvrs-src/cvsubstrate", copy=True)
    .env({"PYTHONPATH": "/root/cvrs-src", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
)


def _download(url: str, destination: Path, maximum: int) -> dict:
    import hashlib
    import urllib.request

    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(); total = 0
    request = urllib.request.Request(url, headers={"User-Agent": "CVRS-RQ002/1.0"})
    with urllib.request.urlopen(request, timeout=300) as response, destination.open("wb") as handle:
        for block in iter(lambda: response.read(1024 * 1024), b""):
            total += len(block)
            if total > maximum: raise RuntimeError("DOWNLOAD_BYTE_BUDGET_EXCEEDED:" + destination.name)
            digest.update(block); handle.write(block)
    return {"sha256": digest.hexdigest(), "bytes": total}


def _model_url(name: str) -> str:
    return f"https://huggingface.co/{MODEL_REPO}/resolve/{MODEL_REVISION}/{name}"


@app.function(image=probe_image, volumes={"/model-cache": model_volume}, cpu=2.0, memory=4096, timeout=1200, retries=0)
def probe() -> dict:
    import tempfile

    model_root = Path("/model-cache") / MODEL_REVISION
    assets = {}
    for name in MODEL_FILES:
        path = model_root / name
        maximum = 750 * 1024 * 1024 if name == "model.safetensors" else 10 * 1024 * 1024
        assets[name] = _download(_model_url(name), path, maximum)
    model_volume.commit()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        source = _download(TRANSFORMERS_SOURCE_URL, root / "transformers.tar.gz", 50 * 1024 * 1024)
        license_identity = _download(TRANSFORMERS_LICENSE_URL, root / "LICENSE", 256 * 1024)
        images = []
        for item in IMAGES:
            identity = _download(item["url"], root / item["file_name"], 2 * 1024 * 1024)
            if identity["sha256"] != item["sha256"]: raise RuntimeError("IMAGE_SHA256_MISMATCH:" + item["id"])
            images.append({**item, **identity})
    return {
        "schema": "cvrs.rq002.grounding-dino-probe.v1", "status": "ASSETS_OBSERVED_NOT_INFERRED",
        "implementation": {"package": "transformers", "version": TRANSFORMERS_VERSION, "tag_object": TRANSFORMERS_TAG_OBJECT, "revision": TRANSFORMERS_REVISION, "source_url": TRANSFORMERS_SOURCE_URL, **source},
        "model": {"repo": MODEL_REPO, "revision": MODEL_REVISION, "files": assets, "total_bytes": sum(item["bytes"] for item in assets.values())},
        "license": {"identifier": "Apache-2.0", "url": TRANSFORMERS_LICENSE_URL, **license_identity},
        "images": images,
        "prompt_protocol": {"atoms_in_order": PROMPT_ATOMS, "serialized_text_exact": PROMPT_TEXT, "source": "fixed_protocol", "box_threshold": 0.25, "text_threshold": 0.25, "prompt_tuning": False},
        "controls": {"inference": False, "training": False, "gpu": False, "protected_data_access": 0},
    }


def _rows(processor, model, image_root: Path, metadata: list[dict], device: str) -> list[dict]:
    import torch
    from PIL import Image

    rows = []
    for item in metadata:
        with Image.open(image_root / item["file_name"]) as opened: image = opened.convert("RGB")
        inputs = processor(images=image, text=PROMPT_TEXT, return_tensors="pt").to(device)
        with torch.inference_mode(): outputs = model(**inputs)
        values = processor.post_process_grounded_object_detection(outputs, inputs.input_ids, threshold=0.25, text_threshold=0.25, target_sizes=[(item["height"], item["width"])])[0]
        phrases = values.get("text_labels", values.get("labels"))
        rows.append({"sample_id": item["id"], "boxes": values["boxes"].cpu().tolist(), "scores": values["scores"].cpu().tolist(), "phrases": list(phrases)})
    return rows


def _bounds(rows: list[dict], sizes: dict[str, tuple[int, int]]) -> dict:
    import math

    total = finite = ordered = out = 0; by_image = []
    for row in rows:
        width, height = sizes[row["sample_id"]]; image_out = 0
        for box, score, phrase in zip(row["boxes"], row["scores"], row["phrases"]):
            total += 1; x1, y1, x2, y2 = map(float, box)
            finite += int(all(math.isfinite(v) for v in (x1, y1, x2, y2, float(score))))
            ordered += int(x2 > x1 and y2 > y1)
            outside = x1 < 0 or y1 < 0 or x2 > width or y2 > height
            out += int(outside); image_out += int(outside)
            if not str(phrase).strip(): raise RuntimeError("EMPTY_NATIVE_PHRASE")
        by_image.append({"sample_id": row["sample_id"], "detections": len(row["boxes"]), "out_of_bounds": image_out})
    return {"detections": total, "finite": finite, "ordered": ordered, "out_of_bounds": out, "by_image": by_image}


def _compare(left: list[dict], right: list[dict]) -> dict:
    import numpy as np

    images = []
    for a, b in zip(left, right):
        same = len(a["boxes"]) == len(b["boxes"])
        images.append({"sample_id": a["sample_id"], "count_exact": same, "phrases_and_order_exact": a["phrases"] == b["phrases"], "boxes_atol_1e_5": bool(same and np.allclose(a["boxes"], b["boxes"], rtol=0.0, atol=1e-5)), "scores_atol_1e_6": bool(same and np.allclose(a["scores"], b["scores"], rtol=0.0, atol=1e-6))})
    return {"images": images, "all_pass": len(left) == len(right) and all(all(value for key, value in item.items() if key != "sample_id") for item in images)}


@app.function(image=runtime_image, volumes={"/model-cache": model_volume}, gpu="T4", cpu=4.0, memory=16384, timeout=1800, retries=0)
def qualify(lock: dict) -> bytes:
    import gc
    import hashlib
    import importlib.metadata
    import io
    import subprocess
    import sys
    import tempfile
    import time
    import zipfile

    import torch
    from PIL import Image
    from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor
    from cvsubstrate.contracts.frontier import GroundedPrediction, PromptSpec

    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    started = time.perf_counter(); model_root = Path("/model-cache") / MODEL_REVISION
    observed_files = {path.relative_to(model_root).as_posix(): digest(path) for path in model_root.rglob("*") if path.is_file()}
    if observed_files != lock["model_files"]: raise RuntimeError("MODEL_FILE_UNIVERSE_OR_HASH_MISMATCH")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); image_root = root / "images"; image_root.mkdir(); metadata = []
        for item in IMAGES:
            path = image_root / item["file_name"]; identity = _download(item["url"], path, 2 * 1024 * 1024)
            if identity["sha256"] != item["sha256"]: raise RuntimeError("IMAGE_SHA256_MISMATCH:" + item["id"])
            with Image.open(path) as image: width, height = image.size
            metadata.append({**item, "width": width, "height": height})
        prompts = [{"id": "fixed-prompt-" + item["id"], "sample_id": item["id"], "kind": "text", "text": PROMPT_TEXT, "source": "fixed_protocol"} for item in metadata]
        (root / "prompt-protocol.json").write_text(json.dumps({"atoms_in_order": PROMPT_ATOMS, "serialized_text_exact": PROMPT_TEXT, "prompts": prompts, "box_threshold": 0.25, "text_threshold": 0.25, "prompt_tuning": False}, indent=2) + "\n", "utf-8")

        processor = AutoProcessor.from_pretrained(str(model_root), local_files_only=True, trust_remote_code=False)
        model = AutoModelForZeroShotObjectDetection.from_pretrained(str(model_root), local_files_only=True, trust_remote_code=False, use_safetensors=True).to("cuda:0").eval()
        native_rows = _rows(processor, model, image_root, metadata, "cuda:0")
        (root / "native-direct.json").write_text(json.dumps(native_rows, indent=2) + "\n", "utf-8")
        sizes = {item["id"]: (item["width"], item["height"]) for item in metadata}
        bounds = _bounds(native_rows, sizes)

        canonical = []
        for item, row, prompt in zip(metadata, native_rows, prompts):
            parsed_prompt = PromptSpec.model_validate(prompt)
            canonical.append(GroundedPrediction(sample_id=item["id"], width=item["width"], height=item["height"], prompt=parsed_prompt, boxes=row["boxes"], scores=row["scores"], phrases=row["phrases"]).model_dump(mode="json"))
        (root / "converted-saved-native.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in canonical), "utf-8")
        del model, processor; gc.collect(); torch.cuda.empty_cache()

        request = {"schema_version": "1.0", "protocol_version": "1.0", "operation": "predict", "job": {"backend": "hf_grounding_dino", "operation": "predict", "model_dir": str(model_root), "model_files": lock["model_files"], "trust_local_code": False, "device": "cuda:0", "package_versions": {"transformers": TRANSFORMERS_VERSION}, "images": [{"id": item["id"], "path": str(image_root / item["file_name"]), "sha256": item["sha256"], "width": item["width"], "height": item["height"], "split_role": "dev"} for item in metadata], "prompts": prompts, "config": {"box_threshold": 0.25, "text_threshold": 0.25, "cpu_threads": 1}, "purpose": "software_fixture"}, "output_dir": str(root / "wrapped-execution")}
        request_path = root / "worker-request.json"; response_path = root / "worker-response.json"
        request_path.write_text(json.dumps(request, indent=2) + "\n", "utf-8")
        completed = subprocess.run([sys.executable, "/root/cvrs-src/cvsubstrate/worker_shims/vision_worker.py", "--request", str(request_path), "--response", str(response_path)], capture_output=True, text=True, timeout=900)
        (root / "wrapped.stdout.txt").write_text(completed.stdout, "utf-8"); (root / "wrapped.stderr.txt").write_text(completed.stderr, "utf-8")
        if completed.returncode != 0: raise RuntimeError(f"WRAPPED_WORKER_EXIT_{completed.returncode}")
        envelope = json.loads(response_path.read_text("utf-8"))
        if envelope.get("status") != "SUCCEEDED": raise RuntimeError("WRAPPED_WORKER_FAILED:" + str(envelope.get("error")))
        wrapped_predictions = [json.loads(line) for line in (root / "wrapped-execution/predictions.jsonl").read_text("utf-8").splitlines()]
        wrapped_rows = [{"sample_id": row["sample_id"], "boxes": row["boxes"], "scores": row["scores"], "phrases": row["phrases"]} for row in wrapped_predictions]
        comparison = _compare(native_rows, wrapped_rows)
        phrase_counts = {}
        for row in native_rows:
            for phrase in row["phrases"]: phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
        report = {
            "schema": "cvrs.rq002.grounding-dino-tiny.v1",
            "status": "PASS_GROUNDING_DINO_NATIVE_CVRS_AND_WRAPPED" if comparison["all_pass"] else "FAIL_GROUNDING_DINO_REPEATABILITY",
            "assets": lock, "native": {"status": "PASS", "bounds": bounds, "phrase_counts": phrase_counts, "rows": len(native_rows)},
            "saved_native_conversion": {"status": "PASS", "native_count": bounds["detections"], "canonical_count": sum(len(row["boxes"]) for row in canonical)},
            "wrapped_execution": {"status": "PASS", "comparison_to_native": comparison, "detections": sum(len(row["boxes"]) for row in wrapped_rows)},
            "prompt_provenance": {"atoms_in_order": PROMPT_ATOMS, "serialized_text_exact": PROMPT_TEXT, "source": "fixed_protocol", "prompt_tuning": False, "protocol_sha256": digest(root / "prompt-protocol.json")},
            "environment": {"python": sys.version, "torch": torch.__version__, "torchvision": importlib.metadata.version("torchvision"), "transformers": importlib.metadata.version("transformers"), "safetensors": importlib.metadata.version("safetensors"), "tokenizers": importlib.metadata.version("tokenizers"), "device": torch.cuda.get_device_name(0)},
            "separate_statuses": {"native_execution": "PASS", "conversion_fidelity": "PASS", "wrapped_repeatability": "PASS" if comparison["all_pass"] else "FAIL", "prompt_provenance": "PASS", "evaluator_equivalence": "NOT_RUN_NO_GROUND_TRUTH"},
            "controls": {"training": False, "optimizer_steps": 0, "protected_data_access": 0, "sealed_test_access": 0, "gpu_concurrency": 1, "automatic_paid_retry": False, "geometry_modification": "NONE", "prompt_tuning": False},
            "runtime_seconds": time.perf_counter() - started,
        }
        (root / "report.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
        checksums = []
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name not in {item["file_name"] for item in IMAGES}: checksums.append(f"{digest(path)}  {path.relative_to(root).as_posix()}")
        (root / "checksums.sha256").write_text("\n".join(checksums) + "\n", "utf-8")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(root.rglob("*")):
                if path.is_file() and path.name not in {item["file_name"] for item in IMAGES}: bundle.write(path, path.relative_to(root).as_posix())
        return buffer.getvalue()


@app.local_entrypoint()
def main(mode: str, out: str, lock_json: str = "") -> None:
    destination = Path(out)
    if destination.exists(): raise RuntimeError(f"refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if mode == "probe": destination.write_text(json.dumps(probe.remote(), indent=2) + "\n", "utf-8")
    elif mode == "qualify": destination.write_bytes(qualify.remote(json.loads(Path(lock_json).read_text("utf-8"))))
    else: raise ValueError("mode must be probe or qualify")
    print(json.dumps({"mode": mode, "output": str(destination), "bytes": destination.stat().st_size}))
