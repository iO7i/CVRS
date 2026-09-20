# Slices 1–5: frozen engineering closure

The 69 rows below are the frozen accepted closure denominator. They are not 69 equally weighted scientific gates. Scope limits remain part of each contract; optional operations are not certified merely because code exists.

## S1

### S1.01 — Versioned stable facade and explicit lifecycle

**Entry:** `cvrs closure policy`

**Implementation:** `src/cvsubstrate/v1.py`, `src/cvsubstrate/foundation/policy.py`

**Boundary:** Only the declared facade/serialized contracts receive the v1 compatibility policy; native implementation internals stay provisional.

### S1.02 — Historical artifact readers and explicit migrations

**Entry:** `cvrs closure compatibility; cvrs migrate`

**Implementation:** `src/cvsubstrate/foundation/compatibility.py`, `src/cvsubstrate/contracts/migrations.py`

**Boundary:** Six exact preserved v0.5 artifacts are checked. Unknown/future versions are rejected, not fabricated.

### S1.03 — DAG cancellation, retries, recovery, concurrency and invalidation

**Entry:** `cvrs graph run`

**Implementation:** `src/cvsubstrate/foundation/lifecycle.py`, `src/cvsubstrate/experiments/dag.py`, `src/cvsubstrate/execution/process.py`

**Boundary:** Local DAG uses an OS-held writer lock. Nodes requiring native code remain trusted operations.

### S1.04 — Atomic content-addressed writes, pinning and safe garbage collection

**Entry:** `cvrs closure gc`

**Implementation:** `src/cvsubstrate/artifacts/managed.py`, `src/cvsubstrate/artifacts/store.py`

**Boundary:** Only unpinned objects older than the minimum age can be removed after an exact dry-run plan digest; no cloud store.

### S1.05 — Capsule dependency closure and readiness

**Entry:** `cvrs closure dependencies; cvrs capsule create --dependencies`

**Implementation:** `src/cvsubstrate/artifacts/dependencies.py`, `src/cvsubstrate/artifacts/capsule.py`

**Boundary:** Embedded/external/optional/restricted identities are distinct. Missing external assets do not pretend to be installed.

### S1.06 — Negotiated sessions, correlation, heartbeats and cancellation

**Entry:** `cvsubstrate.v1.run_session`

**Implementation:** `src/cvsubstrate/execution/session.py`, `src/cvsubstrate/execution/session_runtime.py`

**Boundary:** Session 2 delegates to real protocol-1 workers; one active request per session, no hostile-code sandbox.

### S1.07 — Typed public failures across APIs and CLI

**Entry:** `cvrs closure --help`

**Implementation:** `src/cvsubstrate/errors.py`, `src/cvsubstrate/cli.py`, `src/cvsubstrate/cli_closure.py`

**Boundary:** Internal exceptions become structured public error categories; raw tracebacks are not the public protocol.

## S2

### S2.01 — Explicit MMDetection 2/3 and OneDL drivers

**Entry:** `heritage native operations`

**Implementation:** `src/cvsubstrate/worker_shims/mm_drivers.py`, `src/cvsubstrate/worker_shims/mmdetection_worker.py`

**Boundary:** Optional real MM environments are not installed/executed in this delivery.

### S2.02 — Config/module/environment dependency closure

**Entry:** `cvrs closure config`

**Implementation:** `src/cvsubstrate/heritage/closure.py`

**Boundary:** Static only in controller; dynamic imports are unresolved unless explicitly supplied. Secret environment values are not silently captured.

### S2.03 — Audited explicit tensor transformation rules

**Entry:** `cvrs closure checkpoint transform`

**Implementation:** `src/cvsubstrate/worker_shims/checkpoint_transform.py`, `src/cvsubstrate/heritage/checkpoint_v1.py`

**Boundary:** Rename/prefix/reshape/cast/drop/generate are explicit. This is not an automatic architecture converter.

### S2.04 — Checkpoint structural and numeric differences

**Entry:** `cvrs closure checkpoint diff`

**Implementation:** `src/cvsubstrate/worker_shims/checkpoint_transform.py`, `src/cvsubstrate/heritage/checkpoint_v1.py`

**Boundary:** Scalar/chunked tensor comparisons; no invented equivalence of different architectures.

### S2.05 — Finite native prediction-converter families

**Entry:** `cvrs heritage convert-predictions`

**Implementation:** `src/cvsubstrate/evaluation/converters.py`, `src/cvsubstrate/geometry/polygons.py`

**Boundary:** MM2/MM3/COCO/DOTA/UL/RF and rotated representations have explicit semantics, not all possible upstream result classes.

