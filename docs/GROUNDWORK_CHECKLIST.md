# Groundwork checklist — 0.4.0a1

Implementation-path inventory, not a certification score. Scope is explicit for each row.

## F.A — Schema evolution and migrations

Entry: `schema list/inspect/validate; migrate; migrate-run`.

Code: `src/cvsubstrate/schemas/registry.py`, `src/cvsubstrate/contracts/migrations.py`

Registered migrations only; no invented conversion of unknown schemas.

## F.B — External plugin SDK

Entry: `plugin scaffold/register/inspect/validate/conformance/run`.

Code: `src/cvsubstrate/adapters/sdk.py`, `src/cvsubstrate/adapters/conformance.py`, `src/cvsubstrate/worker_shims/plugin_worker.py`

Scaffold validates JSON until author implements native operations; explicit trust required.

## F.C — Capability negotiation

Entry: `plugin negotiate`.

Code: `src/cvsubstrate/adapters/sdk.py`, `src/cvsubstrate/contracts/groundwork.py`

Requirements checked against declared capabilities; not native execution certification.

## F.D — Local execution DAG

Entry: `graph plan/run/actions`.

Code: `src/cvsubstrate/experiments/dag.py`, `src/cvsubstrate/experiments/actions.py`

Named outputs, artifacts, resume, safe retries, dependency failures and invalidation; single host.

## F.E — Content-addressed cache

Entry: `artifact/cache put/get/verify/exists`.

Code: `src/cvsubstrate/artifacts/store.py`, `src/cvsubstrate/experiments/dag.py`

Hashes include declared inputs and code/environment for action caches; no automatic training cache.

## F.F — Artifact store abstraction

Entry: `artifact put/get/verify/exists`.

Code: `src/cvsubstrate/artifacts/store.py`

Local filesystem implementation; cloud stores are future adapters.

## F.G — Environment capture/import

Entry: `environment capture/import/capsule`.

Code: `src/cvsubstrate/environments/capture.py`, `src/cvsubstrate/heritage/capsule.py`

pip/uv/conda/explicit/Docker; measured versus declared; hardware not silently probed/certified.

## F.H — Structured event/failure model

Entry: `run; graph run`.

Code: `src/cvsubstrate/events.py`, `src/cvsubstrate/execution/runner.py`, `src/cvsubstrate/experiments/dag.py`

Controller observations and hash-chain lifecycle, not fabricated internal model telemetry.

## F.I — Secrets and portable-path sanitization

Entry: `automatic logs/events/environment sanitation`.

Code: `src/cvsubstrate/security.py`, `src/cvsubstrate/provenance/bundle.py`, `src/cvsubstrate/execution/process.py`

Best effort credential/path redaction; do not treat as hostile-code containment.

## F.J — Research capsules

Entry: `capsule create/validate/inspect/archive/materialize`.

Code: `src/cvsubstrate/artifacts/capsule.py`

Safe archive extraction; explicit external references; no automatic assets/environment installation.

## S2.A — Heritage import wizard

Entry: `heritage import`.

Code: `src/cvsubstrate/heritage/wizard.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S2.B — MM2/MM3/OneDL profiles

Entry: `heritage profiles; run`.

Code: `src/cvsubstrate/heritage/profiles.py`, `src/cvsubstrate/worker_shims/mmdetection_worker.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S2.C — Environment generators

Entry: `environment capsule; heritage import`.

Code: `src/cvsubstrate/heritage/capsule.py`, `src/cvsubstrate/heritage/wizard.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S2.D — Config archaeology

Entry: `heritage graph/import`.

Code: `src/cvsubstrate/heritage/importer.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S2.E — Native-result import

Entry: `heritage convert-predictions/trusted-import`.

Code: `src/cvsubstrate/evaluation/converters.py`, `src/cvsubstrate/worker_shims/unsafe_import_worker.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S2.F — Prediction converter registry

Entry: `heritage convert-predictions`.

Code: `src/cvsubstrate/evaluation/converters.py`, `src/cvsubstrate/geometry/polygons.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S2.G — Checkpoint identity and explicit conversion

Entry: `checkpoint inspect/convert`.

Code: `src/cvsubstrate/checkpoints.py`, `src/cvsubstrate/worker_shims/checkpoint_worker.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S2.H — Heritage catalogue tooling

Entry: `heritage catalogue list/search/add/docs`.

Code: `src/cvsubstrate/heritage/catalogue_tools.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S2.I — Published-result metadata

Entry: `heritage catalogue; heritage certify`.

