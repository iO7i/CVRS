# 0.4 architecture and public boundary

```text
Typed contracts + schema registry + explicit migrations
                       |
CLI / Python API --- capability requirements
                       |
Local execution DAG / staged campaign / benchmark policy
                       |
std-library protocol workers (trusted code, separate interpreters)
  | MM2/MM3/OneDL | torchvision | UL / RF-DETR | evaluators |
  | backbone providers | checkpoints | deployment runtimes |
                       |
HBB or separate OBB predictions + native artifact preservation
                       |
reference or explicitly diagnostic evaluation
                       |
CAS / hash-chain events / sealed bundles / portable capsules
```

## Design decisions

The controller depends on Pydantic, not a machine-learning stack. Heavy modules live behind commands or separate workers. Source-model implementations stay native. A declared package/profile identifies an integration target, never a verified compatibility matrix.

Public packages: `contracts`, `schemas`, `adapters`, `artifacts`, `experiments`, `execution`, `environments`, `heritage`, `checkpoints`, `datasets`, `data`, `geometry`, `analysis`, `evaluation`, `campaigns`, `benchmarks`, `backbones`, `deployment`, `reporting`, `provenance`. Treat `worker_shims` as executable transport implementations, not stable model APIs. Alpha interfaces may still change with explicit schema/release migrations.

## Schema evolution

Known historical contracts remain readable. Registry migrations are explicitly registered edges; the release includes an actual ArtifactEnvelope 1.0→1.1 migration and preservation/reporting of run migrations. It does not claim automatic translation of arbitrary unknown historical JSON. Unsupported versions/downgrades fail. Migration writes a derived artifact; it does not mutate sealed source evidence.

## Plugins

Registration records metadata without importing plugin code. Explicit trust is required before execution. Plugin descriptors and protocols cover model/data/evaluator/exporter/simulator metadata/backbone/artifact store/merge roles. The scaffold deliberately advertises JSON validation only until the author implements more. Conformance can execute supplied cases in a selected worker. Structural conformance is not numerical correctness.

## DAG and cache

Only registered local action handlers execute; no shell-expression language. Input references bind exact bytes. Nodes can consume a named parent output (for example `checkpoint`) or a concrete artifact path. `experiment.run` publishes checkpoint/prediction/metric aliases. `experiment.bind-checkpoint` makes a new experiment input for a subsequent stage.

Caches incorporate code, dependency metadata, parameters and all declared input digests. Training/model evaluation are not automatically cacheable. Retry requires both node intent and action permission. Resume checks prior sealed output hashes; explicit invalidation propagates through descendants. Local cache/ledger locks reject concurrent writers; stale locks require explicit recovery. This is not a distributed scheduler.

## Evidence

`RunBundle` remains the full experiment evidence unit. Generic graph/service outputs use sealed directory manifests. Structured controller lifecycle events record observations at the controller boundary, not fabricated kernel/model events. Raw/native outputs remain alongside canonical outputs. Artifacts are immutable-by-policy and tamper-evident against recorded hashes, not cryptographically unmodifiable.

## Task boundaries

HBB uses continuous pixel `xyxy`. OBB uses validated convex quadrilateral corners. Angle tuples require an explicit convention. Nonuniform transforms retain polygons. Mask/open-vocabulary/video/3D contracts are not silently squeezed into HBB; those remain future slices.

## Scope boundaries

Local FS is the implemented ArtifactStore. S3/GCS are future adapters. The new multi-scale Pillow path is image-memory based; memory-budget batch planning is advisory, not a guaranteed gigapixel streaming algorithm. Optional rasterio window extraction supports large raster workflows separately. Native framework epochs are not interchangeable with fixed-update source-preserving campaigns. GPU-hour matching is reported unobserved until instrumented measurements exist.
