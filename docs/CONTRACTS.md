# Version-1 contract semantics

## Geometry

Horizontal boxes use continuous `[x1,y1,x2,y2]` pixel coordinates with origin at
image top-left, x rightwards, y downwards. Bounds are `[0,width]` and `[0,height]`;
x2>x1 and y2>y1. Area is `(x2-x1)*(y2-y1)`, never an implicit `+1` convention.
Predictions have exactly one row per selected image, including empty images.
Scores are finite in [0,1] and are declared backend confidence, not calibrated probabilities.

COCO source category IDs may be noncontiguous. The dataset retains them. A worker
may map categories to training indices internally, but must reverse that mapping
in canonical output. Native Torch reserves class zero for background.

COCO ingestion preserves supplied annotation `area` for reference evaluator area
slices. Diagnostic pixel-size recall instead explicitly uses bounding-box area.
Noncrowd `ignore` is rejected because this foundation has not defined a portable
meaning for it. `iscrowd` is preserved for evaluation. Crowd-aware native training
is not implemented and fails rather than treating crowd boxes as ordinary targets.

## Identity

Canonical JSON v1 uses UTF-8, sorted string object keys, compact separators,
materialized schema defaults, preserved list order, and finite JSON values. It is
Python-canonical JSON, not an assertion of RFC 8785 interoperability. The Python
implementation is recorded. Numeric lexical equality beyond validated contract
normalization is not promised across arbitrary languages.

An experiment digest excludes the dataset locator, freeform notes, and checkpoint
locator; it includes their content digests and all declared measurement/training
settings. The human experiment name remains part of this specification identity.
Unknown backend config paths are not magically made portable. A unique run ID is
separate from the experiment digest: repeating the same spec creates a new run.

Every dataset includes dimensions, image hashes, categories, splits, source tags,
lineage, and per-domain metadata. Relative file paths are portable and traversal is
rejected. A hash establishes byte identity, not label quality or near-duplicate freedom.
Full manifests are hashed; irrelevant split edits conservatively change dataset
identity. Sample order is meaningful for deterministic sampling.

## Extension points

The worker protocol supports capabilities, validate, predict, and optional train.
Unsupported operations fail. New workers must emit the same canonical task result
and pass conformance tests without changing core internals. Core APIs are alpha;
version-1 schema changes require a migration note and new schema version when breaking.

Generation metadata separates planned settings from observed values. Null values
are unknown, not zero. Units, coordinate conventions, and visibility definitions
must accompany measurements. Core ingestion neither measures realism nor certifies
a simulator integration.

Geospatial metadata is preserved but not interpreted. HBB tiling transforms and
merge utilities are tested separately; the integrated model runner currently rejects
nontrivial tile policies. OBB support must first define angle units/range, handedness,
width/height equivalence, affine-transform behavior, and an independent evaluator.

## Validation limits

Pydantic assignment validation is not a substitute for validating a complete
message at a trust boundary. The runner revalidates serialized records. Mutable
nested dictionaries/lists should be treated as draft data until materialized and
hashed; do not mutate a record after it is committed as run evidence.
