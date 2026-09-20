"""First-class stack workspaces without taking ownership of native model code."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from cvsubstrate.adoption.common import output_tree, write_text
from cvsubstrate.adoption.environments import PACKS
from cvsubstrate.adoption.stacks import execute_stack
from cvsubstrate.errors import CVRSError
from cvsubstrate.product.environments import EnvironmentManager, probe
from cvsubstrate.provenance.io import read_json, write_json, digest, file_digest

DETAILS = {
    "mmdetection2": ("MMDetection 2", "python_config", ["COCO HBB"], ["mmcv._ext", "Config inheritance", "CUDA wheel matrix"]),
    "mmdetection3": ("MMDetection 3", "mmengine_config", ["COCO HBB"], ["MMCV upper bound", "Custom imports"]),
    "onedl": ("OneDL Detection", "mmengine_config", ["COCO HBB"], ["Fork identity must be preserved"]),
    "mmrotate": ("MMRotate", "python_config", ["DOTA OBB"], ["Angle convention", "Oriented operators"]),
    "mmseg0": ("MMSegmentation 0.x", "python_config", ["Semantic labels"], ["Ignore index", "reduce_zero_label"]),
    "mmseg1": ("MMSegmentation 1.x", "mmengine_config", ["Semantic labels"], ["MMCV operators", "Dataset label semantics"]),
    "mmyolo": ("MMYOLO", "mmengine_config", ["COCO HBB"], ["Native pipeline and augmentation lineage"]),
    "mmdeploy": ("MMDeploy", "deployment_config", ["Native export artifacts"], ["Backend operator support"]),
    "detectron2": ("Detectron2", "YACS/default_trainer", ["HBB", "Instances", "Semantic labels"], ["LazyConfig/custom loops use paper wrapper"]),
    "ultralytics": ("Ultralytics", "native_job", ["HBB", "OBB", "Masks"], ["Native epochs are not fixed-update campaigns"]),
    "rfdetr": ("RF-DETR", "native_job", ["HBB"], ["Checkpoint variant", "Native epoch semantics"]),
    "grounding-dino": ("Grounding DINO (HF)", "vision_job", ["Grounded regions"], ["Tokenizer/processor identity", "Phrase mapping"]),
    "sam": ("SAM (HF)", "vision_job", ["Prompted masks"], ["Prompt modality", "Mask coordinate frame"]),
    "sam2": ("SAM2", "vision_job", ["Prompted masks"], ["Local config and weights", "Prompt history"]),
    "sam3": ("SAM3", "native_job", ["Text-grounded masks"], ["Native version-specific API", "Whole coupled model stays native"]),
    "torchgeo": ("TorchGeo", "dataset_query", ["Geospatial arrays"], ["Sensor bands", "CRS/query units"]),
    "terratorch": ("TerraTorch", "native_cli", ["Declared decoded task outputs"], ["Explicit decoder required", "Whole training graph stays native"]),
    "core": ("CVRS core", "canonical_json", ["Metadata/evidence"], ["Core does not install model frameworks"]),
}


def inspect_pack(name: str) -> dict:
    if name not in PACKS:
        raise ValueError("unknown stack pack")
    title, config, outputs, pitfalls = DETAILS[name]
    base = PACKS[name]
    return {
        "schema_version": "1.0", "id": name, "title": title, "driver": "cvsubstrate.adoption.stacks:execute_stack",
        "operations": base["operations"], "module_requirements": base["modules"],
        "example_python": base["python"], "config_family": config, "output_contracts": outputs,
        "common_diagnostics": pitfalls, "implementation": "AVAILABLE", "execution": "NOT_RUN",
        "evaluation": "NOT_RUN", "benchmark_reproduction": "NOT_RUN",
        "notes": ["Operation support is finite and task-specific.",
                  "Example Python is a starting template, not a claim that all revisions require that version.",
                  "Bind the actual repository revision, assets and compatible native environment."],
    }


def list_packs() -> list[dict]:
    return [inspect_pack(name) for name in PACKS]


def diagnose(observation: dict, pack: str, error_text: str = "") -> dict:
    info = inspect_pack(pack)
    findings = []
    modules = observation.get("modules", {})
    for name in info["module_requirements"]:
        present = modules.get(name)
        if isinstance(present, dict):
            present = present.get("installed")
        if not present:
            findings.append({"code": "MISSING_MODULE", "module": name,
                             "action": "Create a separate managed environment using reviewed pins for this repository."})
    patterns = {
        "mmcv._ext": ("MMCV_COMPILED_OPS", "Check the native Torch/CUDA/MMCV wheel or build combination; do not alter the controller environment."),
        "undefined symbol": ("COMPILED_ABI", "Compare the compiled extension's build environment with the selected native interpreter."),
        "CUDA out of memory": ("NATIVE_MEMORY", "Reduce the model batch/window size in the native job; CVRS buffer limits do not bound model allocations."),
        "No module named": ("IMPORT_FAILURE", "Compare expected modules with the selected environment observation."),
        "operator torchvision::nms does not exist": ("TORCHVISION_OPS", "Install a mutually compatible native Torch/torchvision build."),
    }
    for pattern, (code, action) in patterns.items():
        if pattern in error_text:
            findings.append({"code": code, "observed_pattern": pattern, "action": action})
    return {"pack": pack, "status": "REQUIRES_ATTENTION" if findings else "METADATA_PRESENT",
            "findings": findings, "native_model_compatibility": "NOT_INFERRED",
            "next": "Run an explicitly trusted local-asset operation and retain its execution receipt."}


def configure_pack(pack: str, destination: Path, *, python: str | None = None,
                   store: Path | None = None, environment: str | None = None,
                   payload: dict | None = None) -> dict:
    info = inspect_pack(pack)
    if bool(python) == bool(store and environment):
        raise ValueError("provide either --python or the pair --store/--environment")
    managed = None
    if store and environment:
        manager = EnvironmentManager(store)
        python = manager.interpreter(environment)
        managed = manager.doctor(environment)
        if managed["health"]["status"] != "HEALTHY_METADATA":
            raise CVRSError("ENV_UNHEALTHY", "repair the named environment before configuring the stack")
    if not Path(str(python)).is_file():
        raise ValueError("stack interpreter must be an existing executable file")
    observation = probe(str(python), info["module_requirements"])
    payload = payload or {}
    asset_hashes = {}
    for key in ("config", "checkpoint", "processor", "dataset_manifest"):
        value = payload.get(key)
        if value and Path(value).is_file():
            asset_hashes[key] = file_digest(Path(value))
    record = {"schema_version": "1.0", "pack": pack, "python": str(Path(str(python)).absolute()),
              "python_binary_sha256": file_digest(Path(str(python))), "payload": payload,
              "asset_hashes": asset_hashes, "managed_environment": managed,
              "observation": observation, "native_execution": "NOT_RUN"}
    with output_tree(destination, seal=False) as out:
        write_json(out / "stack.json", record)
        write_json(out / "pack.json", info)
        write_json(out / "diagnostics.json", diagnose(observation, pack))
        write_text(out / "RUNME.md", f"# {info['title']} workspace\n\n"
            "Review the local assets and native payload in `stack.json`. Nothing was installed or run.\n\n"
            "```bash\ncvrs stack doctor .\ncvrs stack execute . predict --out NEW_OUTPUT --trust\n```\n\n"
            "The chosen operation must be in the pack's declared operation list. Native configuration executes code.\n")
    return {"status": "CONFIGURED", "destination": str(destination), "diagnostics": diagnose(observation, pack)}


def workspace_doctor(workspace: Path) -> dict:
    p = workspace / "stack.json" if workspace.is_dir() else workspace
    spec = read_json(p)
    if file_digest(Path(spec["python"])) != spec["python_binary_sha256"]:
        raise CVRSError("INTERPRETER_CHANGED", "configured interpreter binary changed")
    observation = probe(spec["python"], inspect_pack(spec["pack"])["module_requirements"])
    result = diagnose(observation, spec["pack"])
    result["observation"] = observation
    for key, sha in spec["asset_hashes"].items():
        if not Path(spec["payload"][key]).is_file() or file_digest(Path(spec["payload"][key])) != sha:
            result["findings"].append({"code": "ASSET_CHANGED", "asset": key})
            result["status"] = "REQUIRES_ATTENTION"
    return result


def run_workspace(workspace: Path, operation: str, destination: Path, *, trust: bool = False) -> dict:
    p = workspace / "stack.json" if workspace.is_dir() else workspace
    spec = read_json(p)
    health = workspace_doctor(p)
    if health["status"] != "METADATA_PRESENT":
        raise CVRSError("STACK_NOT_READY", "inspect stack doctor before starting native execution")
    result = execute_stack(spec["pack"], operation, spec["payload"], destination,
                           worker_python=spec["python"], trust=trust)
    return {**result, "workspace_digest": digest(spec), "pack": spec["pack"]}