### S2.06 — Consumed batch/source/augmentation/loss/LR/update/checkpoint telemetry

**Entry:** `native telemetry; cvrs closure telemetry`

**Implementation:** `src/cvsubstrate/worker_shims/telemetry_runtime.py`, `src/cvsubstrate/worker_shims/mm_train_telemetry.py`

**Boundary:** Exact parent tracing needs supplied augmentation metadata; missing provenance stays partial. Per-source gradients are not measured.

### S2.07 — Distributed rank/shard accounting and consistency

**Entry:** `cvrs closure telemetry --world-size`

**Implementation:** `src/cvsubstrate/telemetry_v1.py`, `src/cvsubstrate/worker_shims/telemetry_runtime.py`

**Boundary:** Counts rank observations without multiplying global updates by world size. It is not an all-reduce verifier or distributed scheduler.

### S2.08 — Desired versus observed environment difference

**Entry:** `cvrs closure environment-diff`

**Implementation:** `src/cvsubstrate/environments/compare.py`, `src/cvsubstrate/environments/capture.py`

**Boundary:** Reports declared/observed values; does not install packages or certify an environment.

### S2.09 — Offline model-index catalogue ingestion

**Entry:** `cvrs closure model-index`

**Implementation:** `src/cvsubstrate/heritage/model_index.py`

**Boundary:** Imported entries are unverified; no model zoo downloads or automatic license assumptions.

### S2.10 — Preprocess/taxonomy/postprocess/training comparison

**Entry:** `Python normalization comparison; cvrs cross-framework`

**Implementation:** `src/cvsubstrate/evaluation/normalization.py`, `src/cvsubstrate/evaluation/cross_framework.py`

**Boundary:** Training fairness is distinct from a common evaluation protocol.

## S3

### S3.01 — Canonical OBB raster streaming and oriented merge

**Entry:** `cvrs closure stream`

**Implementation:** `src/cvsubstrate/streaming/tasks.py`, `src/cvsubstrate/worker_shims/task_stream_worker.py`

**Boundary:** No loss-inducing HBB conversion. Native UL OBB path requires a compatible local checkpoint; analytic OBB stream executed.

### S3.02 — Sparse mask streaming and cross-tile instance association

**Entry:** `cvrs closure stream`

**Implementation:** `src/cvsubstrate/streaming/tasks.py`, `src/cvsubstrate/vision/sparse_masks.py`

**Boundary:** Declared score-ordered cross-tile winner/union IoU policy; same-tile distinct instances are not automatically unioned.

### S3.03 — Disk-backed spatial prediction index

**Entry:** `cvsubstrate.v1.SpatialPredictionIndex`

**Implementation:** `src/cvsubstrate/streaming/tasks.py`

**Boundary:** SQLite R-tree and disk-backed raw/selected records; disk capacity is still required.

### S3.04 — Tile admission, byte/pixel budgets, recovery and RSS backpressure

**Entry:** `cvrs closure stream --resume`

**Implementation:** `src/cvsubstrate/streaming/tasks.py`, `src/cvsubstrate/streaming/raster.py`

**Boundary:** Bounds are CVRS-controlled buffers/cache/prediction records. Arbitrary model/GPU allocations cannot be hard-capped by this scheduler.

### S3.05 — Explicit coordinate/CRS/affine/nodata semantics

**Entry:** `GeoSceneSpec; streaming world export`

**Implementation:** `src/cvsubstrate/datasets/sensors.py`, `src/cvsubstrate/geometry/geospatial.py`, `src/cvsubstrate/streaming/tasks.py`

**Boundary:** World output declares CRS. Mask world output is explicitly an instance bounding region, not a fabricated precise polygon.

### S3.06 — Band units, order, scaling, normalization and model-channel contract

**Entry:** `SensorSpec; stream sensor config`

**Implementation:** `src/cvsubstrate/datasets/sensors.py`, `src/cvsubstrate/worker_shims/task_stream_worker.py`

**Boundary:** The bundled small native detector is three-channel; multispectral models must supply a matching predictor.

### S3.07 — Timestamp and temporal-stack lineage

**Entry:** `GeoSceneSpec`

**Implementation:** `src/cvsubstrate/datasets/sensors.py`

**Boundary:** Timezones required; metadata support, not video inference.

### S3.08 — Hierarchical synthetic scene/mesh/material/parent lineage

**Entry:** `cvrs closure lineage`

**Implementation:** `src/cvsubstrate/data/asset_lineage.py`

**Boundary:** Graph records source assets and parent relationships, not a running simulator.

### S3.09 — Cross-split asset/parent contamination checks

**Entry:** `cvrs closure lineage`

