# Verification report — CV Research Substrate 0.1.0a1

**Date:** 17 September 2026  
**Verdict:** CPU foundation verified; official COCO parity and MMDetection execution unverified.

This report describes executed software evidence, not detector quality, research novelty,
production certification, or a claim that every capability in the long-term proposal is complete.
The same assistant implemented and verified this delivery. A separate interpreter is not an
independent reviewer; independent external reproduction remains outstanding.

## Executed tests

The final test run exercised the built, installed wheel rather than an editable source import.
**220 passed, 4 skipped, 0 failures, 0 errors**, in 65.03 seconds. The four skips are explicitly
identified official-COCO reference tests: `pycocotools` was unavailable and package downloads
were blocked. They are not counted as passed. See `evidence/pytest-final.log` and
`evidence/junit.xml` for the exact test records.

The suite covers strict schema and geometry checks, seeded randomized tile-transform tests,
COCO input conversion, analytical diagnostic metrics, worker failures and timeouts,
malformed/fake-success responses, artifact tampering, split/lineage violations, four real
model micro-campaigns, repeatability, and checkpoint loading. An additional actual model
continuation test is recorded under `evidence/resume/`.

The recorded statement coverage is approximately 71% for the traced parent test process.
CLI/worker subprocess executions are not automatically collected in that parent coverage
measurement. This is neither proof that untraced code ran nor proof that it was never run;
the explicit subprocess and run evidence establish the separate claims. Coverage is not
numerical correctness. Ruff, mypy, Windows CI, and hosted GitHub CI were not executed.

## Real model evidence

The native worker executed torchvision `FasterRCNN` with a custom two-convolution backbone:
10,668 trainable parameters, random initialization, CPU fp32, and one Torch thread.
It used real proposals, ROIAlign, prediction heads, backpropagation and optimizer updates.
No heuristic detector, canned predictions, pretrained weights, or model download substituted
for actual execution. Tiny procedural images exercise software behavior only.

| Campaign | Optimizer updates | Mock real exposures | Mock synthetic exposures |
|---|---:|---:|---:|
| R | 2 | 2 | 0 |
| S | 2 | 0 | 2 |
| R+S | 2 | 2 | 2 |
| S→R | 4 | 2 | 2 |

All four archived runs succeeded, changed model parameters, generated predictions for the
four development images, and reproduced those predictions exactly after checkpoint reload.
Actual source-specific counts are in each `training_trace.jsonl` and summarized in
`evidence/campaign-results.json`. Extra synthetic exposure is not claimed to be equal compute.

The fixtures' real/synthetic tags are intentionally mock protocol-accounting labels.
**There is no real aerial dataset or evidence of a synthetic-data accuracy improvement here.**
No reported fixed-threshold diagnostic precision/recall is COCO AP.

The continuation self-test compared four uninterrupted optimizer steps with two steps,
save/load of model, optimizer, scheduler and Torch RNG state, followed by two more steps.
Parameters and predictions matched exactly in this environment. Both parameter digests:

```text
ddce5ff373670b4eaae26162e19b4be577425734492b32fa683462e91008665c
```

This is a scoped same-environment CPU test, not a cross-hardware bitwise promise.
The CLI supports weights-only checkpoint initialization; arbitrary interrupted-run resume
orchestration is still deferred.

## Environment and installation evidence

Tested: Linux x86-64, CPython 3.13.5, PyTorch 2.10.0+cpu, torchvision 0.25.0+cpu,
Pydantic 2.13.4, NumPy 2.3.5, Pillow 12.3.0, pytest 9.0.2.
The wheel was built with setuptools and installed into two separate virtual environments.

A clean controller environment contained Pydantic and its required dependencies, but no
Torch, torchvision, NumPy, Pillow, MMCV, MMDetection, or pycocotools. That controller
successfully launched a real model worker through another interpreter and verified its
20-artifact run bundle. `evidence/core-only-environment.json` and `evidence/isolation-runs/`
record that evidence. This demonstrates dependency separation, not a hostile-code sandbox.

Because package-index access was unavailable, the native environment referenced already
installed packages and the core environment was populated with existing Pydantic dependency
files before wheel installation. An internet-based fresh dependency-resolution/install
matrix was not verified. Windows and macOS instructions are included but unexecuted.

## Acceptance gates

| Gate | Status | Evidence or remaining limitation |
|---|---|---|
| G0 — Boundaries | PASS | Lightweight core, explicit worker/trust contracts and non-goals |
| G1 — Contracts | PASS | 22 schemas, validation/hash tests, core-only installation |
| G2 — Real execution | PASS | Actual CPU detector training/inference, round-trip and continuation |
| G3 — Evaluation | PARTIAL | Diagnostics/input mapping verified; official reference tests skipped |
| G4 — Provenance | PASS | Five verifiable archived runs; tampering and failure-path tests |
| G5 — Heritage | BLOCKED | Native adapter/static inspection implemented; MMDetection absent |
| G6 — Protocols | PASS | Four executed fixture campaigns, accounting and protected-split tests |
| G7 — External usability | PARTIAL | Built-wheel clean-controller test; independent external reviewer absent |

Passing five of eight foundation gates is not a percentage-completion estimate for the
long-term framework. No broad MMDetection compatibility badge should be issued.

## Verification and portability

From an extracted distribution, first verify the distribution file hashes:

```sh
python scripts/verify_distribution.py
```

After installing the core, a bundled run can be verified against the bundled fixture data:

```sh
python -m cvsubstrate verify evidence/campaign-runs/20260917T135717-f70c63be8e1d \
  --dataset examples/fixtures/dataset.json
```

Use a single line in shells that do not recognize the shown continuation character.
Bundle identities and relative artifact paths are portable. Historical controller paths,
worker interpreter paths, UTC timestamps, environment versions, and some test-report
filenames are preserved as build provenance, not as required locations on the user's PC.
Select a local worker interpreter when running a new experiment. No original user
conversations, private-project files, credentials, environments, or third-party datasets
are included in the archive.

Hashes detect changes relative to a manifest. They do not establish authorship, code safety,
independent verification, dataset quality, legal rights, or the absence of leakage.

## Explicitly not delivered as verified functionality

- Official COCO reference parity, actual MMDetection/OneDL execution, or model-zoo reproduction.
- GPU/multi-GPU execution, deployment export, ONNX/TensorRT parity, or latency certification.
- Integrated tiled inference, OBB evaluation, GeoTIFF reprojection, VLM/SAM adapters, or simulators.
- Real-data research results, calibrated generalization claims, or independent external adoption.

Standalone HBB tiling/mapping/merge utilities are tested but the model runner deliberately
rejects a tiled policy rather than silently pretending to execute it. The MMDetection bridge
runs upstream code when configured; it is not a universal config/state-dict converter.

The owner should decide the original-code license before public release. Attribution and
third-party license boundaries are documented. No Git identity, remote, push, official
OpenMMLab succession, public release, or publication has been invented.

## Next bounded milestone

Install the official pinned evaluator and a separate trusted legacy environment. Execute
one existing pretrained MMDetection detector, retain native predictions, compare canonical
conversion through the same official evaluator, and archive the evidence. Close these two
reference/heritage gaps before broadening the model list or claiming a framework revival.
