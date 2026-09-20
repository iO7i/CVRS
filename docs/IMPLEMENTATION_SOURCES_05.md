# Primary API sources consulted for 0.5

Consulted during implementation, 19 September 2026. These references guided optional native calls. They do not establish that the respective libraries/checkpoints were executed in the build environment or that every upstream version is supported.

| Integration | Primary reference | Design implication |
|---|---|---|
| GroundingDINO HF | https://huggingface.co/docs/transformers/model_doc/grounding-dino | Exact processor/model/local assets; current postprocess threshold API |
| Ultralytics callbacks | https://docs.ultralytics.com/usage/callbacks/ | Observe actual model/optimizer operations, not a nominal reserved callback |
| RF-DETR training | https://github.com/roboflow/rf-detr/blob/main/rfdetr/engine.py | Observe targets after microbatch splitting and native optimizer steps |
| RF-DETR export | https://github.com/roboflow/rf-detr/blob/develop/src/rfdetr/export/_onnx/inference.py | Query/class-pair ranking and explicit output decoding |
| SAM2 | https://github.com/facebookresearch/sam2 | Trusted local configuration/checkpoint and native predictor |
| ONNX Runtime quantization | https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html | Calibration reader and static QDQ native pipeline |
| NNCF | https://openvinotoolkit.github.io/nncf/autoapi/nncf/ | Native calibration dataset and quantization APIs |
| MMDeploy detection | https://mmdeploy.readthedocs.io/en/v1.2.0/04-supported-codebases/mmdet.html | Preserve native export tooling instead of guessing detector graph semantics |
| TensorRT dynamic output | https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/dynamic-shapes-basics.html | Explicit data-dependent output allocator and bounds |

Recipe revisions and exact local package versions must be recorded for real runs. The URLs may describe later code after this release; pin your installed source before certification.
