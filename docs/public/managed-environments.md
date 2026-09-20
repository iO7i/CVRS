# Managed environments without destructive repair

`env plan SPEC --store STORE --out PLAN` is a read-only planning operation. The
specification records the interpreter, exact package pins, optional local wheel
hashes and expected modules. `env apply PLAN --approve DIGEST --store STORE`
executes only the approved plan. There is no automatic remote installation.

The supported management backends are venv, uv, conda, Docker and Apptainer.
venv/uv can use an existing interpreter entirely offline. The latter three need
their native executables; missing tools are explicit errors. Containers require
a digest-pinned base. Recipe generation and metadata health are not CUDA ABI or
model-operation certification.

A new prefix is created at its final location. Moving a venv afterwards would
break embedded paths, so CVRS never does that. Repair/upgrade create another
revision, capture the actual environment and activate only a healthy candidate.
The old prefix remains intact. `env activate` can restore a prior healthy
revision after explicit approval. Failed revisions are preserved for diagnosis.

```bash
cvrs env plan environment.json --store ../my-envs --out planned.json
cvrs env apply planned.json --store ../my-envs --approve EXACT_PLAN_DIGEST
cvrs env doctor experiment --store ../my-envs
cvrs env repair experiment --store ../my-envs --out repair.json
cvrs env upgrade experiment --store ../my-envs --spec reviewed-new-pins.json --out upgrade.json
cvrs env diff experiment other-experiment --store ../my-envs
```

`--allow-network` is not an implicit global permission; network and source-build
policy are fields in the reviewed environment spec. Exact top-level pins still
are not a full transitive binary lock. Hash-locked installs require every local
wheel. No attempt is made to merge incompatible old/new model stacks into one
Python environment.

[Guided paper adoption](guided-paper.md) · [Stack packs](packs.md)
