"""Bounded MMDeploy 1.3.1 / ONNX Runtime qualification for frozen RTMDet."""
from __future__ import annotations

import json
from pathlib import Path

import modal


MMDEPLOY_REVISION = "bc75c9d6c8940aa03d0e1e5b5962bd930478ba77"
MMDEPLOY_SOURCE_URL = f"https://codeload.github.com/open-mmlab/mmdeploy/tar.gz/{MMDEPLOY_REVISION}"
MMDET_REVISION = "44ebd17b145c2372c4b700bfb9cb20dbd28ab64a"
MMDET_SOURCE_URL = f"https://codeload.github.com/open-mmlab/mmdetection/tar.gz/{MMDET_REVISION}"
DEPLOY_CONFIG_RELATIVE = "configs/mmdet/detection/detection_onnxruntime_static.py"
DEPLOY_ENTRY_RELATIVE = "tools/deploy.py"
MODEL_CONFIG_RELATIVE = "configs/rtmdet/rtmdet_tiny_8xb32-300e_coco.py"
CHECKPOINT_URL = (
    "https://download.openmmlab.com/mmdetection/v3.0/rtmdet/"
    "rtmdet_tiny_8xb32-300e_coco/"
    "rtmdet_tiny_8xb32-300e_coco_20220902_112414-78e30dcc.pth"
)
IMAGE = {
    "id": "139", "file_name": "000000000139.jpg",
    "url": "http://images.cocodataset.org/val2017/000000000139.jpg",
    "sha256": "ffe0f0cec3b2e27aab1967229cdf0a0d7751dcdd5800322f0b8ac0dffb3b8a8d",
}

app = modal.App("cvrs-rq002-mmdeploy131-rtmdet-ort")
probe_image = modal.Image.debian_slim(python_version="3.10")
runtime_image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("libgl1", "libglib2.0-0")
    .pip_install("torch==2.1.2", "torchvision==0.16.2", index_url="https://download.pytorch.org/whl/cu121")
    .pip_install("mmcv==2.1.0", find_links="https://download.openmmlab.com/mmcv/dist/cu121/torch2.1/index.html")
    .pip_install(
        "mmengine==0.10.7", "mmdet==3.3.0", "mmdeploy==1.3.1",
        "onnx==1.15.0", "onnxruntime==1.16.3", "numpy==1.26.4",
        "opencv-python-headless==4.8.1.78", "Pillow==10.4.0",
    )
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
        root = Path(td)
        deploy_archive = root / "mmdeploy.tar.gz"
        deploy_source = _download(MMDEPLOY_SOURCE_URL, deploy_archive, 200 * 1024 * 1024)
        deploy_root = _extract(deploy_archive, root / "mmdeploy")
        mmdet_archive = root / "mmdet.tar.gz"
        mmdet_source = _download(MMDET_SOURCE_URL, mmdet_archive, 100 * 1024 * 1024)
        mmdet_root = _extract(mmdet_archive, root / "mmdet")
        checkpoint = _download(CHECKPOINT_URL, root / "checkpoint.pth", 200 * 1024 * 1024)
        image = _download(IMAGE["url"], root / IMAGE["file_name"], 10 * 1024 * 1024)
        digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
        return {
            "schema": "cvrs.rq002.mmdeploy-probe.v1", "status": "ASSETS_OBSERVED_NOT_EXPORTED",
            "mmdeploy": {"version": "1.3.1", "revision": MMDEPLOY_REVISION, "source_url": MMDEPLOY_SOURCE_URL, **deploy_source},
            "mmdetection": {"version": "3.3.0", "revision": MMDET_REVISION, "source_url": MMDET_SOURCE_URL, **mmdet_source},
            "deploy_entry": {"relative_path": DEPLOY_ENTRY_RELATIVE, "sha256": digest(deploy_root / DEPLOY_ENTRY_RELATIVE)},
            "deploy_config": {"relative_path": DEPLOY_CONFIG_RELATIVE, "sha256": digest(deploy_root / DEPLOY_CONFIG_RELATIVE)},
            "model_config": {"relative_path": MODEL_CONFIG_RELATIVE, "sha256": digest(mmdet_root / MODEL_CONFIG_RELATIVE)},
            "checkpoint": {"url": CHECKPOINT_URL, **checkpoint},
            "image": {**IMAGE, **image},
            "controls": {"export": False, "inference": False, "training": False, "gpu": False, "protected_data_access": 0},
        }