**Implementation:** `src/cvsubstrate/data/asset_lineage.py`

**Boundary:** Checks declared identities/hashes/ancestors, not an assertion that undisclosed contamination is impossible.

### S3.10 — Fairness/budget compilation and mismatches

**Entry:** `cvrs closure native-campaign plan`

**Implementation:** `src/cvsubstrate/campaigns/native.py`, `src/cvsubstrate/campaigns/dsl.py`

**Boundary:** Cannot simultaneously equalize unequal exposures/updates/epochs. Unsupported equality requirements prevent execution.

### S3.11 — Native MM/modern multi-stage campaign execution

**Entry:** `cvrs closure native-campaign run`

**Implementation:** `src/cvsubstrate/campaigns/native.py`, `src/cvsubstrate/worker_shims/native_campaign_worker.py`, `src/cvsubstrate/heritage/native_data.py`

**Boundary:** MM direct-CocoDataset recipes bind actual selected samples. Native UL/RF stages use epoch budgets; fixed-update source preservation is not silently promised.

### S3.12 — Actual stage checkpoint and dataset dependency edges

**Entry:** `native-campaign run --resume`

**Implementation:** `src/cvsubstrate/campaigns/native.py`, `src/cvsubstrate/worker_shims/native_campaign_worker.py`

**Boundary:** Exact parent checkpoint hashes and sealed completed stage evidence are required on resume.

### S3.13 — Explicit diagnostic plugin registry

**Entry:** `DomainMetricRegistry`

**Implementation:** `src/cvsubstrate/analysis/metric_plugins.py`

**Boundary:** Plugin registration is explicit trusted code; no silent arbitrary module execution.

### S3.14 — Optical/SAR/multispectral sensor contracts

**Entry:** `SensorSpec`

**Implementation:** `src/cvsubstrate/datasets/sensors.py`

**Boundary:** Sensor contracts do not manufacture model architectures or real sensor data.

### S3.15 — Inspectable metric population predicates and IDs

**Entry:** `cvrs closure slice; cvrs closure reevaluate`

**Implementation:** `src/cvsubstrate/analysis/population.py`, `src/cvsubstrate/analysis/metric_plugins.py`, `src/cvsubstrate/research/evaluators.py`

**Boundary:** Image predicates retain the complete negative universe and all selected-image annotations. Object-level official metrics use reference area/ignore semantics, not silent object deletion.

## S4

### S4.01 — Complete finite PromptSet representation

**Entry:** `PromptSet; closure prompts negotiate`

**Implementation:** `src/cvsubstrate/vision/prompts.py`

**Boundary:** Text/points/boxes/masks/reference images/reference regions/concepts represented. Each native model declares its actual supported subset.

### S4.02 — Iterative prompt trajectories and grouped corrections

**Entry:** `closure prompts trajectory/continue`

**Implementation:** `src/cvsubstrate/vision/trajectories.py`, `src/cvsubstrate/worker_shims/vision_drivers.py`

**Boundary:** Previous prompt and prediction hashes, model identity and target grouping are retained.

### S4.03 — Reference image/region prompt identities

**Entry:** `ReferenceAsset; register_prompt_backend`

**Implementation:** `src/cvsubstrate/vision/prompts.py`, `src/cvsubstrate/vision/assets.py`

**Boundary:** Stock SAM/GroundingDINO do not gain unsupported exemplar capabilities. Reference-capable plugins explicitly negotiate them.

### S4.04 — Explicit concept hierarchy, aliases and phrase mapping

**Entry:** `ConceptOntology; evaluate_open_set`

**Implementation:** `src/cvsubstrate/vision/ontology.py`

**Boundary:** No automatic semantic equivalence of truck/pickup/vehicle.

### S4.05 — Prompt provenance and oracle-aware comparability

**Entry:** `closure compare; closure reevaluate`

**Implementation:** `src/cvsubstrate/vision/prompts.py`, `src/cvsubstrate/vision/ontology.py`, `src/cvsubstrate/vision/diagnostics.py`

**Boundary:** Oracle metadata is propagated from actual canonical prompt records, not overridden by a report flag.

### S4.06 — Known/unknown/unmapped grounding diagnostics

**Entry:** `evaluate_open_set; closure reevaluate`

**Implementation:** `src/cvsubstrate/vision/ontology.py`

**Boundary:** Explicit protocol-defined diagnostics, not a claim of official universal open-set AP.

### S4.07 — Dense/RLE/polygon mask interchange

**Entry:** `mask transforms/interchange API`

**Implementation:** `src/cvsubstrate/vision/masks.py`, `src/cvsubstrate/vision/sparse_masks.py`

