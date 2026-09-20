# Type-checking scope

The alpha release requires mypy to pass for the maintained controller and
product surface:

- the `cvrs` command router and every maintained CLI command family;
- the finite `cvsubstrate.v1` facade and package import;
- documentation/reference generation;
- managed product workflows and the static research browser;
- publication, public-tree audit, packaging, and release-support code.

The following native worker implementations are deliberately outside this
single-interpreter type gate. Each executes in an independently pinned runtime,
often on a different Python, CUDA, PyTorch, MMCV, or TensorRT version:

| Excluded implementation | Runtime reason |
|---|---|
| MMDetection 2/3 and MMRotate workers | mutually incompatible MMCV, MMEngine, PyTorch and Python combinations |
| MMSegmentation and MMDeploy workers | native OpenMMLab and ONNX/TensorRT stacks are isolated from the controller |
| TensorRT allocator/deployment shims | type availability depends on NVIDIA's runtime-only Python bindings |
| Ultralytics, Grounding DINO, SAM-family and DINO-family workers | optional model frameworks and checkpoints are not controller dependencies |
| DOTA/native evaluator shims | independently pinned evaluator environments and optional compiled packages |
| GPU telemetry/native-training shims | monkey-patch framework internals that are version-specific by design |

These exclusions do not suppress errors globally and do not imply native
compatibility. Each worker remains governed by its own environment lock,
execution evidence, and truthful qualification disposition.
