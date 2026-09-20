# Primary API references consulted for the 0.4 implementation

Reviewed during this build on 18 September 2026. This bibliography supports API choices, not execution claims. Project/runtime dependencies must be pinned by the user to a compatible version before meaningful reproduction.

- MMDetection: https://mmdetection.readthedocs.io/en/latest/ and https://mmdetection.readthedocs.io/en/v3.0.0rc0/user_guides/train.html
- OpenMMLab source/version identity: https://github.com/open-mmlab/mmdetection
- OneDL: https://github.com/vbti-development/onedl-mmdetection
- Ultralytics predict/train/export: https://docs.ultralytics.com/modes/predict/ , https://docs.ultralytics.com/modes/train/ , https://docs.ultralytics.com/modes/export/
- Ultralytics OBB original-image corner API: https://docs.ultralytics.com/tasks/obb/
- RF-DETR training/reference: https://rfdetr.roboflow.com/learn/train/ , https://rfdetr.roboflow.com/latest/reference/rfdetr/
- timm features: https://huggingface.co/docs/timm/feature_extraction
- Hugging Face backbones: https://huggingface.co/docs/transformers/main_classes/backbones
- DINO local code: https://github.com/facebookresearch/dinov2 and https://github.com/facebookresearch/dinov3
- PyTorch export: https://docs.pytorch.org/docs/stable/export.html
- PyTorch ONNX: https://docs.pytorch.org/docs/stable/onnx.html
- ONNX Runtime Python: https://onnxruntime.ai/docs/api/python/api_summary.html
- TensorRT Python: https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/python-api-docs.html
- OpenVINO conversion: https://docs.openvino.ai/2025/openvino-workflow/model-preparation/convert-model-to-ir.html
- DOTA reference: https://github.com/CAPTAIN-WHU/DOTA_devkit
- COCO reference: https://github.com/cocodataset/cocoapi
- VisDrone: https://github.com/VisDrone/VisDrone-Dataset
- xView utilities: https://github.com/DIUx-xView/xView1_baseline

No upstream model implementation, checkpoint, dataset, or licensed asset was bulk-vendored. Code/weights/data/config licensing remain separate metadata and owner review responsibilities.
