# Slice 02 — MMDetection heritage + cross-framework reproduction

## Delivered implementation

1. Standalone stdlib MMDetection worker shim, launched by file path in a foreign interpreter.
2. Trusted config/checkpoint hashing and explicit network-disabled execution policy.
3. Native upstream config resolution with preserved resolved config and a filesystem inheritance graph.
4. MMDetection 3.x `DetDataSample` and legacy 2.x bbox-result extraction paths.
5. Native + canonical prediction preservation and exact representation conversion audit.
6. H0–H5 heritage contracts and H0–H4 evidence-scoped certification code.
7. Reference COCO direct-vs-wrapper parity auditor using pinned `pycocotools==2.0.11` when installed.
8. Cross-framework run comparison that separates measurement comparability from training fairness.
9. Environment-capsule structure, migration guide, TOOD heritage catalogue seed, CLI commands, tests, and evidence ledger.
10. Existing `native_torch`/torchvision worker remains the contemporary second implementation path.

## Honest execution status in this build environment

The build environment has CPU PyTorch/torchvision but no MMDetection/MMCV/MMEngine or pycocotools, and outbound package-index DNS is unavailable. Therefore:

- real MMDetection H2/H3 execution: **BLOCKED_DEPENDENCY / BLOCKED_ASSET**;
- official direct-vs-wrapper COCO parity: **BLOCKED_DEPENDENCY**;
- full published COCO metric reproduction H4: **BLOCKED_DEPENDENCY / BLOCKED_ASSET**;
- GPU is **not** the reason those gates are unexecuted.

Protocol conformance via fake MM-shaped modules is useful software evidence and is explicitly excluded from heritage certification claims.
