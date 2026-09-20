# Optional adapter contracts and limits

| Adapter | Implemented native path | Requirements / unverified scope |
|---|---|---|
| MMDetection 2 | mmcv.Config and native inference; upstream tools/train.py path | Local compatible MM/CUDA stack, exact config/source/checkpoint/data. Not executed here. |
| MMDetection 3 / OneDL | mmengine.Config, DetDataSample outputs; native training launcher | Fork identity is explicit. Config inheritance preserved; no universal model port. Not executed here. |
| Ultralytics HBB | YOLO load/train/predict/export with native outputs | Local trusted checkpoint or architecture; package pin; exact class map. Not executed here. |
| RF-DETR HBB | named native model classes, local checkpoint, train/predict/export | Local trusted assets; API/environment needs a real run. Not executed here. |
| Ultralytics OBB | native train/predict on declared oriented manifests, original-image corners | `model predict-obb` / `train-obb`; native-epoch accounting; dev only. Not executed here. |
| COCO evaluator | separate stdlib worker calls pinned pycocotools | pycocotools2.0.11 unavailable; official parity not executed. |
| DOTA reference | supplied hash-identified official-devkit module in chosen interpreter | Compiled polyiou/source version still required. No invented official AP. |
| timm | features_only with explicit local state dictionary | Optional library/weights; no auto pretrained download. |
| Hugging Face vision | local AutoBackbone directory identity | Local model files, supported backbone outputs; no arbitrary remote model code. |
| DINOv2/v3 | trusted local repository + exact checkpoint feature provider | Explicit feature stride/channels and local repo digest. Not executed here. |
| Foundation-backed detector | native torchvision detector wrapping selected feature provider/FPN | Architectural configuration must be valid; no claim it reproduces a named detector. |
| torch.export | real export + exported/native tensor inference | Small CPU tensor fixture exercised; not arbitrary detection export certification. |
| ONNX / ORT | real Torch ONNX export and named-tensor ORT execution | Optional dependencies; hash all external model tensor files; explicit providers. Not executed here. |
| OpenVINO | convert/save/compile/infer | Hash XML + BIN; explicit device; no AUTO claims. Not executed here. |
| TensorRT | parse/build engine; explicit dynamic profiles; v3 execution buffers | Requires CUDA/TRT; data-dependent output allocation may require model-specific adapter. Not executed here. |

## Training semantics

The native conformance worker executes fixed optimizer-update, source-preserving stages and records sample exposures. Ultralytics/RF-DETR/OBB adapters execute native epochs and disclose exposures/optimizer updates as `NOT_OBSERVED` when hooks do not provide them. General graph orchestration can run these native jobs; it must not certify fixed-exposure fairness from epoch counts. A new adapter must explicitly support the required training contract or execution fails.

## Predict/convert/export boundaries

Converting checkpoint keys is an explicit, audited tensor operation; it is not a universal cross-architecture model conversion. Native label mappings are injective and explicit. A missing mapping fails instead of discarding classes. OBB canonicalization can change corner order without fitting a different rectangle.

Deployment accepts a tensor-boundary model factory or exported artifact. Generic exported tensor arrays can be decoded to postprocessed HBB predictions through an explicit box/score/label/count specification. Raw YOLO/DETR logits, masks, custom NMS, dynamic outputs and unsupported model operators require the model's native decoder/export adapter. INT8 calibration is not implemented or silently substituted.

## Offline and security

No model/data downloads are automatic. Ordinary library download attempts are blocked in optional workers. Explicit trust is required for Python config/repository/plugin/factory execution and unsafe checkpoint formats. NumPy defaults to allow_pickle=false; unsafe import has a separate explicit trust path. Process separation and network guards do not sandbox hostile code. Do not run untrusted archives/configs in a valuable environment.

## Declared extras, not a certified matrix

`native`, `coco`, `research`, `geo`, `geometry-validation`, `environments`, `ultralytics`, `rfdetr`, `backbones`, `onnx`, `ort`, `openvino`, `dev`. Optional modern version ranges are installation declarations based on documented APIs, not transitive hash locks or tested pairings. Install conflicting frameworks in different worker environments. TensorRT/MMCV/CUDA stacks are user-supplied platform-specific installations, not core pip dependencies.