Code: `src/cvsubstrate/heritage/catalogue.py`, `src/cvsubstrate/heritage/catalogue_tools.py`, `src/cvsubstrate/execution/heritage.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S2.J — Isolated evaluator worker

Entry: `run/evaluate --evaluator-python; dota-reference`.

Code: `src/cvsubstrate/evaluation/service.py`, `src/cvsubstrate/worker_shims/coco_reference_worker.py`, `src/cvsubstrate/evaluation/reference_dota.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S2.K — Modern detector native adapters

Entry: `model predict/train-native/export; run`.

Code: `src/cvsubstrate/adapters/modern.py`, `src/cvsubstrate/worker_shims/modern_detector_worker.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S2.L — Cross-framework comparison

Entry: `compare; cross-framework`.

Code: `src/cvsubstrate/evaluation/cross_framework.py`, `src/cvsubstrate/evaluation/compare.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S2.M — Evidence-scoped H0-H5 certification

Entry: `heritage certify/certify-training/train-native`.

Code: `src/cvsubstrate/execution/heritage.py`, `src/cvsubstrate/heritage/training.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S2.N — Licensing and attribution

Entry: `licenses report`.

Code: `src/cvsubstrate/licensing.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S2.O — Catalogue documentation generator

Entry: `heritage catalogue docs`.

Code: `src/cvsubstrate/heritage/catalogue_tools.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S3.A — OBB task and native conventions

Entry: `model predict-obb/train-obb; geometry`.

Code: `src/cvsubstrate/contracts/research.py`, `src/cvsubstrate/geometry/polygons.py`, `src/cvsubstrate/adapters/oriented.py`, `src/cvsubstrate/worker_shims/obb_worker.py`

Canonical quadrilateral geometry, import/export/eval and optional native UL OBB job code. Real OBB checkpoint execution not verified.

## S3.B — Reference oriented evaluator

Entry: `dota-reference`.

Code: `src/cvsubstrate/evaluation/reference_dota.py`, `src/cvsubstrate/worker_shims/dota_reference_worker.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S3.C — Geospatial manifests/readers

Entry: `dataset inspect-geo/geo-manifest; geotiff`.

Code: `src/cvsubstrate/datasets/geospatial.py`, `src/cvsubstrate/data/geotiff.py`, `src/cvsubstrate/contracts/groundwork.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S3.D — Pixel/world mapping and exports

Entry: `dataset export-world`.

Code: `src/cvsubstrate/geometry/geospatial.py`, `src/cvsubstrate/datasets/geospatial.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S3.E — Six aerial-format readers

Entry: `dataset import/materialize`.

Code: `src/cvsubstrate/datasets/importers.py`, `src/cvsubstrate/datasets/materialize.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S3.F — Multi-scale image planner/execution

Entry: `large plan/run`.

Code: `src/cvsubstrate/data/large.py`, `src/cvsubstrate/execution/large.py`

Pillow multi-scale execution; advisory tile batch/memory estimates, not bounded-memory gigapixel streaming. Rasterio windows are separate.

## S3.G — Merge plugins

Entry: `large merge`.

Code: `src/cvsubstrate/geometry/merge.py`

NMS/SoftNMS/WBF/oriented/keep-all are explicit diagnostic merge policies; no official benchmark parity inferred.

## S3.H — Tiny-object metrics

Entry: `size-evaluate; tiny-evaluate`.

Code: `src/cvsubstrate/evaluation/object_size.py`, `src/cvsubstrate/evaluation/tiny.py`

Custom AP/size/FPPI diagnostics have their own definitions and are not labeled official COCO/DOTA AP.

## S3.I — Declarative domain slicing

Entry: `slice select`.

Code: `src/cvsubstrate/analysis/slices.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S3.J — Synthetic provenance schema

Entry: `synthetic validate-sample`.

Code: `src/cvsubstrate/contracts/synthetic.py`, `src/cvsubstrate/contracts/research.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S3.K — Simulator metadata importer SDK

Entry: `synthetic ingest`.

Code: `src/cvsubstrate/data/simulator_sdk.py`, `src/cvsubstrate/data/synthetic.py`

Explicit pointer maps for generic/Unreal/Blender/Isaac-shaped exports, not live simulator plugins.

## S3.L — Distribution comparison

Entry: `distribution describe/compare`.

Code: `src/cvsubstrate/analysis/distributions.py`, `src/cvsubstrate/analysis/domain.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S3.M — Embedding-domain analysis

Entry: `distribution embeddings; backbone extract`.

