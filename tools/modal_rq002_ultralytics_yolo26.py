"""Bounded Ultralytics YOLO26n native/CVRS/ONNX qualification on Modal."""
from __future__ import annotations

import json
from pathlib import Path

import modal


VERSION = "8.4.0"
TAG_OBJECT = "6f6158be448c73471c000cf41db5cd9169300ed9"
REVISION = "f2d3aed634a5b0e4828024718d4a61ab2f83fb19"
SOURCE_URL = f"https://codeload.github.com/ultralytics/ultralytics/tar.gz/{REVISION}"
LICENSE_URL = f"https://raw.githubusercontent.com/ultralytics/ultralytics/{REVISION}/LICENSE"
CHECKPOINT_URL = "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt"
CONFIG_RELATIVE = "ultralytics/cfg/models/26/yolo26.yaml"
IMAGES = [
    {"id": "139", "file_name": "000000000139.jpg", "url": "http://images.cocodataset.org/val2017/000000000139.jpg", "sha256": "ffe0f0cec3b2e27aab1967229cdf0a0d7751dcdd5800322f0b8ac0dffb3b8a8d"},
    {"id": "285", "file_name": "000000000285.jpg", "url": "http://images.cocodataset.org/val2017/000000000285.jpg", "sha256": "f3a2974ce3686332609124c70e3e6a2e3aca43fccf1cd1bd7c5c03820977f57d"},
]

