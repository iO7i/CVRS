# Slices 1–5 engineering closure — 0.5.1a1

This release extends 0.5.0a1 without rewriting its formats or removing its commands. The new public facade is `cvsubstrate.v1`; native driver internals remain provisional. The frozen scope and implementation paths are in `V1_CLOSURE.md` and `../IMPLEMENTATION_LEDGER.json`.

## Install and inspect

Use a new environment; do not merge an old MMCV stack into the modern controller.

```bash
python -m venv .venv
# POSIX: source .venv/bin/activate
# PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m cvsubstrate --version
python -m cvsubstrate closure policy
python -m cvsubstrate closure --help
python -m cvsubstrate schema list
```

Core needs only Pydantic. Optional native dependencies need installation separately. Native assets are local and explicit; the tool must not download replacement weights.

## Execute the closure workflow

```bash
python -m pip install -e '.[native,geo,signing]'
python tools/smoke_closure.py ./my-closure-demo
```

Use a new output path. This creates generated images and a real CPU mask model, records actual training telemetry, runs a windowed mask stream with pause/resume, produces canonical masks and a world-coordinate index, re-evaluates saved predictions, performs exact reversible tensor transforms, executes two baseline/treatment run pairs, records original/reproduction attempts, and exchanges signed registry copies. It also restores a capsule with an intentionally missing restricted external dependency. Private signing keys are temporary and are not included in the result.

Read `my-closure-demo/summary.json`. The inputs are procedural, the model starts with random weights, the operator/machine are the same, and the report explicitly does not claim independent or real-world scientific reproduction. The mask threshold in this fixture is declared as 0.25 to exercise nonempty random-model outputs; it is not a recommended research threshold.

## Inspect existing historical bytes

```bash
cvrs closure compatibility tests/compat/v0.5.0a1/manifest.json --root tests/compat/v0.5.0a1
```

This checks the preserved exact bytes against their recorded hashes and named schema readers. It does not invent future migrations. Old registry records can be preserved in the new format without assigning new scientific meaning:

```bash
cvrs closure registry migrate ./old-registry --out ./new-registry
```

The original registry remains intact.

## Native MM campaigns

`cvrs closure native-campaign plan campaign.json` validates the budget units, parent dependencies, seeds and equality requirements. `run` takes `--out`, an optional `--workers workers.json` mapping from backend to interpreter, and `--resume`.

A supported MM training stage carries the native repository/config identities, the canonical dataset manifest and digest, a local data root, category mapping and train/validation split names. The worker writes separate native COCO annotation files and binds the derived config to those exact samples. It never edits the original config or dataset.

The automatic dataset-binding recipe is **a direct CocoDataset pipeline**. Composite dataset wrappers need explicit recipes and are rejected rather than silently flattened. MM iteration budgets use supported iteration loops. UL/RF native stages are epoch-based; claims of fixed-update or real-stream equivalence are refused when not established. Completed stages seal their actual checkpoints; resume verifies both evidence and checkpoint identity.

## Reference and task re-evaluation

```bash
cvrs closure reevaluate evaluation.json --out ./new-analysis
```

A task evaluation spec declares `task`, dataset/prediction/protocol paths, split where relevant, and optional `population_slice`. Tasks are `hbb`, `obb`, `masks`, `grounding`, and explicitly nonofficial `mask_diagnostics`. Official evaluation goes through its configured reference interpreter. Grounded canonical predictions are converted with a receipt preserving prompt/oracle provenance. Existing prediction bytes are never mutated.

For a protected final population, obtain a counted authorization before invoking the same task path:

```bash
cvrs closure authorize-evaluation evaluation.json --ledger ./test-access.jsonl --approved-by researcher --reason "Frozen final analysis"
```

Copy the returned `ledger` and `approval_digest` into the spec's `authorization` object. Authorization binds the exact prediction/data/protocol bytes and all other semantic spec fields. It is consumed before attempted evaluation, even if the evaluator later fails. This is local accountability, not file secrecy or independent identity verification.

## Prompt trajectories

Use `closure prompts negotiate prompt-sets.json --backend sam_hf` before native execution. Point/box/mask atoms can share a `target_id` so corrective positive/negative points refer to the same object. A continued interaction binds both prior prompt-set and prior prediction hashes. `reference_image`, `reference_region`, and concept atoms are represented, but stock models that do not support them reject them; external plugins can explicitly register these capabilities. No exemplar is silently turned into text.

## Registry exchange

```bash
cvrs closure registry add ./registry --kind claim --input claim.json
cvrs closure registry verify ./registry
cvrs closure registry query ./registry --minimum-level R3
cvrs closure registry export ./registry --out ./exchange
cvrs closure registry merge ./second-registry --input ./exchange
cvrs closure registry site ./second-registry --out ./site
```

For signing, `closure keygen key.pem` asks for a password. `--unencrypted` explicitly opts out; never commit that file. Registry sign/export accept `--key`; encrypted keys use a password prompt or the explicitly named `--key-password-env`. Import can require a signature and allowlisted key IDs. Key possession proves a signature over bytes, not the truth of an experiment or a scientist's institutional identity.

The v2 registry uses SQLite transactions for local concurrent writers and immutable event-DAG exchange between copies. Identical imports are idempotent. Conflicting content, missing artifacts, invalid signatures, dangling edges and cycles abort a merge. Failed and blocked reproduction attempts remain part of history.

## Garbage collection

`closure gc STORE` defaults to dry-run with an age limit. Pin referenced object digests before collection. Applying removal requires the exact current dry-run plan digest via `--apply-plan`. This protects against applying a stale deletion plan; it is not remote storage management.

## Limits and verification

`SUPPORTED_V1_MATRIX.json` is operation-specific. Installing a dependency is not evidence that a model ran. The five original slices' scientific gates remain separate from the finite closure checklist. See `LIMITATIONS_051.md` and the current build report.
