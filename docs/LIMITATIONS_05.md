# Explicit limits — 0.5.0a1

## Implemented but not executed against the corresponding real ecosystem

MMDetection/OneDL native telemetry and published checkpoint reproduction; Ultralytics/RF-DETR native hooks; pretrained GroundingDINO, YOLO-World, SAM/SAM2 and timm/HF/DINO backbones; official COCO/DOTA scores; ORT/OpenVINO/NNCF/TensorRT quantization/deployment; actual CUDA/mixed precision/distributed behavior. Native API calls exist. Missing dependencies or assets cause explicit errors. Local conformance does not establish upstream numerical correctness.

## Finite implementation boundaries, not merely missing tests

1. Source telemetry measures consumed identities and optimizer calls, not per-source gradient influence. Untraced mixing remains partial. Single-process native recipes do not provide a complete distributed training agent.
2. Windowed raster execution controls its own buffers and spills predictions to disk. It does not cap arbitrary native model/driver memory or make ordinary compressed JPEG/PNG drivers efficient random-access rasters. Streamed output is HBB; native OBB jobs exist separately.
3. Deployment profiles cover specified output contracts, not every detector configuration. TensorRT's per-image profile implementation is not optimized persistent serving. Calibration is static ORT QDQ/OpenVINO NNCF, not a general QAT toolkit or legacy TensorRT calibration-cache manager.
4. SAM adapters currently accept points/boxes. Mask-logit refinement and every SAM3-style concept/video task are not implemented. Shared mask IDs must be provided for tile-instance union; automatic cross-tile association is not invented.
5. Vision jobs over plain image lists are dev/selection only, not an integrated authorized locked-test vision benchmark executor. HBB benchmark authorization remains separate.
6. Research registry independence is explicitly attested, not authenticated. Local hash chains need an external anchor to detect wholesale history replacement. Registry assumes one logical writer, not clustered concurrent publication.
7. Capsules do not automatically vendor arbitrary data, models or Python environments. Re-evaluation initially covers stored canonical HBB predictions; other task evaluators remain explicit.
8. Arbitrary native-epoch trainers do not inherit exact six-arm fixed-update sampling semantics. Instrumentation makes the mismatch measurable; integrating each backend's sampler/budget policies is still model-specific work.
9. Foundation feature layouts are checked, not automatically made compatible. A model requiring a missing pyramid/neck still needs a deliberate model-specific adapter.

## Deliberately outside this release

Cloud S3/GCS/Azure stores, distributed Slurm/Ray/Kubernetes scheduling, live Unreal/Colosseum/Isaac/Blender controllers, hundreds of model-zoo entries, public hosting, video/tracking/pose/depth/3D/VLM tasks. These were not silently used as a requirement to finish local Slices 1–5. Source-metadata importers, local artifact stores and a static registry are included.

## Evidence

All included newly trained weights are owned randomly initialized CPU conformance models trained on procedural fixtures. No aerial accuracy improvement, real Sim2Real effect, independent researcher reproduction, broad OS matrix, production security or GPU performance is claimed. Old 0.1–0.4 evidence is historical. See `BUILD_REPORT.md` and `evidence/0.5/VERIFICATION_SUMMARY.json` for current executed checks.