app = modal.App("cvrs-rq002-ultralytics-yolo26n")
probe_image = modal.Image.debian_slim(python_version="3.11")
runtime_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgl1", "libglib2.0-0")
    .pip_install("torch==2.7.1", "torchvision==0.22.1", index_url="https://download.pytorch.org/whl/cu126")
    .pip_install(
        "ultralytics==8.4.0", "onnx==1.19.1", "onnxruntime==1.23.2",
        "numpy==2.1.3", "opencv-python-headless==4.11.0.86", "pydantic==2.11.9",
    )
    .add_local_dir("src/cvsubstrate", "/root/cvrs-src/cvsubstrate", copy=True)
    .add_local_file(
        "qualification/inputs/coco2017-val-128-official-http/annotations/instances_val2017_subset.json",
        "/root/inputs/instances_val2017_subset.json",
        copy=True,
    )
    .env({"PYTHONPATH": "/root/cvrs-src", "ULTRALYTICS_OFFLINE": "true"})
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
        checkpoint = _download(CHECKPOINT_URL, root / "yolo26n.pt", 100 * 1024 * 1024)
        license_identity = _download(LICENSE_URL, root / "LICENSE", 256 * 1024)
        images = []
        for item in IMAGES:
            identity = _download(item["url"], root / item["file_name"], 2 * 1024 * 1024)
            if identity["sha256"] != item["sha256"]:
                raise RuntimeError("IMAGE_SHA256_MISMATCH:" + item["id"])
            images.append({**item, **identity})
        return {
            "schema": "cvrs.rq002.ultralytics-yolo26n-probe.v1",
            "status": "ASSETS_OBSERVED_NOT_INFERRED",
            "source": {"version": VERSION, "tag_object": TAG_OBJECT, "revision": REVISION, "url": SOURCE_URL, **source},
            "config": {"relative_path": CONFIG_RELATIVE, "sha256": hashlib.sha256(config.read_bytes()).hexdigest()},
            "checkpoint": {"url": CHECKPOINT_URL, **checkpoint},
            "license": {"identifier": "AGPL-3.0", "url": LICENSE_URL, **license_identity},
            "images": images,
            "controls": {"inference": False, "export": False, "training": False, "gpu": False, "protected_data_access": 0},
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
        for value in row["boxes"]:
            total += 1
            x1, y1, x2, y2 = map(float, value)
            finite += int(all(math.isfinite(v) for v in (x1, y1, x2, y2)))
            ordered += int(x2 >= x1 and y2 >= y1)
            flags = [x1 < 0, y1 < 0, x2 > width, y2 > height]
            out += int(any(flags)); image_out += int(any(flags))
            for key, flag in zip(reasons, flags): reasons[key] += int(flag)
            maxima["left"] = max(maxima["left"], max(0.0, -x1))
            maxima["top"] = max(maxima["top"], max(0.0, -y1))
            maxima["right"] = max(maxima["right"], max(0.0, x2 - width))
            maxima["bottom"] = max(maxima["bottom"], max(0.0, y2 - height))
        by_image.append({"sample_id": row["sample_id"], "detections": len(row["boxes"]), "out_of_bounds": image_out})
    return {"detections": total, "finite": finite, "ordered": ordered, "out_of_bounds": out, "out_of_bounds_fraction": out / total if total else 0.0, "reason_counts": reasons, "maximum_excess_pixels": maxima, "by_image": by_image}


def _compare(left: list[dict], right: list[dict]) -> dict:
    import numpy as np

    outcomes = []
    for a, b in zip(left, right):
        same_shape = len(a["boxes"]) == len(b["boxes"])
        outcomes.append({
            "sample_id": a["sample_id"],
            "count_left": len(a["boxes"]), "count_right": len(b["boxes"]),
            "labels_and_order_exact": a["labels"] == b["labels"],
            "boxes_atol_1e_5": bool(same_shape and np.allclose(a["boxes"], b["boxes"], rtol=0.0, atol=1e-5)),
            "scores_atol_1e_6": bool(same_shape and np.allclose(a["scores"], b["scores"], rtol=0.0, atol=1e-6)),
        })
    return {"images": outcomes, "all_pass": len(left) == len(right) and all(all(v for k, v in item.items() if k.endswith("exact") or k.startswith("boxes_") or k.startswith("scores_")) for item in outcomes)}


@app.function(image=runtime_image, gpu="T4", cpu=4.0, memory=12288, timeout=1800, retries=0)
def qualify(lock: dict) -> bytes:
    import contextlib
    import hashlib
    import importlib.metadata
    import io
    import subprocess
    import sys
    import tempfile
    import time
    import traceback
    import zipfile

    import cv2
    import numpy as np
    import onnx
    import onnxruntime as ort
    import torch
    import ultralytics
    from PIL import Image
    from ultralytics import YOLO
    from ultralytics.data.augment import LetterBox

    from cvsubstrate.evaluation.converters import convert_results

    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        errors = {}
        checkpoint = root / "yolo26n.pt"
        if _download(CHECKPOINT_URL, checkpoint, 100 * 1024 * 1024)["sha256"] != lock["checkpoint_sha256"]:
            raise RuntimeError("CHECKPOINT_SHA256_MISMATCH")
        image_root = root / "images"; image_root.mkdir()
        metadata = []
        for item in IMAGES:
            path = image_root / item["file_name"]
            identity = _download(item["url"], path, 2 * 1024 * 1024)
            if identity["sha256"] != item["sha256"]: raise RuntimeError("IMAGE_SHA256_MISMATCH:" + item["id"])
            with Image.open(path) as image: width, height = image.size
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
        manifest_path = root / "dataset.json"; manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", "utf-8")
        sizes = {item["id"]: (item["width"], item["height"]) for item in metadata}
        predict_kwargs = {"imgsz": 640, "max_det": 300}

        native_rows = []
        try:
            model = YOLO(str(checkpoint), task="detect")
            for item in metadata:
                result = model.predict(source=str(image_root / item["file_name"]), device="cuda:0", verbose=False, conf=0.001, **predict_kwargs)[0]
                native_rows.append({"sample_id": item["id"], "boxes": result.boxes.xyxy.detach().cpu().tolist(), "scores": result.boxes.conf.detach().cpu().tolist(), "labels": [int(x) for x in result.boxes.cls.detach().cpu().tolist()]})
        except Exception as exc:
            errors["native_inference"] = f"{type(exc).__name__}: {exc}"
            (root / "native-inference.traceback.txt").write_text(traceback.format_exc(), "utf-8")
        native_path = root / "native-direct.json"
        native_path.write_text(json.dumps(native_rows, indent=2) + "\n", "utf-8")
        native_bounds = _bounds(native_rows, sizes) if native_rows else None

        conversion_status = "NOT_RUN"
        conversion_audit = None
        if native_rows:
            try:
                conversion_audit = convert_results(native_rows, format="ultralytics_hbb", category_map=category_map, output=root / "converted-native", manifest=manifest, split="dev")
                conversion_status = "PASS"
            except Exception as exc:
                conversion_status = "FAIL"
                errors["saved_native_conversion"] = f"{type(exc).__name__}: {exc}"
                (root / "saved-native-conversion.traceback.txt").write_text(traceback.format_exc(), "utf-8")

        wrapped_rows = []
        wrapped_status = "NOT_RUN"
        try:
            request = {
                "schema_version": "1.0", "protocol_version": "1.0", "operation": "predict", "service": "ultralytics",
                "experiment": {"name": "rq002-yolo26n-wrapped", "adapter": {"name": "ultralytics", "config": {"package_version": VERSION, "category_map": category_map, "device": "cuda:0", "score_threshold": 0.001, "predict_kwargs": predict_kwargs}}, "eval_split": "dev"},
                "manifest": manifest, "checkpoint": {"path": str(checkpoint), "sha256": digest(checkpoint), "trust": "trusted_legacy_pickle"},
                "output_dir": str(root / "wrapped-execution"), "data_root": str(root),
            }
            request_path = root / "worker-request.json"; response_path = root / "worker-response.json"
            request_path.write_text(json.dumps(request, indent=2) + "\n", "utf-8")
            completed = subprocess.run([sys.executable, "/root/cvrs-src/cvsubstrate/worker_shims/ultralytics_worker.py", "--request", str(request_path), "--response", str(response_path)], capture_output=True, text=True, timeout=600)
            (root / "wrapped.stdout.txt").write_text(completed.stdout, "utf-8"); (root / "wrapped.stderr.txt").write_text(completed.stderr, "utf-8")
            if completed.returncode != 0: raise RuntimeError(f"WRAPPED_WORKER_EXIT_{completed.returncode}")
            response = json.loads(response_path.read_text("utf-8"))
            if response.get("status") != "ok": raise RuntimeError("WRAPPED_WORKER_RESPONSE:" + str(response.get("error")))
            wrapped_rows = [json.loads(line) for line in (root / "wrapped-execution/upstream_predictions.jsonl").read_text("utf-8").splitlines()]
            wrapped_status = "PASS"; _ = _bounds(wrapped_rows, sizes)
        except Exception as exc:
            wrapped_status = "FAIL"; errors["wrapped_execution"] = f"{type(exc).__name__}: {exc}"
            (root / "wrapped-execution.traceback.txt").write_text(traceback.format_exc(), "utf-8")

        graph = None; export_status = "NOT_RUN"; ort_status = "NOT_RUN"; ort_rows = []; ort_raw = {}; ort_repeatability = []
        try:
            export_input = root / "export-input"; export_input.mkdir()
            export_checkpoint = export_input / checkpoint.name; export_checkpoint.write_bytes(checkpoint.read_bytes())
            export_model = YOLO(str(export_checkpoint), task="detect")
            artifact = export_model.export(format="onnx", imgsz=640, opset=19, simplify=False, dynamic=False, nms=True, device="cpu")
            graph = Path(artifact)
            onnx_model = onnx.load(str(graph)); onnx.checker.check_model(onnx_model)
            export_status = "PASS"

            session = ort.InferenceSession(str(graph), providers=["CPUExecutionProvider"])
            input_name = session.get_inputs()[0].name
            first_image = cv2.imread(str(image_root / metadata[0]["file_name"]))
            letterboxed = LetterBox(new_shape=(640, 640), auto=False, stride=32)(image=first_image)
            tensor = np.ascontiguousarray(letterboxed[:, :, ::-1].transpose(2, 0, 1))[None].astype(np.float32) / 255.0
            outputs_1 = session.run(None, {input_name: tensor}); outputs_2 = session.run(None, {input_name: tensor})
            ort_repeatability = [bool(np.array_equal(a, b)) for a, b in zip(outputs_1, outputs_2)]
            np.savez_compressed(root / "onnxruntime-raw-image139.npz", **{item.name: value for item, value in zip(session.get_outputs(), outputs_1)})
            ort_raw = {item.name: {"shape": list(value.shape), "dtype": str(value.dtype), "finite": bool(np.isfinite(value).all())} for item, value in zip(session.get_outputs(), outputs_1)}

            ort_model = YOLO(str(graph), task="detect")
            for item in metadata:
                result = ort_model.predict(source=str(image_root / item["file_name"]), device="cpu", verbose=False, conf=0.001, **predict_kwargs)[0]
                ort_rows.append({"sample_id": item["id"], "boxes": result.boxes.xyxy.detach().cpu().tolist(), "scores": result.boxes.conf.detach().cpu().tolist(), "labels": [int(x) for x in result.boxes.cls.detach().cpu().tolist()]})
            (root / "onnxruntime-postprocessed.json").write_text(json.dumps(ort_rows, indent=2) + "\n", "utf-8")
            ort_status = "PASS" if all(ort_repeatability) else "FAIL_REPEATABILITY"
        except Exception as exc:
            if export_status != "PASS": export_status = "FAIL"
            else: ort_status = "FAIL"
            errors["export_or_onnxruntime"] = f"{type(exc).__name__}: {exc}"
            (root / "export-onnxruntime.traceback.txt").write_text(traceback.format_exc(), "utf-8")

        wrapped_comparison = _compare(native_rows, wrapped_rows) if native_rows and wrapped_rows else None
        ort_comparison = _compare(native_rows, ort_rows) if native_rows and ort_rows else None
        report = {
            "schema": "cvrs.rq002.ultralytics-yolo26n.v1",
            "status": "PASS_ULTRALYTICS_NATIVE_CVRS_AND_ORT" if native_rows and conversion_status == "PASS" and wrapped_status == "PASS" and export_status == "PASS" and ort_status == "PASS" else "FAIL_OR_PARTIAL_ULTRALYTICS_QUALIFICATION",
            "assets": lock,
            "native": {"status": "PASS" if native_rows else "FAIL", "bounds": native_bounds, "detections": sum(len(row["boxes"]) for row in native_rows)},
            "saved_native_conversion": {"status": conversion_status, "audit": conversion_audit},
            "wrapped_execution": {"status": wrapped_status, "comparison_to_native": wrapped_comparison, "detections": sum(len(row["boxes"]) for row in wrapped_rows)},
            "export": {"status": export_status, "onnx_sha256": digest(graph) if graph and graph.is_file() else None, "onnx_bytes": graph.stat().st_size if graph and graph.is_file() else None, "onnx_checker": "PASS" if export_status == "PASS" else "NOT_PASS"},
            "onnxruntime": {"status": ort_status, "version": ort.__version__, "provider": "CPUExecutionProvider", "raw_outputs_image139": ort_raw, "raw_repeatability_exact": ort_repeatability, "postprocessed_bounds": _bounds(ort_rows, sizes) if ort_rows else None, "comparison_to_native": ort_comparison},
            "environment": {"python": sys.version, "ultralytics": ultralytics.__version__, "torch": torch.__version__, "torchvision": importlib.metadata.version("torchvision"), "onnx": onnx.__version__, "onnxruntime": ort.__version__, "numpy": np.__version__, "native_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None},
            "frozen_parameters": {"score_threshold": 0.001, "imgsz": 640, "max_det": 300, "native_device": "cuda:0", "onnxruntime_device": "cpu", "export": {"opset": 19, "simplify": False, "dynamic": False, "nms": True}},
            "separate_statuses": {"native_execution": "PASS" if native_rows else "FAIL", "conversion_fidelity": conversion_status, "wrapped_repeatability": "PASS" if wrapped_comparison and wrapped_comparison["all_pass"] else "FAIL_OR_NOT_RUN", "export": export_status, "runtime_repeatability": ort_status, "deployment_fidelity": "PASS" if ort_comparison and ort_comparison["all_pass"] else "FAIL_OR_NOT_RUN", "evaluator_equivalence": "NOT_RUN_NO_GROUND_TRUTH"},
            "errors": errors,
            "controls": {"training": False, "optimizer_steps": 0, "protected_data_access": 0, "sealed_test_access": 0, "gpu_concurrency": 1, "automatic_paid_retry": False, "geometry_modification": "NONE", "filtering": "ONLY_PREREGISTERED_NATIVE_SCORE_THRESHOLD_AND_MAX_DET"},
            "runtime_seconds": time.perf_counter() - started,
        }
        (root / "report.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
        excluded = {"yolo26n.pt", *[item["file_name"] for item in IMAGES]}
        checksums = []
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name not in excluded:
                checksums.append(f"{digest(path)}  {path.relative_to(root).as_posix()}")
        (root / "checksums.sha256").write_text("\n".join(checksums) + "\n", "utf-8")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(root.rglob("*")):
                if path.is_file() and path.name not in excluded:
                    bundle.write(path, path.relative_to(root).as_posix())
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
