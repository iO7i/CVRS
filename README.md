# CV Research Substrate

**Keep native computer-vision code. Preserve the experiment and its evidence.**

CVRS is a local-first interoperability layer for computer-vision research. It connects separately configured model environments to explicit data, prediction, evaluation and provenance contracts. It does not replace OpenMMLab, implement a new model zoo, or automatically resolve dependencies inside a coupled model.

```text
Existing native code                    Existing analysis tools
MMDetection / MMRotate / Detectron2      FiftyOne / Supervision
Ultralytics / RF-DETR / SAM / HF         W&B / MLflow / DVC
            | native environments                   ^
            v                                       |
       reviewed workers -> canonical outputs -> evaluation
                    \________ evidence + capsules ______/
```

## Release status

**0.7.1a3 is the prepared public-alpha release candidate.** The public project is **CVRS / CV Research Substrate**, authored by **Hosam Talbi (`iO7i`)**, distributed as `cv-research-substrate`, imported as `cvsubstrate`, and invoked with `cvrs`. Source is licensed under **Apache-2.0**. The intended repository is `https://github.com/iO7i/CVRS`. This candidate is not a stable 1.0 release and has not been remotely published.

This release freezes the H2 alpha qualification state without adding another model, dataset, scientific campaign, or compatibility claim. Existing API/CLI paths, native workers, model behavior and research semantics are retained. Read [release notes](RELEASE_NOTES.md) and the [0.7.1 hardening record](docs/HARDENING_071.md).

## Inspect the frozen qualification evidence

Open [`qualification/h2/browser/index.html`](qualification/h2/browser/index.html) directly in a browser. It is an offline, read-only view of **20 frozen qualification lanes** across RQ001 and RQ002. Passing, CVRS-failure, deployment-fidelity, native-runtime, and externally blocked outcomes remain distinct; the public source export includes the browser, its matrix, and the reviewed primary-evidence targets it links to.

The browser is evidence navigation, not a support badge. A passing lane means its declared contract passed for the recorded route; it does not certify every version, model, dataset, GPU, or operating system.

## First use: inspect before executing

Use Python **3.11 or later** for the controller. Native workers may require their own interpreter and dependency versions. Run these commands from an extracted source checkout in a fresh virtual environment:

```bash
python -m pip install -e ".[adoption]"
cvrs doctor
cvrs init my-experiment --profile detection
cvrs inspect-repo my-experiment --out inspection.json
```

This installs the lightweight controller, creates procedural fixture data and an experiment specification, and inspects files **without executing model code**. Package installation may require internet access. No model weights, benchmark dataset or API key is required.

`doctor` reports observed packages and configuration. A package being present does not mean a model has been executed or certified. Use a new output directory for each example.

### Run the real CPU example

For the simple single-environment example, install the native extra in that dedicated environment:

```bash
python -m pip install -e ".[native,adoption]"
cvrs run my-experiment/experiments/baseline.json --out my-first-run
```

`--out my-first-run` is an output **parent**. The command returns JSON containing the actual timestamped `run` directory; use that exact directory when invoking `verify` or `report`.

This executes an actual small torchvision detector with random initialization and generated images. It does **not** demonstrate detector quality, benchmark reproduction or a Sim2Real gain. Model execution needs no network after the dependencies are installed.

The longer, existing golden demonstration performs two CPU model runs, re-evaluates saved predictions and exports local registry/capsule artifacts:

```bash
cvrs demo-all my-demo
```

For a separate native environment, keep the controller lightweight, install the **same CVRS candidate and its native extra in the native environment**, and use `cvrs run ... --worker-python /path/to/native/python`. The built-in torchvision worker is a CVRS module; installing Torch alone in that interpreter is not sufficient. On Windows, use the native environment's `Scripts/python.exe`. See [the first-use guide](docs/public/first-use.md) for environment setup, expected artifacts and exact trust boundaries. Do not install every model ecosystem into one environment.

## Bring an existing research repository

```bash
cvrs inspect-repo /path/to/native-repo --out inspection.json
cvrs wrap-repo /path/to/native-repo --out paper-project --python /path/to/native-python
```

