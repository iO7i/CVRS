# Verification record — 0.3.0a1

This is the current verification record. Older `docs/VERIFICATION.md`, `docs/GATES.md`, root Slice 02 handoff, and older `evidence/` logs are historical snapshots, not new release results.

## Complete executed suite

`evidence/slice03/verification-final/status.json` records the exact command, Python, timestamps, wall time and zero exit code. `results.xml` and `pytest.log` record **404 passed, zero failed, five skipped**. Ten executed tests are marked `native`. The five skips are the four COCO perfect/empty/duplicate/crowd parity cases and the Slice 02 COCO reference-audit case; all require unavailable pycocotools.

The full suite ran in Linux with Python 3.13.5 and a CPU PyTorch/torchvision installation. It covered real inference/backpropagation, checkpoint reload and scoped resume, geometry properties, Shapely numerical checks, generated GeoTIFF transforms, campaign accounting/resume, worker crashes and malformed output, artifact mutation, protected-test misuse, safe configuration/prediction imports, CLI workflows, and direct schema validation. Tests using a small trusted fake DOTA module validate invocation/output handling only. They do not validate official DOTA AP.

An earlier regression run had a failing legacy assertion about the expected wording for the generic runner's rejection of tiled input. The assertion was updated to match the explicit dedicated-tiled-runner error; the generic runner was not changed to silently accept unsupported tiling. The final complete run passes. Earlier logs are retained as development history, not substituted for the final results.

## Executed model evidence

| Evidence | Meaning |
|---|---|
| `evidence/slice03/six-arm-campaign/summary.json` | Six actual native CPU training arms, all SUCCEEDED |
| `evidence/slice03/six-arm-campaign/runs/` | Native checkpoints, measured traces, predictions and sealed run artifacts |
| `evidence/slice03/six-arm-report/` | Generated per-arm/seed report; one exploratory seed, no statistical benefit claim |
| `evidence/slice03/campaign-resume-check.log` | Completed cases reused without extra training |
| `evidence/slice03/high-resolution-final-run/` | Complete 2048x1536 procedural-image tiling/model/merge/evaluation execution |
| `evidence/slice03/high-resolution-final-input/` | Generated source and annotations; half-open box coordinates |
| `evidence/slice03/core-wheel-verification.json` | New wheel in core-only environment launching a real separate-interpreter worker |
| `evidence/slice03/core-wheel-workflow/runs/` | Actual model evidence from that isolated-controller path |
| `evidence/slice03/wheel-source-parity.json` | Current package files equal the bundled wheel payload |

The high-resolution final run verifies 42 artifacts; the core-wheel model run verifies 20. Earlier high-resolution development artifacts remain under differently named paths; the final helper and final input use the corrected inclusive-drawing/exclusive-label boundary. The tiled path preserves the configured model's native preprocessing; it does not claim to make a tiny test model accurate on aerial images.

## Core-only installation method

A fresh venv without system-site-packages was created. Already-installed Pydantic-family package files and distribution metadata were copied into it offline, and the current wheel was installed with `pip --no-index --no-deps`. Its controller could generate fixtures and plan six arms without ML/geospatial packages. For actual model execution it launched a different interpreter with this repository available to the worker. The controller package remained the installed wheel and the controller did not import Torch, NumPy or Pillow.

This tests an installed wheel and real process/environment separation. It is not a network-resolved clean installation, an MMDetection run, another OS/hardware platform, or independent external reproduction.

## Reference and numerical boundaries

- Official COCO wrapper code exists; actual reference parity is NOT_RUN because pycocotools is unavailable. Diagnostic precision/recall is not COCO AP.
- The DOTA bridge requires the user's explicitly trusted and hashed official/reference module and its dependencies. Actual official invocation is NOT_RUN. Local polygon geometry cross-checks are not benchmark certification.
- Real MMDetection/MMCV, published MM checkpoint/data pairs, contemporary external model ecosystems, and pretrained foundation backbones were not executed.
- All model fixtures are randomly initialized small native detectors on generated images. No scientific causal or accuracy result is inferred.
- CPU checkpoint/resume and prediction tolerances are scoped to the recorded environment. No cross-GPU bitwise guarantee follows.

## Re-run commands

```bash
python scripts/verify_distribution.py
python tools/run_checks.py --suite fast --out evidence/recheck-fast
python tools/run_checks.py --suite native --out evidence/recheck-native
python tools/run_checks.py --suite all --out evidence/recheck-all
python tools/audit_source.py --out evidence/source-audit-recheck.json
python tools/summarize_verification.py evidence/recheck-all/results.xml --out evidence/recheck-summary.json
```

`run_checks` records the actual process result without installing packages or downloading data. Optional tests skip with explicit reasons when their dependencies are absent. The summary tool reports observed test counts only, not scientific compatibility or overall completion. The source audit checks Python syntax and inventories review-relevant calls/installed distributions; it is not a live CVE lookup, penetration test, ruff run, mypy run or security certification. Hosted CI configuration is provided but was not executed here.

## Known remaining implementation limits

The native backend is the small torchvision conformance detector, not a modern DETR/Ultralytics training adapter. No usable native oriented-detector training backend, foundation-backbone experiment, ONNX/TensorRT export/runtime adapter, production sandbox, multi-GPU runner, full transitive environment-lock solver, or gigapixel GeoTIFF training pipeline has been added. Reference and research data blockers are separate from GPU needs. A CPU machine with appropriate assets can close some reference gates later, but cannot close them retroactively for this build.

Hash integrity is not signed authorship. Local approval ledgers are research-policy accounting, not a hostile-user security boundary. Source/checkpoint/data licensing remain distinct. Evidence paths may record this build's original absolute locations; those are historical records, not portable preconfigured invocations. Generate fresh local examples and select local worker/data paths for reruns.