@app.function(image=runtime_image, cpu=8.0, memory=16384, timeout=1800, retries=0)
def qualify(lock: dict) -> bytes:
    import hashlib
    import importlib.metadata
    import io
    import os
    import subprocess
    import sys
    import tempfile
    import time
    import zipfile

    import mmcv
    import mmdeploy
    import mmdet
    import mmengine
    import numpy as np
    import onnx
    import onnxruntime as ort
    import torch
    from mmdeploy.apis.utils import build_task_processor
    from mmdeploy.utils import get_input_shape, load_config

    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        deploy_archive = root / "mmdeploy.tar.gz"
        if _download(MMDEPLOY_SOURCE_URL, deploy_archive, 200 * 1024 * 1024)["sha256"] != lock["mmdeploy_source_sha256"]:
            raise RuntimeError("MMDEPLOY_SOURCE_SHA256_MISMATCH")
        deploy_root = _extract(deploy_archive, root / "mmdeploy")
        mmdet_archive = root / "mmdet.tar.gz"
        if _download(MMDET_SOURCE_URL, mmdet_archive, 100 * 1024 * 1024)["sha256"] != lock["mmdet_source_sha256"]:
            raise RuntimeError("MMDET_SOURCE_SHA256_MISMATCH")
        mmdet_root = _extract(mmdet_archive, root / "mmdet")
        deploy_entry = deploy_root / DEPLOY_ENTRY_RELATIVE
        deploy_config = deploy_root / DEPLOY_CONFIG_RELATIVE
        model_config = mmdet_root / MODEL_CONFIG_RELATIVE
        for path, expected in [
            (deploy_entry, lock["deploy_entry_sha256"]),
            (deploy_config, lock["deploy_config_sha256"]),
            (model_config, lock["model_config_sha256"]),
        ]:
            if digest(path) != expected:
                raise RuntimeError("CONFIG_OR_ENTRY_SHA256_MISMATCH")
        checkpoint = root / "checkpoint.pth"
        if _download(CHECKPOINT_URL, checkpoint, 200 * 1024 * 1024)["sha256"] != lock["checkpoint_sha256"]:
            raise RuntimeError("CHECKPOINT_SHA256_MISMATCH")
        image_path = root / IMAGE["file_name"]
        if _download(IMAGE["url"], image_path, 10 * 1024 * 1024)["sha256"] != lock["image"]["sha256"]:
            raise RuntimeError("IMAGE_SHA256_MISMATCH")

        export_dir = root / "export"
        command = [
            sys.executable, str(deploy_entry), str(deploy_config), str(model_config),
            str(checkpoint), str(image_path), "--work-dir", str(export_dir),
            "--device", "cpu", "--dump-info",
        ]
        environment = dict(os.environ, PYTHONPATH=str(deploy_root) + os.pathsep + str(mmdet_root))
        completed = subprocess.run(command, cwd=deploy_root, env=environment, capture_output=True, text=True, timeout=1500)
        (root / "export.stdout.txt").write_text(completed.stdout, "utf-8")
        (root / "export.stderr.txt").write_text(completed.stderr, "utf-8")
        if completed.returncode != 0:
            raise RuntimeError(f"MMDEPLOY_EXPORT_FAILED_EXIT_{completed.returncode}")
        graphs = sorted(export_dir.rglob("*.onnx"))
        if len(graphs) != 1:
            raise RuntimeError(f"EXPECTED_ONE_ONNX_GRAPH_GOT_{len(graphs)}")
        graph = graphs[0]
        onnx_model = onnx.load(str(graph)); onnx.checker.check_model(onnx_model)

        deploy_cfg, model_cfg = load_config(str(deploy_config), str(model_config))
        task_processor = build_task_processor(model_cfg, deploy_cfg, "cpu")
        model_inputs, _ = task_processor.create_input(str(image_path), get_input_shape(deploy_cfg))
        torch_model = task_processor.build_pytorch_model(str(checkpoint))
        processed = torch_model.data_preprocessor(model_inputs, training=False)
        tensor = processed["inputs"]
        if tensor.ndim == 3:
            tensor = tensor.unsqueeze(0)
        input_array = tensor.detach().cpu().numpy().astype(np.float32, copy=False)
        runtime_error = None; outputs_1 = []; output_names = []; repeatability = []
        session = ort.InferenceSession(str(graph), providers=["CPUExecutionProvider"])
        input_name = session.get_inputs()[0].name
        try:
            outputs_1 = session.run(None, {input_name: input_array})
            outputs_2 = session.run(None, {input_name: input_array})
            output_names = [item.name for item in session.get_outputs()]
            repeatability = [bool(np.array_equal(a, b)) for a, b in zip(outputs_1, outputs_2)]
            np.savez_compressed(root / "onnxruntime-outputs.npz", **dict(zip(output_names, outputs_1)))
        except Exception as exc:
            runtime_error = f"{type(exc).__name__}: {exc}"
        np.save(root / "onnxruntime-input.npy", input_array, allow_pickle=False)
        raw = {
            name: {"shape": list(value.shape), "dtype": str(value.dtype), "finite": bool(np.isfinite(value).all())}
            for name, value in zip(output_names, outputs_1)
        }
        runtime_pass = runtime_error is None and bool(repeatability) and all(repeatability)
        report = {
            "schema": "cvrs.rq002.mmdeploy-rtmdet-ort.v1",
            "status": "PASS_MMDEPLOY_EXPORT_AND_ORT_PENDING_FIDELITY" if runtime_pass else "FAIL_MMDEPLOY_ORT_RUNTIME",
            "assets": lock,
            "export": {"onnx_sha256": digest(graph), "onnx_bytes": graph.stat().st_size, "onnx_checker": "PASS", "command": command},
            "onnxruntime": {"version": ort.__version__, "provider": "CPUExecutionProvider", "input_name": input_name, "input_shape": list(input_array.shape), "input_dtype": str(input_array.dtype), "outputs": raw, "repeatability_exact": repeatability, "error": runtime_error},
            "environment": {"python": sys.version, "torch": torch.__version__, "mmcv": mmcv.__version__, "mmengine": mmengine.__version__, "mmdet": mmdet.__version__, "mmdeploy": mmdeploy.__version__, "onnx": onnx.__version__, "onnxruntime": ort.__version__, "numpy": np.__version__, "torchvision": importlib.metadata.version("torchvision"), "device": "cpu"},
            "separate_statuses": {"export": "PASS", "transport_fidelity": "PENDING_LOCAL_COMPARISON_TO_PRESERVED_NATIVE" if runtime_pass else "NOT_RUN_RUNTIME_FAILURE", "conversion_fidelity": "PENDING_LOCAL_STRICT_VALIDATION" if runtime_pass else "NOT_RUN_RUNTIME_FAILURE", "runtime_repeatability": "PASS_EXACT" if runtime_pass else "FAIL", "evaluator_equivalence": "NOT_RUN_NO_GROUND_TRUTH"},
            "controls": {"training": False, "optimizer_steps": 0, "native_gpu_inference_rerun": False, "protected_data_access": 0, "sealed_test_access": 0, "gpu_concurrency": 0, "geometry_modification": "NONE"},
            "runtime_seconds": time.perf_counter() - started,
        }
        (root / "report.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
        checksums = []
        excluded = {"checkpoint.pth", "mmdeploy.tar.gz", "mmdet.tar.gz", IMAGE["file_name"]}
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(root)
            if path.is_file() and path.name not in excluded and not ({"mmdeploy", "mmdet"} & set(rel.parts)):
                checksums.append(f"{digest(path)}  {rel.as_posix()}")
        (root / "checksums.sha256").write_text("\n".join(checksums) + "\n", "utf-8")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(root.rglob("*")):
                rel = path.relative_to(root)
                if path.is_file() and path.name not in excluded and not ({"mmdeploy", "mmdet"} & set(rel.parts)):
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