Code: `src/cvsubstrate/analysis/distributions.py`, `src/cvsubstrate/backbones/service.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S3.N — Arbitrary staged campaign DSL

Entry: `campaign compile/run-stages`.

Code: `src/cvsubstrate/campaigns/dsl.py`, `src/cvsubstrate/contracts/groundwork.py`

Fixed-update stages execute through compatible workers. Native-epoch adapters must use native jobs/DAG; source exposure equivalence is not fabricated.

## S3.O — Budget/fairness constraints

Entry: `campaign budgets`.

Code: `src/cvsubstrate/campaigns/dsl.py`

Planned exposures checked; actual GPU hours remain unobserved without instrumentation.

## S3.P — Seed and failure preservation

Entry: `campaign run-stages/report`.

Code: `src/cvsubstrate/campaigns/dsl.py`, `src/cvsubstrate/campaigns/report.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S3.Q — Deterministic ablation sweeps

Entry: `campaign sweep`.

Code: `src/cvsubstrate/campaigns/dsl.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S3.R — Benchmark specification

Entry: `benchmark register`.

Code: `src/cvsubstrate/contracts/groundwork.py`, `src/cvsubstrate/benchmarks/registry.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S3.S — Immutable benchmark identities

Entry: `benchmark register/list`.

Code: `src/cvsubstrate/benchmarks/registry.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S3.T — Locked-test access governance

Entry: `benchmark authorize-final/final-eval/access-log`.

Code: `src/cvsubstrate/benchmarks/registry.py`, `src/cvsubstrate/governance/policy.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S3.U — Preregistration artifacts

Entry: `benchmark preregister`.

Code: `src/cvsubstrate/benchmarks/registry.py`, `src/cvsubstrate/governance/ledger.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S3.V — Multi-backend orchestration

Entry: `benchmark orchestrate; graph run`.

Code: `src/cvsubstrate/campaigns/dsl.py`, `src/cvsubstrate/experiments/actions.py`

Multiple declared backends; unsupported training semantics fail explicitly instead of pretending equal budgets.

## S3.W — Foundation backbone and detector integration

Entry: `backbone extract; native model backbone config`.

Code: `src/cvsubstrate/backbones/detector.py`, `src/cvsubstrate/worker_shims/backbone_impl.py`, `src/cvsubstrate/worker_shims/backbone_worker.py`

Local real feature-provider calls and torchvision detector wrapper; optional weights/libs not executed here.

## S3.X — Export/runtime implementations

Entry: `deploy export/infer`.

Code: `src/cvsubstrate/deployment/service.py`, `src/cvsubstrate/worker_shims/deployment_worker.py`

Real tensor-boundary native APIs; arbitrary-model decoding/calibration and dynamic output allocators are not automatic.

## S3.Y — Deployment fidelity and decoding

Entry: `deploy compare-arrays/compare-detections/compare-metrics/decode`.

Code: `src/cvsubstrate/deployment/compare.py`, `src/cvsubstrate/deployment/decode.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## S3.Z — Formal benchmark reports

Entry: `report create`.

Code: `src/cvsubstrate/reporting/formal.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## X.A — Public Python API

Entry: `docs generate`.

Code: `src/cvsubstrate/adapters/sdk.py`, `src/cvsubstrate/contracts/groundwork.py`, `src/cvsubstrate/documentation.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## X.B — CLI taxonomy

Entry: `cvrs --help`.

Code: `src/cvsubstrate/cli.py`, `src/cvsubstrate/cli_groundwork.py`, `src/cvsubstrate/cli_research.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## X.C — Structured errors

Entry: `structured JSON failures`.

Code: `src/cvsubstrate/errors.py`, `src/cvsubstrate/execution/services.py`, `src/cvsubstrate/worker_shims/runtime_common.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## X.D — Schema/API docs generation

Entry: `docs generate; schema export`.

Code: `src/cvsubstrate/documentation.py`, `src/cvsubstrate/schemas/registry.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## X.E — Adapter conformance

Entry: `plugin conformance`.

Code: `src/cvsubstrate/adapters/conformance.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## X.F — Static fixture library

Entry: `groundwork-fixtures`.

Code: `src/cvsubstrate/data/groundwork_fixtures.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## X.G — Local release automation

Entry: `release build --wheel`.

Code: `src/cvsubstrate/release.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## X.H — SBOM/dependency inventory

Entry: `release sbom`.

Code: `src/cvsubstrate/release.py`

Implemented software path; optional native dependencies and data remain separate execution gates.

## X.I — Optional dependency groups

Entry: `pip extras`.

Code: `pyproject.toml`

Declaration ranges, not a tested compatibility matrix; GPU-specific stacks supplied separately.

## X.J — Architecture and extension documentation

Entry: `README links`.

Code: `docs/ARCHITECTURE_04.md`, `docs/ADAPTERS_04.md`, `docs/QUICKSTART_04.md`

Finite engineering scope and unexecuted integrations made explicit.

