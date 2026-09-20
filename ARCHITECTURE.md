# Architecture

The controller owns contracts, native process execution, artifact identity, evaluation protocols and evidence. Models and task-specific training stay in native environments.

```text
Read-only repository scan → reviewed wrapper/stack job
                                  ↓
              isolated worker (whole native graph)
                                  ↓
            original output + canonical task artifact
                                  ↓
           evaluation / analysis / ecosystem bridge
                                  ↓
           run evidence → capsule → research registry
```

Slice 6 adds `adoption/`, `bridges/` and `publication/`, with no ML imports in their public module initialization. Standalone shims support older Python runtimes without importing the modern controller. CLI dispatch is additive; the original experimental interfaces remain available.

A materialized feature artifact must include sample, shape, dtype, stride/layer and producer identity. Cross-worker gradients are deliberately rejected. MMSeg class maps, instance masks and language-grounded predictions have different meanings.

See `docs/public/extend.md`, `docs/public/packs.md`, `docs/public/security.md` and the original numbered ADRs. Package, worker, schema, benchmark and registry versions remain separate.
