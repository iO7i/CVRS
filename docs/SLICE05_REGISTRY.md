# Slice 5 — reproducible research registry

The registry is a local SQLite-backed graph plus content-addressed evidence objects. Static HTML/JSON export is included. It is not a cloud service, a model hub, a leaderboard of incompatible metrics or an identity authority.

## Records and invariants

A `ClaimSpec` fixes a question, estimand, dataset/protocol/experiment identities, reported metrics and tolerances. Repeated insertion is content-idempotent. An attempt never edits the claim. `ReproductionAttempt` retains actor, machine, implementation, evidence, outcome and failure reason. Failed/blocked attempts remain visible. Corrections are new claims with explicit acyclic supersession edges.

Evidence files are copied into a SHA-addressed object store. Registration/import events form a timestamped hash chain. Verification checks files, sizes, record hashes, references, and event-to-record/object/supersession inventory. Deleting a record or edge is detected, not merely modifying an evidence file. The local registry assumes one logical writer; it is not a multi-node coordination system. An attacker controlling the entire unsigned store can rewrite its history: retain an external capsule/hash to anchor provenance.

## Evidence ladder

- R0: claim/metadata.
- R1: bound experiment, dataset, protocol, environment and predictions preserved.
- R2: a native execution receipt binds the actual prediction bytes and run identity.
- R3: a separate reproduction attempt matches required metrics within predeclared tolerances under compatible data/protocol/estimand.
- R4: R3 plus a separately recorded independent-operator/machine review.
- R5: R4 plus a separately reviewed distinct implementation of the declared estimand.

A changed username or machine string never creates R4. Reviewers cannot self-review as claim author or attempt actor. Review attestations are retained evidence, not verified legal identities. An original execution is labeled original, not promoted to reproduction because its metrics equal themselves. Reusing the original receipt is detected. A re-evaluation is not a rerun. Software fixtures retain `FIXTURE_` statuses and never become scientific certification.

`capture-run` starts from an existing verified SUCCEEDED CVRS run, preserves its native worker result and prediction bytes, and creates an original record or an attempt against an existing claim. It checks the supplied dataset against the source experiment. Hash validation does not independently prove that an untrusted publisher honestly ran the claimed model.

## Exchange and re-evaluation

Snapshots retain records, evidence, reviews, supersessions and the original event chain. Portable capsules package the snapshot with safe archive extraction and integrity manifests. Imports build transactionally into a new directory; failures do not leave a purportedly valid half-imported registry. Static pages escape untrusted titles and link to per-claim JSON.

`research-registry reevaluate` invokes the declared evaluator on saved predictions and checks that source files did not change. The new analysis has its own protocol identity and lineage. It never invokes training/inference. The initial re-evaluation path uses canonical HBB datasets/predictions; masks have their separate evaluator. It does not claim a universal reevaluator for video, VLMs or every possible task.

Capsules contain selected preserved evidence, not automatically all licensed training images, pretrained weights or installed dependencies. Inference/training reproduction may need separately supplied licensed assets. No external files or executable code are fetched during registry import.

## Gates

| Original gate | Locally implemented/exercised | Outstanding |
|---|---|---|
| G5.1 Capsule portability | Snapshot/capsule restore to a fresh local path, original event head preserved | Independent machine/environment |
| G5.2 Re-evaluation | Real saved detector predictions re-evaluated without model execution | More task-specific reference evaluators |
| G5.3 Benchmark identity | Existing versioned benchmark identities; explicit claim/protocol mismatch handling | Public benchmark maintenance |
| G5.4 Reproduction ladder | Evidence-bound levels; original/duplicate/fixture safeguards | Real evidence earns high levels |
| G5.5 Independent reproduction | Reviewer records, conflicts and independence checks | Actual separate researcher/machine |
| G5.6 Failure preservation | Failed/blocked/mismatched attempts retained and exported | Real failed research attempts |
| G5.7 Cross-implementation | Distinct implementation + reviewed evidence path | Genuine same-claim scientific reproduction across implementations |
| G5.8 Public-ready registry | Local escaped static site and JSON export | Licensing review, actual research content, optional hosting |

The bundled CPU rerun reaches fixture-level R3 on one machine. No R4/R5 scientific success is claimed. Synthetic review fixtures exercise code paths only.
