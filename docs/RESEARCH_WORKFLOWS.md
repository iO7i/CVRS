# Research workflows and boundaries — 0.3

## Training controls

| Arm | Main stage | Additional stage/group | What the control addresses |
|---|---|---|---|
| R | Real only | None | Real baseline |
| S | Synthetic only | None | Source-only transfer probe |
| R+S | Real + weighted synthetic forward groups | Same optimizer update | Supplementation at preserved primary real exposures |
| S->R | Synthetic pretraining | Real fine-tuning, optimizer/scheduler reset | Synthetic pretraining |
| R-replay | Primary real group | Weighted additional real group | More sample exposure/loss-group control for supplementation |
| R->R | Real pretraining | Real fine-tuning, reset | Additional pretraining exposure control |

Primary real IDs and forward RNG seeds match between R, R+S and R-replay.
Weights and gradients subsequently diverge, so equal sample streams do not imply
equal proposals/gradients. The tiny native worker has no stochastic image
augmentation. R->R requires equal real/synthetic per-update counts to match its
pretraining counterpart. Loss weights are nominal; gradient influence is NOT
measured. GPU time is unknown here, not zero. End-to-end wall time includes process
startup and cannot be marketed as steady-state inference latency.

Campaigns require an explicit primary-metric JSON pointer and identical declared
data/evaluation contracts across backends. Different model/pretraining histories
remain potentially confounded. No model ranking is automatically a causal claim.

## Split governance

Dataset roles are `train`, `dev`, `selection`, and `locked_test`. Training accepts
only train-role samples. Campaigns accept explicitly chosen dev/selection roles;
selection use is recorded in each run. Threshold-sweeping diagnostics are dev-only.
A normal controller `run` cannot execute a locked test using the old authorization
JSON alone. Use a hash-chained approval ledger:

1. Prepare an inference-only ExperimentSpec and compute its experiment identity.
2. Prepare `AccessApproval` with that identity, dataset identity, split, person,
   reason and allowed number of uses. No person/account authentication is implied.
3. `cvrs ledger approve access.jsonl --approval approval.json`
4. `cvrs ledger final-run final.json --ledger access.jsonl --approval-digest DIGEST --out final-runs`
5. `cvrs ledger test-report access.jsonl`

An attempted execution consumes the approval before model execution; a failure
never restores its usage counter. The sealed run contains its receipt. This is
local accountability, not encryption or hostile-code sandboxing. Direct file or
low-level evaluator access outside these APIs cannot be observed. Protect actual
secrets and test custody separately. An externally retained ledger head is needed
to detect a complete rewrite or tail truncation by a filesystem owner.

Confirmatory campaign metadata requires at least three fresh seeds and a selection
record digest. Seed history is the provided local ledger and explicit previous
seed list; a separate unshared campaign cannot magically be detected. Seed reports
list every missing/failed pair. A bootstrap with very few seeds is unstable and
is not a substitute for power analysis or independent replication.

## Geometry and geospatial data

Horizontal boxes are continuous xyxy in original-image pixels, no `+1`. Tiles
preserve crop, scale, padding, valid region, and source identities. Predictions
from padding are explicitly clipped/rejected; overlap NMS records suppressed
sources. Whole-image labels are not silently converted to empty tile ground truth.

Oriented interchange uses convex quadrilateral polygons. Coordinate system: x
right, y down. Clockwise winding is canonicalized and angle direction/unit are
explicit. `le90`, `le135`, `oc_positive` and `oc_negative` are named conversion
conventions; the code does not guess a framework's convention. Nonuniform affine
transforms may produce a parallelogram, which must not be represented as a
rectangle-plus-angle. Convex diagnostic IoU has numerical tests against Shapely;
this is not official DOTA metric parity.

GeoReference requires a declared CRS and invertible six-coefficient affine
transform. Pixel coordinates reference corners; pixel-center conversion is an
explicit option. Optional reprojection uses pyproj with declared xy axis order.
A world polygon is not automatically an RFC7946 GeoJSON object. GeoTIFF windows
require three explicit band choices and a fixed value range. Their uint8 display
conversion does not preserve original sensor radiometry. Nodata is accompanied
by a validity mask. No automatic physical GSD/altitude is inferred.

## Model/adapter limitations

The existing MM worker supports inference, not generic heritage training. The
campaign runner exposes unsupported operations rather than silently replacing a
backend. Its executed six-arm campaign uses the native conformance detector only.
External plugins are explicit trusted scripts with pre/post hashes, selected
interpreters and a versioned protocol; no discovery/install hooks are run. A new
real model adapter still needs its own preprocessing, checkpoint, training,
numerical, and reference-evaluation certification.

## Reports versus experiments

Domain, tiling-policy, seed, oriented, tiny-object and output-parity reports describe
their recorded inputs. Output-file parity is useful for later export validation,
but no ONNX/TensorRT runtime is implemented or certified by the parity auditor.
Foundation-backbone and deployment comparison reports can consume future supplied
runs; this release does not supply those experiments. Unknown inputs and results
remain unknown, not benchmark-looking zeros.
