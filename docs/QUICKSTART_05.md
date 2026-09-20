# 0.5 quickstart

Use a dedicated Python environment. Python 3.13/Linux is the locally exercised platform. The controller's core is Pydantic-only; install optional libraries only where used. PowerShell examples use `python` after activating the environment, or `./.venv/Scripts/python.exe` explicitly.

## Core-only registry and planning

```bash
python -m pip install -e .
python -m cvsubstrate adapter-recipes list
python -m cvsubstrate research-registry init work-registry
python -m cvsubstrate research-registry verify work-registry
python -m cvsubstrate adapter-recipes scaffold external-vision-adapter
```

The scaffold is native-delegating code, not a model implementation. Its generated `plugin.json` requires explicit trust before execution. Install that project and CVRS in the selected plugin interpreter. Supply a valid local hashed `VisionJob` via the plugin payload's `job` field; `worker_python` can select another model interpreter. Artifact output is supplied by the plugin runner, not an arbitrary payload path.

## One real CPU integration run

```bash
python -m pip install -e '.[native,geo]'
python tools/smoke_frontier.py my-cpu-smoke
```

This creates a real small Mask R-CNN, a real Faster R-CNN, procedural images/raster, checkpoints, telemetry, masks, source-coordinate detections, a registry, derived evaluation and a capsule. `summary.json` records what occurred. It uses no pretrained model download. Multiple subprocesses run synchronously; this is not a cloud job.

## Inspect the generated evidence

```bash
cvrs telemetry inspect my-cpu-smoke/native-mask-training.sqlite
cvrs stream plan my-cpu-smoke/stream-job.json --width 96 --height 80
cvrs research-registry verify my-cpu-smoke/registry
cvrs research-registry list my-cpu-smoke/registry --kind claim
cvrs research-registry export my-cpu-smoke/registry --out my-static-registry
cvrs research-registry capsule my-cpu-smoke/registry --out my-capsule --archive my-capsule.zip
cvrs research-registry restore my-capsule.zip --out my-restored-registry
```

Use distinct output paths; immutable exports never overwrite successful evidence. The streaming path accepts `--resume`, and reuses only tiles with matching source/model/plan identity.

## Use a real pretrained optional model

Start from a recipe, not an unpinned model name:

```bash
cvrs adapter-recipes show grounding_dino_hf
cvrs vision run /path/to/local-job.json --worker-python /path/to/model-env/python --out new-vision-run
```

A job names a local asset directory, hashes all declared required model files, lists image identities, and carries exact prompts. See `VisionJob`, `PromptSpec`, generated schemas and `examples/frontier/README.md`. There is no automatic downloading or inference that a model repository's code license also covers its weights.

## Quantization and detector deployment

```bash
cvrs quantize prepare /path/to/calibration-images.json --out calibration-run
cvrs quantize validate calibration-run/quantization.json
cvrs quantize run calibration-run/quantization.json --worker-python /path/to/ort-env/python --out quantized-run
cvrs detector-deploy infer /path/to/deployment-job.json --worker-python /path/to/runtime-env/python --out deployment-run
```

These commands require actual matching assets and optional libraries. The supplied profile JSON examples describe tensor semantics; they are not predownloaded executable detector packages. Validate exported-runtime predictions against native output before accepting any accuracy or speed claim.

## Tests

```bash
python -m pip install -e '.[dev,native,geo,geometry-validation]'
python -m pytest -q tests/test_frontier_vision.py tests/test_frontier_registry.py tests/test_frontier_stream_telemetry.py tests/test_frontier_deployment_cli.py
python -m pytest -q
```

COCO-reference tests additionally need `.[coco]`. Skips are evidence gaps, not silently passing substitutions. The archive itself can be verified before editing with `cvrs release verify .`.
