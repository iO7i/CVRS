# Installation and portability

## Tested environment

The delivered evidence records Linux x86-64, CPython 3.13.5, torch 2.10.0+cpu,
torchvision 0.25.0+cpu, NumPy 2.3.5, Pillow 12.3.0, and Pydantic 2.13.4.
These are observed versions, not claims about the newest releases.
The build sandbox's package network was unavailable. A dedicated native environment
referenced its preinstalled libraries; a separate core-only environment received
only local Pydantic dependencies. This is documented in the isolation evidence.
A fresh internet-based dependency installation was not tested here.

The source distribution is portable. Wheels/dependencies are not vendored.
The archive is a source project, not a standalone desktop application or a CUDA image.

## Avoid unintended GPU package downloads

For a CPU setup, explicitly install the tested Torch pair from its official CPU index,
then install the project without asking it to choose a different Torch build:

```sh
python -m pip install torch==2.10.0 torchvision==0.25.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install 'Pillow>=10,<13' 'numpy>=1.26,<3'
python -m pip install -e .
```

Pin the remaining versions to `workers/native_torch/requirements-tested.txt` when
reproducing the recorded environment. Package and platform availability must be
checked locally. Do not assume Linux verification certifies Windows, ARM, macOS,
CUDA, or another Python/Torch pair.

## Separate environments

Install `cv-research-substrate` in each environment that executes its modules.
The controller environment needs the core package (and the optional COCO extra
only when using that evaluator). The native worker environment needs native
framework packages. The heritage environment must already be able to run its
chosen MMDetection configuration before attempting compatibility certification.

`--worker-python` is a trusted interpreter path, not an arbitrary shell command.
There is no global pip install, no system dependency removal, and no modification
of existing historical environments unless the owner explicitly chooses to install
this small bridge into one.

## Offline runtime

The generated fixture/diagnostic workflow does not require network access after
installation. There are no automated dataset/model downloads. All checkpoints are
explicit local references with hashes. The diagnostic demo trains random weights.

## Wheel installation

The archive includes `dist/cv_research_substrate-0.1.0a1-py3-none-any.whl` if the
recorded package-build gate passed. Install it normally with pip. Dependencies
still need to be present or acquired separately; the wheel is not a complete
Python/Torch environment.

## Common errors

`COCO_DEPENDENCY`: Install the pinned official evaluator in the controller, or
explicitly select the separate diagnostic protocol for a software test. There is
no automatic fallback.

`ADAPTER_NOT_INSTALLED` / `MMDETECTION_NOT_INSTALLED`: Check the worker interpreter,
not just the controller interpreter. Run `cvrs capabilities --worker-python ...`.

`IMAGE_HASH` / `DATASET_DIGEST`: Data changed. Create a new manifest/version and
experiment instead of weakening validation.

`MODEL_CONFIG_UNSUPPORTED`: The first native worker is intentionally a narrow
conformance detector. It is not a generic architecture loader.

`LOCKED_TEST`: Use a separate final inference experiment and a matching explicit
authorization record. Do not change split roles to evade this policy.
