# Acceptance gates

## Foundation gates retained from Slice 01

| Gate | Status | Evidence / limitation |
|---|---|---|
| G0 Boundaries | PASS | Lightweight core, isolated worker boundary, explicit non-goals/trust |
| G1 Contracts | PASS | 24 schemas, semantic validation, stable hashing, core-only imports |
| G2 Real execution | PASS | Genuine CPU detector, real optimizer steps, checkpoint round-trip/resume tests |
| G3 Evaluation | PARTIAL | Diagnostics verified; official COCO parity code exists but pycocotools unavailable here |
| G4 Provenance | PASS | Verifiable bundles, failure evidence, tamper/missing-artifact detection |
| G5 Heritage | PARTIAL / execution blocked | Standalone bridge and conformance evidence implemented; real MM stack/checkpoint absent |
| G6 Protocols | PASS | Existing four-arm CPU protocol evidence retained |
| G7 External usability | PARTIAL | Packaged/clean-environment checks by same builder; external reproduction not performed |

## Slice 02 gates

| Gate | Status in 0.2.0a1 | What is actually proven |
|---|---|---|
| G2.0 Environment isolation | PARTIAL | stdlib-only heritage shim executes under `python -S` and does not import the controller; no genuine conflicting MM env available |
| G2.1 Real heritage execution | BLOCKED_DEPENDENCY / BLOCKED_ASSET | worker implementation exists; MMDetection/MMCV/MMEngine and trusted real checkpoint are absent |
| G2.2 Heritage output fidelity | PARTIAL | exact native→canonical parity is conformance-tested against MM-shaped modules; real MM outputs not executed here |
| G2.3 Reference evaluation | BLOCKED_DEPENDENCY | direct-vs-wrapper pycocotools parity implementation exists; pycocotools is absent and package-index DNS failed |
| G2.4 Published-result reproduction | BLOCKED_DEPENDENCY / BLOCKED_ASSET | H4 logic requires exact data/protocol/config/checkpoint/source identity; no real published run was fabricated |
| G2.5 Cross-framework execution | PARTIAL | cross-run infrastructure and genuine modern CPU path work; real MM side is blocked |
| G2.6 Comparability honesty | PASS | measurement comparability is explicitly separated from training fairness |
| G2.7 Heritage evidence bundle | PARTIAL | conformance evidence captures resolved config/native/canonical/audit metadata; no real-MM H2+ bundle |
| G2.8 Independent heritage verification | NOT_RUN | same builder cannot claim independent external reproduction |

`PARTIAL` is deliberate: a mock/conformance run never upgrades a real heritage certification.
GPU absence is **not** the blocker for G2.1/G2.3/G2.4 in this environment.
