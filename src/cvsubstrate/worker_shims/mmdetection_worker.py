#!/usr/bin/env python3
"""Standalone trusted MMDetection bridge.

This file intentionally depends on Python stdlib + the target heritage environment.
It MUST NOT import cvsubstrate, pydantic, numpy, Pillow, or controller packages.
It is launched by absolute file path from the modern controller so an old MMDetection
Python environment does not need CVRS installed.

It is dependency isolation, not a sandbox. Python configs and legacy checkpoints are
executable/trusted inputs and require explicit trust declarations.
"""
import argparse
import ast
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

PROTOCOL_VERSION = "1.0"
ALLOWED_UPSTREAMS = {"open-mmlab/mmdetection", "VBTI-development/onedl-mmdetection"}


def _json_read(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _json_write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(str(tmp), str(path))


def _jsonl_write(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(str(tmp), str(path))


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _safe_join(root, rel):
    p = (Path(root) / rel).resolve()
    r = Path(root).resolve()
    try:
        p.relative_to(r)
    except ValueError:
        raise RuntimeError("DATA_PATH: sample image escapes declared data root")
    return p


def _package_version(name):
    try:
        from importlib import metadata
        return metadata.version(name)
    except Exception:
        try:
            mod = importlib.import_module(name)
            return getattr(mod, "__version__", "unknown")
        except Exception:
            return None


def _git_identity(module_name):
    result = {"git_sha": None, "git_remote": None, "source_path": None, "verified_from_git": False}
    try:
        mod = importlib.import_module(module_name)
        src = Path(mod.__file__).resolve()
        result["source_path"] = str(src)
        candidates = [src.parent] + list(src.parents)
        repo = None
        for candidate in candidates:
            if (candidate / ".git").exists():
                repo = candidate
                break
        if repo is None:
            return result
        sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=5)
        remote = subprocess.run(["git", "-C", str(repo), "config", "--get", "remote.origin.url"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=5)
        if sha.returncode == 0:
            result["git_sha"] = sha.stdout.strip()
            result["verified_from_git"] = True
        if remote.returncode == 0:
            result["git_remote"] = remote.stdout.strip()
    except Exception:
        pass
    return result


def _environment():
    installed = importlib.util.find_spec("mmdet") is not None and importlib.util.find_spec("mmcv") is not None
    env = {
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "platform": sys.platform,
        "mmdet": _package_version("mmdet") if installed else None,
        "mmcv": _package_version("mmcv"),
        "mmengine": _package_version("mmengine") if installed else None,
        "torch": _package_version("torch"),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "mmdet_source": _git_identity("mmdet") if installed else None,
    }
    return installed, env


def _capabilities():
    installed, env = _environment()
    return {
        "schema_version": "1.0",
        "adapter": "mmdetection",
        "protocol_version": PROTOCOL_VERSION,
        "tasks": ["hbb_detection"],
        "operations": ["capabilities", "validate", "predict"],
        "installed": installed,
        "execution_verified_in_this_process": False,
        "limitations": [
            "Trusted executable configs and legacy checkpoints only",
            "Training intentionally not implemented in heritage bridge",
            "No network artifact acquisition",
            "Published metric reproduction requires exact external dataset/protocol",
        ],
        "environment": env,
        "standalone_bridge": True,
        "imports_controller_package": False,
    }


def _disable_network():
    def denied(*args, **kwargs):
        raise RuntimeError("NETWORK_DISABLED: heritage bridge does not acquire remote artifacts")
    socket.create_connection = denied
    try:
        socket.socket.connect = denied
    except Exception:
        pass


def _literal_bases(path):
    try:
        tree = ast.parse(Path(path).read_text("utf-8"), filename=str(path))
    except Exception as exc:
        return [], "parse_error:%s" % type(exc).__name__
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "_base_" for t in node.targets):
                try:
                    v = ast.literal_eval(node.value)
                except Exception:
                    return [], "dynamic_base"
                if isinstance(v, str):
                    return [v], None
                if isinstance(v, (list, tuple)) and all(isinstance(x, str) for x in v):
                    return list(v), None
                return [], "unsupported_base_literal"
    return [], None


def _config_graph(root_path):
    root_path = Path(root_path).resolve()
    seen = set()
    nodes = []
    edges = []
    unresolved = []

    def walk(path):
        path = Path(path).resolve()
        key = str(path)
        if key in seen:
            return
        seen.add(key)
        if not path.is_file():
            unresolved.append({"path": key, "reason": "missing"})
            return
        bases, reason = _literal_bases(path)
        nodes.append({"path": key, "sha256": _sha256(path), "base_literals": bases})
        if reason:
            unresolved.append({"path": key, "reason": reason})
        for base in bases:
            # Package-style bases and variables are left unresolved rather than guessed.
            if base.startswith("mmdet::") or ":" in base:
                unresolved.append({"path": key, "base": base, "reason": "package_or_nonfilesystem_base"})
                continue
            child = (path.parent / base).resolve()
            edges.append({"config": key, "base": str(child)})
            walk(child)

    walk(root_path)
    return {"root": str(root_path), "nodes": nodes, "edges": edges, "unresolved": unresolved}


def _tolist(value):
    for name in ("detach", "cpu"):
        fn = getattr(value, name, None)
        if callable(fn):
            value = fn()
    fn = getattr(value, "tolist", None)
    return fn() if callable(fn) else list(value)


def _extract_prediction(result):
    """Return boxes, scores, zero-based labels from MMDetection 3.x or 2.x APIs."""
    if hasattr(result, "pred_instances"):
        pred = result.pred_instances
        return _tolist(pred.bboxes), _tolist(pred.scores), [int(x) for x in _tolist(pred.labels)], "mmdet3_data_sample"
    bbox_result = result[0] if isinstance(result, tuple) else result
    if isinstance(bbox_result, (list, tuple)):
        boxes, scores, labels = [], [], []
        for label, per_class in enumerate(bbox_result):
            rows = _tolist(per_class)
            for row in rows:
                if len(row) < 5:
                    raise RuntimeError("NATIVE_OUTPUT: expected x1,y1,x2,y2,score row")
                boxes.append([float(row[0]), float(row[1]), float(row[2]), float(row[3])])
                scores.append(float(row[4]))
                labels.append(int(label))
        return boxes, scores, labels, "mmdet2_bbox_result"
    raise RuntimeError("NATIVE_OUTPUT: unsupported MMDetection inference result shape")


def _validate_inputs(req):
    exp = req.get("experiment")
    manifest = req.get("manifest")
    if not isinstance(exp, dict) or not isinstance(manifest, dict):
        raise RuntimeError("REQUEST: experiment and manifest are required")
    adapter = exp.get("adapter") or {}
    if adapter.get("name") != "mmdetection":
        raise RuntimeError("ADAPTER_MISMATCH: expected mmdetection")
    if exp.get("training") is not None:
        raise RuntimeError("OPERATION_UNSUPPORTED: heritage training is not implemented")
    config = adapter.get("config") or {}
    required = {"config_path", "config_sha256", "trust_executable_config", "category_map", "upstream", "revision"}
    if not required.issubset(set(config)):
        raise RuntimeError("HERITAGE_CONFIG: explicit config identity/trust/taxonomy/upstream/revision required")
    if config.get("trust_executable_config") is not True:
        raise RuntimeError("CONFIG_TRUST: executable Python config requires explicit trust")
    if config.get("upstream") not in ALLOWED_UPSTREAMS:
        raise RuntimeError("UPSTREAM_IDENTITY: unrecognized heritage source")
    config_path = Path(config["config_path"]).resolve()
    if not config_path.is_file() or _sha256(config_path) != config["config_sha256"]:
        raise RuntimeError("CONFIG_HASH: config unavailable or digest mismatch")
    checkpoint = req.get("checkpoint")
    if checkpoint:
        if checkpoint.get("trust") != "trusted_legacy_pickle":
            raise RuntimeError("CHECKPOINT_TRUST: legacy loader trust must be explicit")
        cp = Path(checkpoint.get("path", "")).resolve()
        if not cp.is_file() or _sha256(cp) != checkpoint.get("sha256"):
            raise RuntimeError("CHECKPOINT_HASH: checkpoint unavailable or digest mismatch")
    elif not config.get("allow_random_initialization", False):
        raise RuntimeError("CHECKPOINT_REQUIRED: real checkpoint required unless random initialization explicitly allowed for conformance testing")
    out = Path(req.get("output_dir") or "").resolve()
    out.mkdir(parents=True, exist_ok=True)
    data_root = Path(req.get("data_root") or "").resolve()
    categories = {int(c["id"]) for c in manifest.get("categories", [])}
    cmap = {int(k): int(v) for k, v in config["category_map"].items()}
    if not set(cmap.values()).issubset(categories):
        raise RuntimeError("CATEGORY_MAP: mapping references unknown dataset category")
    return exp, manifest, config, config_path, checkpoint, out, data_root, cmap


def _run(req):
    op = req.get("operation")
    if req.get("protocol_version") != PROTOCOL_VERSION:
        raise RuntimeError("PROTOCOL_VERSION: incompatible worker request")
    if op == "capabilities":
        return _capabilities()
    if op == "train":
        raise RuntimeError("OPERATION_UNSUPPORTED: heritage training is not implemented")
    installed, env = _environment()
    if not installed:
        raise RuntimeError("MMDETECTION_NOT_INSTALLED: configure trusted isolated MMDetection interpreter; no substitute model used")
    exp, manifest, config, config_path, checkpoint, out, data_root, cmap = _validate_inputs(req)
    _disable_network()
    import mmdet
    family = str(getattr(mmdet, "__version__", "unknown")).split(".")[0]
    profile = config.get("profile")
    if profile == "mmdet2" and family != "2":
        raise RuntimeError("PROFILE_MISMATCH: expected MMDetection 2.x")
    if profile == "mmdet3" and family != "3":
        raise RuntimeError("PROFILE_MISMATCH: expected MMDetection 3.x")
    from mm_drivers import get_driver
    driver = get_driver('onedl' if config.get('upstream') == 'VBTI-development/onedl-mmdetection' else 'mmdet2' if family == '2' else 'mmdet3')

    graph = _config_graph(config_path)
    _json_write(out / "config_graph.json", graph)
    graph_sha = _sha256(out / "config_graph.json")
    resolved = driver.resolve(str(config_path))
    pretty = resolved.pretty_text
    (out / "resolved_config.py.txt").write_text(pretty, encoding="utf-8", newline="\n")
    resolved_sha = _sha256(out / "resolved_config.py.txt")
    source = env.get("mmdet_source") or {}
    actual_sha = source.get("git_sha")
    revision_match = actual_sha == config.get("revision") if actual_sha else None

    if op == "validate":
        result = {
            "status": "CONFIG_RESOLVED",
            "heritage_level": "H1_CONFIG_RESOLVED",
            "environment": env,
            "upstream_claim": config["upstream"],
            "revision_claim": config["revision"],
            "actual_source_identity": source,
            "revision_match": revision_match,
            "resolved_config_sha256": resolved_sha,
            "config_graph_sha256": graph_sha,
            "evidence_artifacts": ["resolved_config.py.txt", "config_graph.json"],
        }
        _json_write(out / "heritage_execution.json", result)
        return result

    if op != "predict":
        raise RuntimeError("OPERATION: unsupported operation")
    model = driver.construct(resolved, checkpoint["path"] if checkpoint else None, device=config.get("device", "cpu"))
    samples = {s["id"]: s for s in manifest.get("samples", [])}
    split_name = exp.get("eval_split", "dev")
    split = manifest.get("splits", {}).get(split_name)
    if not split:
        raise RuntimeError("SPLIT: selected evaluation split missing")
    raw_rows = []
    canonical_rows = []
    total_native = 0
    total_canonical = 0
    backends = set()
    for sid in split["sample_ids"]:
        sample = samples[sid]
        image_path = _safe_join(data_root, sample["image"])
        if not image_path.is_file() or _sha256(image_path) != sample["sha256"]:
            raise RuntimeError("DATA_HASH: image unavailable or digest mismatch for %s" % sid)
        result = driver.predict(model, str(image_path))
        boxes, scores, labels, native_shape = _extract_prediction(result)
        backends.add(native_shape)
        if any(int(label) not in cmap for label in labels):
            raise RuntimeError("CATEGORY_MAP: model returned unmapped class; no detections dropped")
        native = {"sample_id": sid, "boxes": boxes, "scores": scores, "zero_based_labels": labels, "native_shape": native_shape}
        canonical = {
            "schema_version": "1.0",
            "sample_id": sid,
            "width": int(sample["width"]),
            "height": int(sample["height"]),
            "boxes": boxes,
            "scores": scores,
            "category_ids": [cmap[int(label)] for label in labels],
            "coordinate_frame": "original_image_xyxy",
            "score_semantics": "backend confidence, not calibrated probability",
            "transform_provenance": {"native_api": "mmdet.apis.inference_detector", "rescale": "native API original-image coordinates", "native_shape": native_shape},
        }
        raw_rows.append(native)
        canonical_rows.append(canonical)
        total_native += len(boxes)
        total_canonical += len(canonical["boxes"])
    _jsonl_write(out / "upstream_predictions.jsonl", raw_rows)
    _jsonl_write(out / "predictions.jsonl", canonical_rows)

    mismatches = []
    for native, canonical in zip(raw_rows, canonical_rows):
        if native["boxes"] != canonical["boxes"]:
            mismatches.append({"sample_id": native["sample_id"], "field": "boxes"})
        if native["scores"] != canonical["scores"]:
            mismatches.append({"sample_id": native["sample_id"], "field": "scores"})
        expected = [cmap[int(x)] for x in native["zero_based_labels"]]
        if expected != canonical["category_ids"]:
            mismatches.append({"sample_id": native["sample_id"], "field": "category_ids"})
    audit = {
        "native_images": len(raw_rows),
        "canonical_images": len(canonical_rows),
        "native_detections": total_native,
        "canonical_detections": total_canonical,
        "array_mismatches": mismatches,
        "exact_representation_fidelity": not mismatches and total_native == total_canonical,
        "category_map": {str(k): v for k, v in sorted(cmap.items())},
        "native_result_shapes": sorted(backends),
        "note": "Fidelity certifies representation conversion only, not model accuracy or published metric reproduction.",
    }
    _json_write(out / "conversion_audit.json", audit)
    if not audit["exact_representation_fidelity"]:
        raise RuntimeError("OUTPUT_PARITY: native/canonical representation mismatch")
    result = {
        "status": "OUTPUT_PARITY_VERIFIED",
        "heritage_level": "H3_OUTPUT_PARITY_VERIFIED",
        "environment": env,
        "upstream_claim": config["upstream"],
        "revision_claim": config["revision"],
        "actual_source_identity": source,
        "revision_match": revision_match,
        "resolved_config_sha256": resolved_sha,
        "config_graph_sha256": graph_sha,
        "checkpoint_sha256": checkpoint.get("sha256") if checkpoint else None,
        "representation_arrays_exact": True,
        "evidence_artifacts": [
            "resolved_config.py.txt", "config_graph.json", "upstream_predictions.jsonl",
            "predictions.jsonl", "conversion_audit.json", "heritage_execution.json"
        ],
        "nonclaims": [
            "No published model-zoo metric reproduction unless separately evaluated on exact reference data/protocol",
            "No heritage training reproduction",
            "Source repository revision is independently verified only when a Git checkout is discoverable",
        ],
    }
    _json_write(out / "heritage_execution.json", result)
    return result


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--request", required=True)
    p.add_argument("--response", required=True)
    args = p.parse_args(argv)
    try:
        req = _json_read(args.request)
        result = _run(req)
        response = {"schema_version": "1.0", "protocol_version": PROTOCOL_VERSION, "status": "SUCCEEDED", "result": result, "error": None}
        code = 0
    except Exception as exc:
        text = str(exc)
        code_name = text.split(":", 1)[0] if ":" in text else type(exc).__name__
        response = {"schema_version": "1.0", "protocol_version": PROTOCOL_VERSION, "status": "FAILED", "result": {}, "error": {"code": code_name, "message": text}}
        code = 0  # structured failure is a successful transport response
    _json_write(args.response, response)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
