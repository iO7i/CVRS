# Engineering closure — finite 0.5 implementation

## Native training telemetry

`worker_shims/telemetry_runtime.py` records hash-chained SQLite events for samples reaching the model, source identity, batch, epoch, optimizer-step calls and repeats. Actual optimizer calls are separate from batches: gradient accumulation and an AMP-skipped optimizer call must not be counted as equal. Unknown source identity stays unknown. Gradient contribution per source is not measured.

The Ultralytics recipe observes metadata after preprocessing and counts only when the model consumes it. Exact source attribution requires explicitly disabled or fully traced mixing; primary image IDs do not describe all mosaic/mixup contributors. The RF-DETR recipe instruments native `train_one_epoch`, model microbatch inputs and optimizer calls. Unsupported signatures fail. MM2/MM3 inspect native data containers at `train_step` and the native optimizer. Real MM/UL/RF packages were unavailable here; these integration hooks still require actual native execution.

Native-epoch training remains a different budget contract from the controlled fixed-update campaign runner. Telemetry provides measured information; it does not make those trainers mathematically equivalent or force all six research arms into every native framework. Rank aggregation requires declared complete ranks; equal optimizer-call counts do not prove distributed synchronization. The included automatic native recipes are single-process; distributed launch needs explicit per-rank integration.

Commands: `telemetry inspect`, `telemetry aggregate`; native job config can specify telemetry mixing policy. Ledger inspection is read-only and does not add events.

## Windowed raster execution

`streaming/raster.py` reads source windows directly through rasterio, with fractional windows for multiple scales. A bounded synchronous batch provides backpressure. No resized full-scene image or full Python prediction list is built. Each tile's raw predictions and inverse transform commit transactionally to SQLite; interrupted attempts preserve their state. Resume checks source hash, model identity and plan identity before reusing committed tiles.

Global score-ordered HBB NMS is performed after prediction ingestion using disk-backed SQLite/RTree. It does not finalize low-scoring tile boxes before a later tile might produce a better box. Equal scores use stable tile/ordinal ordering, independent of arrival order. Output can be a detection-per-line stream or a streaming-written canonical image record. Reference evaluators may still need memory to load the latter.

Memory bounds cover controlled tile arrays, declared per-tile prediction limits, configured GDAL cache and SQLite cache. They are not a promise about total process RSS, model CUDA memory, raster-driver internals, or compressed source layout. For a hard process cap, use an OS/container limit. Source hashing reads the file sequentially; it does not load it all in RAM. All-metadata merge is global and disk-backed, not an approximate incremental NMS. Streaming currently emits HBB; existing OBB utilities are not advertised as a full streaming oriented-detector pipeline.

`stream run` supports native torchvision, Ultralytics or RF-DETR in one persistent worker per invocation. The model loads once, not once per tile. `--stop-after-tiles` intentionally creates a resumable partial result. Raw stream databases are mutable while work continues; export a capsule/snapshot after completion for immutable exchange.

## Detector deployment and calibration

Four explicit profiles are provided: Ultralytics raw output, Ultralytics end-to-end output, RF-DETR logits/boxes, and MMDeploy end-to-end boxes/labels. They specify image dtype, RGB/BGR, resize/letterbox behavior, padding order, normalization, tensor names, class mapping and inverse transforms. Raw YOLO applies one NMS; an end-to-end output does not get an accidental second NMS. RF-DETR uses query/class-pair top-k rather than per-query argmax. No profile is guessed from tensor dimensions.

Native export routes call the upstream APIs; MM export delegates to a trusted, hash-identified MMDeploy checkout/config. Runtime inference supports ORT, OpenVINO and TensorRT with local assets. TensorRT data-dependent output allocation has an explicit byte cap. The TensorRT per-image profile path reloads the generic engine; its timing is not equivalent to the persistent ORT/OpenVINO path and it is not an optimized serving loop.

`quantize prepare` creates calibration NPZ files using the same preprocessing profile, records identity and transforms, and rejects protected evaluation roles. `quantize run` supports static ORT QDQ and OpenVINO/NNCF; it validates actual graph output rather than relabeling FP32 as INT8. External tensor data must be explicitly safe and hashed. QDQ artifacts can feed a compatible TensorRT build through the generic export/runtime layer; legacy TensorRT calibrator caches and general QAT are not implemented.

`quantize regression` compares the same metric identity against predeclared higher-is-better tolerances. Calibration on dev data is disclosed as training-time data reuse. No ONNX/ORT/OpenVINO/TensorRT quantized model was executed in this build environment.

## Adapter quality

Finite recipes cover MM2/MM3, UL/RF, GroundingDINO-HF, SAM-HF, SAM2, YOLO-World, UL segmentation, DINO/timm/HF feature backbones. Recipes explicitly state assets, task, transformations and limitations; they do not certify all library versions. Foundation feature extractors record finite shape/channel/stride receipts and reject missing/inconsistent geometry rather than inventing a feature pyramid.

The external vision scaffold has a no-argument factory compatible with the public plugin runner, typed job validation, explicit capabilities and native prediction delegation. The local build exercised the generated external project through an actual worker process. It was not authored by an independent researcher.