Neither command imports or rewrites that repository. Review the generated specification, supply exact argument lists/output paths, and bind the required local assets. Missing commands or assets must remain **NOT_READY**.

Only after that review:

```bash
cvrs paper readiness paper-project/paper.json
cvrs paper approve paper-project/paper.json --actor YOUR_ACTOR --out approval.json
cvrs paper execute paper-project/paper.json --approval approval.json --operation predict --out paper-result --trust
```

The approval is bound to the reviewed source and inputs. This is explicit execution of **trusted native code**, not a security sandbox. Separate workers exchange detached artifacts; they do not preserve gradients across processes or automatically divide one internally coupled model between environments.

## What is implemented, and what has been demonstrated?

| Surface | Evidence boundary |
|---|---|
| Lightweight core, contracts and artifact integrity | Local software regression evidence; integrity is not proof of computation or scientific validity |
| Owned torchvision CPU models and procedural fixtures | Real training/inference and checkpoint execution have been recorded in earlier builds; current closeout checks are separately identified |
| MMDetection/OneDL/Detectron2 and other native model packs | Finite implementation paths; actual pretrained-model compatibility remains unverified per stack |
| Grounding, segmentation, geospatial and ecosystem bridges | Task-specific contracts and adapters; payload tests are not native SDK certification |
| COCO/DOTA reference evaluation | Reference integration paths; no official benchmark result is claimed by this release |
| GPU, remote services, cluster and independent reproduction | Not executed or certified by this closeout |

[Machine-readable status](PUBLIC_STATUS.json) separates historical evidence from current release checks. The earlier 0.7.1 hardening run recorded **682 passed and 5 skipped**. That is not a new test run performed merely by repackaging. Its coverage measured the pytest process only; child-worker execution was outside that measurement.

## Choose your workflow

| Need | Guide |
|---|---|
| Preserve an OpenMMLab/Detectron2 experiment | [Heritage](docs/public/heritage.md) |
| Use existing analysis, tracking or geospatial tools | [Ecosystem bridges](docs/public/bridges.md) |
| Conduct and inspect research experiments | [Research](docs/public/research.md) |
| Add a native adapter | [Extend](docs/public/extend.md) |
| Configure managed worker environments | [Managed environments](docs/public/managed-environments.md) |
| Review native task boundaries | [Stack packs](docs/public/packs.md) |

Source-attributed recipes listed by `cvrs recipe list` are **preparation recipes**, not reproduced papers. The [architecture](ARCHITECTURE.md), [current product limitations](docs/LIMITATIONS_07.md) and [security guide](SECURITY.md) explain the boundaries.

## Prepare, do not silently publish

```bash
cvrs release preflight . --out ../release-preflight.json
cvrs release public-tree . --out ../cvrs-public-source
cvrs release publish-bundle . --out ../cvrs-publication
```

For this prepared candidate, a non-preview preflight must **PASS** before any remote publication. Preview mode remains useful only for local inspection and never overrides credential or sensitive-data findings. The release tooling generates a reviewed source tree, wheel, source distribution, documentation/schema bundles and hashes; it does not publish to GitHub or PyPI.

The approved identity and Apache-2.0 grant are recorded in `PUBLICATION.json`. Review the [closeout checklist](docs/public/closeout.md), the generated public-source audit, and the exact final artifact hashes before creating any remote release. GitHub private vulnerability reporting must be enabled before the public announcement.

## Documentation and contribution

```bash
cvrs docs portal . --out ../cvrs-docs
cvrs docs link-check ../cvrs-docs
python tools/dev.py check
```

The built-in documentation renderer is offline. The test command requires the development dependencies; it is not part of a minimal user installation. See [CONTRIBUTING.md](CONTRIBUTING.md), [GOVERNANCE.md](GOVERNANCE.md), [SUPPORT.md](SUPPORT.md) and [ROADMAP.md](ROADMAP.md). No claim that Ruff, mypy, hosted CI, MkDocs or every optional integration passed is implied by configuration files being present.

**Non-goals:** model hosting, annotation services, a new CUDA operator library, replacing MLOps dashboards, live simulator control, or universal model conversion. This alpha is a starting point for real integration feedback, not a finished replacement for every CV framework.
