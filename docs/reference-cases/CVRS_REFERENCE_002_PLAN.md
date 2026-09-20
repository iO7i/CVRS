# CVRS Reference Qualification 002 — Cross-Generation CV Interoperability

Status: `PLANNED_NOT_EXECUTED`

This is the final flagship qualification before the public alpha. It is not a
new scientific benchmark and does not change Reference Qualification 001.

## Public proof

> One reproducible vision campaign can span incompatible legacy OpenMMLab,
> modern OpenMMLab, foundation-model, deployment, ecosystem, and geospatial
> stacks without merging their environments or losing artifact provenance.

## Frozen rules

- Reference Qualification 001 and DesertSynth remain immutable.
- Each mandatory lane needs a direct native reference path and a CVRS path.
- Mock outputs cannot satisfy a native-execution gate.
- Raw native outputs are preserved before canonical conversion.
- Canonical geometry remains strict; native semantics use explicit native paths.
- Prompt sources, model revisions, checkpoints, data selections, and evaluators are pinned before expansion.
- No protected or sealed data is used.
- No paid execution, gated model access, or large download starts before H0.
- A failed mandatory lane remains red unless its actual defect is fixed and rerun.
- No result is promoted from implementation presence alone.

## Mandatory lanes

| Lane | Native stack | Qualification target |
| --- | --- | --- |
| OML-LEGACY | MMDetection 2.x | Published detector inference/evaluation in its own 1.x-era MMCV environment |
| OML-MODERN | MMDetection 3.x | RTMDet-family native inference/evaluation under MMEngine/MMCV 2.x |
| OML-ROTATED | MMRotate 0.x | Real OBB inference and oriented-coordinate preservation |
| OML-SEG | MMSegmentation 1.x | Real semantic label map and ignore-label/evaluator preservation |
| OML-DEPLOY | MMDeploy 1.x | Selected MMDetection model native vs ONNX Runtime; TensorRT if H0 provides CUDA |
| ULTRALYTICS | Current pinned YOLO26 | Native detector plus ONNX deployment parity |
| GROUNDING | Grounding DINO | Predeclared text prompts, original-coordinate boxes, prompt provenance |
| SAM3 | SAM 3.x | Box/spatial-prompt to real instance masks; gated checkpoint access recorded |
| DINOV3 | DINOv3 | Global and selected dense feature artifacts with immutable model identity |
| TORCHGEO | TorchGeo | Real georeferenced raster windows with CRS/band/window lineage |
| SUPERVISION | Supervision SDK | Native SDK roundtrip for supported geometry with loss report |
| FIFTYONE | FiftyOne SDK | Native SDK roundtrip and visualization metadata with loss report |
| CLEANROOM | CVRS-only controller | Capsule verification/browser generation without model runtimes |

## Data anchors

- COCO 2017 validation: deterministic 128-image HBB/mask anchor; 32-image shared composition/deployment subset.
- Open Images V7: deterministic 64-image open-vocabulary/licensing stress subset; dataset-native semantics only.
- ADE20K: deterministic 32-image semantic-segmentation subset.
- DOTA: 16 source images, at most 64 derived tiles, with original/tile coordinate lineage.
- Geospatial: one real public GeoTIFF area of interest, at most 16 windows.

These are bounded qualification subsets, not benchmark claims. Dataset-native
evaluation semantics take precedence over convenient format conversion.

## Cross-worker compositions

1. Grounding DINO boxes -> SAM 3 masks.
2. Ultralytics boxes -> SAM 3 masks.
3. Selected MMDetection model -> MMDeploy ONNX Runtime.
4. Selected Ultralytics model -> ONNX Runtime.

Every boundary records source sample identity, raw producer artifact, coordinate
frame, consumer input contract, transformation receipt, and content hash.

## Acceptance gates

The machine-readable contract enumerates R2.01-R2.25. The critical invariants are:

- native and CVRS paths execute independently enough to expose shared-adapter mistakes;
- no incompatible framework environments are merged merely to simplify setup;
- evaluator identity and dataset selection are immutable before result inspection;
- native-to-canonical conversions have zero silent loss;
- explicit native-preserving paths are used when canonical semantics cannot represent an upstream artifact;
- deployment comparisons record score/coordinate drift and not merely successful export;
- all real SDK bridges are executed, not inferred from package presence;
- clean-room verification succeeds without ML packages;
- tamper and missing-evidence probes behave distinctly;
- every unexecuted or blocked lane stays visibly unexecuted or blocked.

## Human gates

### H0 — asset / runtime / spend approval

Before substantial downloads or any paid compute, produce one packet containing:
exact candidate revisions, licenses/access terms, expected download/storage,
local/cloud execution plan, expected GPU hours/cost, and fallback behavior.

### H1 — small-stage visual review

After 1-2 image smoke and eight-image expansion, show representative native and
CVRS outputs plus every unexplained mismatch. Expansion requires explicit approval.

### H2 — final release review

Show the final per-lane matrix, remaining red/yellow limitations, public demo
media, exact claims proposed for README/release notes, and release artifacts.

## Stop condition

After RQ002 and alpha hardening are sealed, do not add another qualification
campaign before release. External users become the next source of requirements.