**Boundary:** Sparse coordinate transforms avoid full-scene materialization; polygon rasterization uses the optional geospatial dependency and preserves holes.

### S4.08 — Cross-tile mask association policy

**Entry:** `closure stream with mask_policy`

**Implementation:** `src/cvsubstrate/streaming/tasks.py`, `src/cvsubstrate/vision/sparse_masks.py`

**Boundary:** Greedy winner/union under explicit IoU, not perfect object identity or embedding-based tracking.

### S4.09 — Mask boundary/IoU/population diagnostics and reference routing

**Entry:** `closure reevaluate; vision evaluate-masks`

**Implementation:** `src/cvsubstrate/vision/diagnostics.py`, `src/cvsubstrate/vision/evaluation.py`, `src/cvsubstrate/research/evaluators.py`

**Boundary:** Custom boundary scores stay distinct from official COCO segmentation metrics.

### S4.10 — Explicit finite native vision drivers

**Entry:** `vision run; closure prompts`

**Implementation:** `src/cvsubstrate/worker_shims/vision_drivers.py`, `src/cvsubstrate/worker_shims/vision_worker.py`

**Boundary:** HF GroundingDINO/SAM/SAM2/YOLO-World/UL masks delegate native APIs. Native optional models remain unexecuted here.

### S4.11 — Composite model/processor/tokenizer/config asset identity

**Entry:** `closure assets`

**Implementation:** `src/cvsubstrate/vision/assets.py`, `src/cvsubstrate/vision/service.py`

**Boundary:** Only declared local files and complete allowlisted directories are accepted; no model-download fallback.

### S4.12 — Content-based model identity/cache inputs

**Entry:** `vision run; closure assets`

**Implementation:** `src/cvsubstrate/vision/assets.py`, `src/cvsubstrate/worker_shims/vision_worker.py`

**Boundary:** Model names alone are not content identity; dependency/config receipts remain explicit.

### S4.13 — Task/protocol/prompt-aware comparison

**Entry:** `cvrs closure compare`

**Implementation:** `src/cvsubstrate/vision/diagnostics.py`, `src/cvsubstrate/vision/grounding.py`

**Boundary:** No common ranking of incomparable AP, prompt-IoU, oracle-conditioned masks and grounded detection.

## S5

### S5.01 — Structured scientific claims

**Entry:** `closure registry add --kind claim`

**Implementation:** `src/cvsubstrate/research/claims.py`

**Boundary:** Population/intervention/comparator/metric/conditions are explicit; not NLP claim extraction.

### S5.02 — Semantic claim scope fingerprint

**Entry:** `ScientificClaim.scope_fingerprint`

**Implementation:** `src/cvsubstrate/research/claims.py`

**Boundary:** Title/author are not scope; protocol/data/model/conditions/purpose are scope.

### S5.03 — Supported/contradicted/not-supported/inconclusive assertions

**Entry:** `EffectObservation.assess`

**Implementation:** `src/cvsubstrate/research/claims.py`

**Boundary:** Point estimates do not become statistical significance.

### S5.04 — Baseline/treatment/effect/uncertainty records

**Entry:** `EffectObservation`

**Implementation:** `src/cvsubstrate/research/claims.py`

**Boundary:** Uncertainty interval needs a stated method; no invented confidence intervals.

### S5.05 — Typed acyclic evidence graph

**Entry:** `closure registry edge`

**Implementation:** `src/cvsubstrate/research/federated.py`, `src/cvsubstrate/research/claims.py`

**Boundary:** Cycles and dangling references are rejected, including after merging independent copies.

### S5.06 — Artifact-level run/weight/prediction/evaluation lineage

**Entry:** `closure capture-comparison; register_evaluation`

**Implementation:** `src/cvsubstrate/research/capture_v2.py`, `src/cvsubstrate/research/evaluators.py`

**Boundary:** Verified original run files and exact metric paths are required; no invented execution receipts.

### S5.07 — Optional Ed25519 record/exchange signatures

**Entry:** `closure keygen; registry sign/export/merge`

**Implementation:** `src/cvsubstrate/research/signing.py`, `src/cvsubstrate/research/federated.py`

**Boundary:** Private keys never bundled; signed bytes are not proof of true computation or independent identity.

### S5.08 — Provider-neutral actor identity and attestations

**Entry:** `ActorIdentity`

**Implementation:** `src/cvsubstrate/research/claims.py`

**Boundary:** Public-key/ORCID/GitHub/email labels remain self-asserted unless explicit review evidence accompanies them.

### S5.09 — Concurrent local writers and independent-copy merges

**Entry:** `closure registry merge`

