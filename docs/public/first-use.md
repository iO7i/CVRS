# First use: one inspect-to-execute journey

This page applies to the `0.7.1a3` public-alpha release candidate. It does not require the package to exist on PyPI. Keep the extracted repository separate from your experiment outputs.

## 1. Create a dedicated controller environment

The controller requires Python 3.11 or later. In a terminal at the repository root:

```bash
python -m venv .venv
```

On Linux/macOS, activate with `source .venv/bin/activate`. In Windows PowerShell, use `.\.venv\Scripts\Activate.ps1`; when activation is restricted, call `.\.venv\Scripts\python.exe` directly instead. None of these instructions certifies an untested operating system.

```bash
python -m pip install -e ".[adoption]"
python -m cvsubstrate doctor
python -m cvsubstrate init my-experiment --profile detection
python -m cvsubstrate inspect-repo my-experiment --out inspection.json
```

The extra named `adoption` supplies packaging/YAML utilities, not all native frameworks. Dependency installation may contact a package index. Inspecting and creating this example needs no external model or benchmark dataset and does not execute a detector.

The generated project includes `experiments/baseline.json` and deterministic software-test images. Read the specification and `inspection.json`. The fixture images are not real aerial imagery, regardless of bookkeeping tags used in later protocol demos.

## 2. Choose the existing native CPU path

For a simple dedicated example environment:

```bash
python -m pip install -e ".[native,adoption]"
python -m cvsubstrate run my-experiment/experiments/baseline.json --out my-first-run
```

This runs a small actual detector. It is not a canned prediction service or a pretrained benchmark reproduction. The native extra is substantial; a lightweight controller install is not the same as a lightweight ML runtime.

To keep the controller and model dependencies separate, install the **same CVRS candidate with its native extra** in another environment and pass that interpreter using `--worker-python`. The built-in torchvision worker is imported as a CVRS module, so Torch alone is insufficient. For example, run `/path/to/native/python -m pip install -e ".[native]"` from this source checkout, or install the matching wheel and its native dependencies there. Use the native interpreter's absolute path. Do not merge old MMDetection and modern foundation-model environments merely to follow this example.

## 3. Inspect the evidence

`--out my-first-run` names a parent directory, not the final run directory. The command prints JSON with the actual timestamped `run` path. Replace `RUN_DIRECTORY` below with that exact path. Do not pass the parent containing several runs.

A successful run has an `artifacts.json` integrity manifest and JSON artifacts describing its experiment, data, source, environment, predictions and evaluation. Use the existing commands:

```bash
python -m cvsubstrate verify RUN_DIRECTORY
python -m cvsubstrate report RUN_DIRECTORY
```

Exact report options remain available through `report --help`. Inspect metric names and protocol definitions: diagnostic metrics are not automatically official COCO AP. An artifact hash detects byte changes within its declared scope; it does not certify the correctness of the detector or prove an independent reproduction.

The optional golden workflow is `python -m cvsubstrate demo-all my-demo`. It creates two real CPU runs and saved-prediction re-evaluation using procedural data. Allow it to finish before inspecting its final manifest. A failed or cancelled run must not be reported as succeeded.

## 4. Move to your own research repository

Use [guided paper wrapping](guided-paper.md) or [the heritage guide](heritage.md). Keep source inspection separate from approval and execution. Static inspection cannot recover every dynamic dependency or supply missing checkpoints/data.

`--trust` authorizes execution of the chosen native code; it does not sandbox it. Checkpoint/config/plugin trust and dataset redistribution permissions remain your responsibility. See [security](security.md).

## Installation and evidence boundaries

No Python interpreter, installed environment, GPU driver, real dataset or pretrained checkpoint is bundled. Local dependency versions used in recorded checks are observations, not a complete platform compatibility matrix. See [release closeout](closeout.md) and the root `PUBLIC_STATUS.json` for what was checked in this candidate versus earlier builds.
