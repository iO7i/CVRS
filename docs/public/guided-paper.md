# Inspect, bind, approve, execute

Keep your working native repository. CVRS can prepare a reviewed wrapper around
its commands without importing it or rewriting its model. An inspector candidate
is not an executable instruction. Supply exact argv and named output contracts
for the real repository.

```bash
cvrs paper prepare ./paper --python /path/to/native/python --spec decisions.json --out paper-project
cvrs paper readiness paper-project/paper.json
cvrs paper approve paper-project/paper.json --actor MY_ACTOR --out approval.json
cvrs paper execute paper-project/paper.json --approval approval.json --operation predict --out results --trust
```

Approval produces a separate approved spec and digest-bound record. The original
spec remains untrusted. Mutation of commands, source, approved specification or
bound inputs invalidates the operation. Neither this record nor the actor string
proves that native code is safe or establishes real-world identity.

File inputs are content-pinned. Directory inputs still need a versioned dataset
manifest for complete identity. A directory name alone is not reproducibility.

A stack workspace adds native module observations, exact interpreter identity,
asset hashes, pack-specific diagnostics and supported operation descriptions:

```bash
cvrs stack inspect mmdetection3
cvrs stack configure mmdetection3 --python /path/to/old-env/python --spec native-job.json --out mm-workspace
cvrs stack doctor mm-workspace
cvrs stack execute mm-workspace predict --out mm-result --trust
```

The pack's job schema is still native/task-specific. No stock profile handles
arbitrary custom loops or automatically splits a jointly trained multi-model
network. Use the reviewed paper wrapper for custom entry points.

Ten source-attributed preparation recipes are searchable using `recipe search`.
A missing immutable revision, dataset or checkpoint stays missing. Recipes are
not paper reproductions. Contributors use `recipe check` and `recipe contribute`;
self-awarded execution badges are rejected.
