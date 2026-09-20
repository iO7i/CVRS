# v0.7 — use the system without replacing your research stack

This extends the v0.6 codebase. It adds managed environments, guided approval,
rich geometry bridges, evidence-scoped compatibility receipts, a static research
browser, and owner-gated release workflows. It does not grant a source license,
register a package name, publish a repository, or certify unexecuted models.

## Install and inspect

```bash
python -m pip install -e '.[adoption]'
cvrs doctor
cvrs stack inspect mmrotate
cvrs recipe search --pack mmrotate
```

Core remains separate from model SDKs. The native CPU demonstrations additionally
need `.[native]`; mask array interchange needs NumPy. Do not install every model
extra into one environment. Python, CUDA and compiled extension compatibility
must match the particular native repository and hardware.

## Create a managed environment

Copy `examples/product/managed-environment.json`, choose your own name and an
installed interpreter. Package requirements must be exact pins. Local wheel
artifacts can carry SHA-256 digests; a fully hash-locked installation requires the
complete local dependency closure, not only the top-level package.

```bash
cvrs env plan examples/product/managed-environment.json --store ../cvrs-envs --out env-plan.json
```

Read `env-plan.json`. Then apply its exact `plan_digest`:

```bash
cvrs env apply env-plan.json --store ../cvrs-envs --approve THE_REVIEWED_DIGEST
cvrs env doctor research --store ../cvrs-envs
cvrs env repair research --store ../cvrs-envs --out repair-plan.json
```

Planning does not install anything. Applying creates a new final-prefix revision,
installs only the reviewed packages and checks the resulting interpreter. Repair
never mutates an old working prefix. A failed replacement remains failed and does
not become active. Rollback uses `env activate NAME REVISION --approve REVISION`.
`env upgrade NAME --spec replacement.json` prepares a new revision with new pins.
The store is local and explicitly owned; the current Python environment is not
adopted or modified. Network/Python downloads/source builds are separate opt-ins.

venv and uv have real offline lifecycle evidence in this release. Conda, Docker
and Apptainer have native command/build implementations but were not available for
execution here. These are not universally solved GPU environment recipes.

## Wrap a paper with an approval record

```bash
cvrs paper prepare /path/to/research-repo --python /path/to/native-python --spec decisions.json --out paper-project
cvrs paper readiness paper-project/paper.json
cvrs paper approve paper-project/paper.json --actor YOUR_LOCAL_ACTOR --out paper-approval.json
cvrs paper execute paper-project/paper.json --approval paper-approval.json --operation predict --out native-result --trust
```

`decisions.json` declares reviewed argv, bound file inputs and output names. Use
`examples/product/paper-decisions.json` as a structural example, not a claim that
an arbitrary repository has those exact arguments. Inspection never guesses and
executes a training command. The original specification remains untrusted; a
separate approved copy and approval digest authorize execution. Changes to either
copy, source state or bound file content invalidate the handoff.

Directory or opaque inputs remain partially closed unless you bind a versioned
manifest. A worker is dependency isolation, not a hostile-code sandbox. Coupled
models remain together; separate workers exchange detached artifacts, not live
gradients or automatically compatible feature tensors.

## Geometry and methodology

```bash
cvrs exchange export canonical-rich.json --format supervision --out exchange.json
cvrs exchange import exchange.json --format supervision --out restored.json
cvrs exchange audit canonical-rich.json restored.json
cvrs research lint examples/product/methodology.json --out methodology-review
```

The rich exchange format supports HBB, quadrilateral OBB, masks and grounded
metadata. `exchange native ... --worker-python ... --trust` exercises an installed
Supervision/FiftyOne SDK in another interpreter. Payload conversion does not
prove native SDK compatibility. Mask pixels are not silently resized; unsupported
conversions fail rather than drop data.

The methodology review distinguishes benchmark class-vocabulary prompts from
per-image ground-truth assistance, planned from observed budgets, and reusable
synthetic assets from prohibited shared-source contamination. Rules inspect
supplied evidence; they do not decide whether a scientific conclusion is true.

## Browse and document

```bash
cvrs site build /path/to/research-results --out ../research-site --verify
cvrs docs portal . --out ../docs-current
cvrs docs version-site --files ../docs-previous ../docs-current --out ../versioned-docs
```

Open the generated `index.html`, or use any static host. Search, filters, record
details and comparison are entirely local. Task/dataset/evaluator mismatches
prevent numeric ranking. No checkpoints/media are copied automatically.
Versioned docs preserve the supplied versions; unknown historical portals are not
invented or relabeled.

## Publication remains a separate owner action

```bash
cvrs release preflight .
cvrs release launch-plan . --out launch-plan.json
cvrs release public-tree . --out ../public-preview --preview
```

Until real identity/license/security-contact values are approved, preflight
returns `BLOCKED`. Read [the release process](public/release-process.md) before
activating GitHub workflows, repository security writes, PyPI publishing or DOI
archiving. No credentials, services or repository settings are changed by these
inspection commands.

## Integrated software demonstration

```bash
python -m pip install -e '.[native,adoption]'
python tools/smoke_product.py ../product-smoke
```

It uses procedural images, random-initialized models, owned local environment
fixtures and fresh output directories. It is not a pretrained benchmark or an
independent reproduction. Browser screenshots and native SDK integration status
are separate evidence categories.