**Implementation:** `src/cvsubstrate/research/federated.py`

**Boundary:** SQLite transaction locking locally; deterministic immutable-record union. No hosted multi-machine scheduler.

### S5.10 — Signed/unsigned exchange bundles and idempotent import

**Entry:** `closure registry export/merge`

**Implementation:** `src/cvsubstrate/research/federated.py`

**Boundary:** Imported branch histories survive merge. Trust keys are supplied explicitly.

### S5.11 — Evidence-derived R0–R5 reproduction levels

**Entry:** `closure registry status`

**Implementation:** `src/cvsubstrate/research/federated.py`

**Boundary:** Original/reevaluation is not a reproduction; levels need receipts and the declared evidence rules.

### S5.12 — Independence along five explicit axes

**Entry:** `registry review records/status`

**Implementation:** `src/cvsubstrate/research/claims.py`, `src/cvsubstrate/research/federated.py`

**Boundary:** Operator/machine/environment/implementation/organization are review attestations, not authentication.

### S5.13 — Artifact-only HBB/OBB/mask/grounding/population re-evaluation

**Entry:** `closure reevaluate; authorize-evaluation`

**Implementation:** `src/cvsubstrate/research/evaluators.py`, `src/cvsubstrate/research/task_access.py`

**Boundary:** Official evaluators use optional workers; custom diagnostics stay named. Locked-test use is charged before the attempt.

### S5.14 — Lossless preservation of legacy registry versions

**Entry:** `closure registry migrate`

**Implementation:** `src/cvsubstrate/research/federated.py`

**Boundary:** Legacy contents are preserved as explicit legacy records/objects, not silently elevated to structured verified claims.

### S5.15 — Whole-export record/object/edge/signature integrity

**Entry:** `closure registry verify/merge`

**Implementation:** `src/cvsubstrate/research/federated.py`

**Boundary:** Detects changed/deleted/conflicting records and missing evidence; external trust roots are optional and explicit.

### S5.16 — Structured registry queries

**Entry:** `closure registry query --filters --minimum-level`

**Implementation:** `src/cvsubstrate/research/federated.py`

**Boundary:** Queries local structured metadata and evidence-derived status; no internet identity inference.

### S5.17 — Static claim/attempt/lineage/export views

**Entry:** `closure registry site`

**Implementation:** `src/cvsubstrate/research/federated.py`

**Boundary:** Escaped static files only, not a publicly hosted site.

## X

### X.01 — Finite protocol/API policy freeze

**Entry:** `closure policy`

**Implementation:** `src/cvsubstrate/foundation/policy.py`, `src/cvsubstrate/v1.py`

**Boundary:** No claim that future unknown schemas or upstream APIs can be certified today.

### X.02 — Independent package/schema/worker/registry versions

**Entry:** `COMPONENT_VERSIONS`

**Implementation:** `src/cvsubstrate/foundation/identity.py`

**Boundary:** Package 0.5.1a1 is independent from stable contract and exchange major versions.

### X.03 — Namespaced canonical identities

**Entry:** `closure identity`

**Implementation:** `src/cvsubstrate/foundation/identity.py`

**Boundary:** Exact declared values are hashed; no lossy float/taxonomy/model normalization.

### X.04 — Shared explicit provenance-edge vocabulary

**Entry:** `ProvenanceGraph; EvidenceEdge`

**Implementation:** `src/cvsubstrate/foundation/identity.py`, `src/cvsubstrate/research/claims.py`

**Boundary:** Graph directions are preserved; not an inference engine that invents causal relationships.

### X.05 — Explicit hidden/local dependency inspection

**Entry:** `closure config/assets/dependencies`

**Implementation:** `src/cvsubstrate/heritage/closure.py`, `src/cvsubstrate/vision/assets.py`, `src/cvsubstrate/artifacts/dependencies.py`

**Boundary:** Unresolved dynamic imports and missing external dependencies remain visible blockers, not assumed complete.

### X.06 — Canonical serialization rules

**Entry:** `canonical_bytes; content_id`

**Implementation:** `src/cvsubstrate/provenance/io.py`, `src/cvsubstrate/foundation/identity.py`

**Boundary:** CVRS sorted finite Python JSON v1, explicitly not RFC8785/JCS.

### X.07 — Large/restricted artifact lifecycle and reachability

**Entry:** `closure gc; capsule commands`

**Implementation:** `src/cvsubstrate/artifacts/managed.py`, `src/cvsubstrate/artifacts/dependencies.py`, `src/cvsubstrate/artifacts/capsule.py`

**Boundary:** Local immutable objects, pinning and dependency manifests; no automatic distribution of restricted weights/data.

