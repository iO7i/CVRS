# Implementation versus evidence

The accepted request was to build engineering groundwork, not manufacture certification. Every feature in the implementation ledger has a code path and documented scope. This is **not** a declaration that every line or optional native integration has been validated.

## Still not earned

- Real MMDetection/OneDL inference, upstream checkpoint/config parity and published full-benchmark reproduction.
- Real Ultralytics/RF-DETR/OBB model execution and native training/export verification.
- Official COCO/DOTA evaluator parity on real datasets.
- Real aerial/synthetic corpus import, meaningful training, multi-family comparison and fresh-seed scientific confirmation.
- Foundation-backbone local weights, feature geometry and downstream results.
- ONNX/ORT/OpenVINO/TensorRT real model fidelity, CUDA/mixed precision/multi-GPU/hardware certification.
- Independent external researcher, Windows/macOS and second-machine reproduction.

## Engineering boundaries still explicit

- Epoch-native adapters do not yet provide fixed-update/source-exposure instrumentation. They are executable native job paths, not equal-budget campaign certification.
- Tensor export expects an explicit model boundary; arbitrary detector graph export/decode is not automatic. INT8 calibration/data-dependent TRT output allocators are not generic features.
- The Pillow multi-scale inference path is not a bounded-memory gigapixel streamer; rasterio window extraction is a separate optional path.
- The general schema engine applies registered migrations only; future unknown versions need real migration code.
- Dataset readers require explicit image indexes, dimensions, split/lineage conventions and available local files. They do not download datasets or infer licensing.
- Simulator-shaped JSON mappings are importers, not independently tested integrations with live simulators.
- Catalogue/status evidence is local and unsigned. Fixture H3 conversion tests are not genuine MMDetection H3 scientific certification.
- Native model APIs were checked against official documentation, but unexecuted integrations may require fixes when exercised.

All these limits belong next to the implementation, not in a hidden disclaimer. The old 80%/95% estimates are not an audited measure. Use the checklist plus actual evidence files instead of averaging software and scientific gates into a percentage.
