# Primary engineering references consulted

These links document APIs used; they do not certify this implementation. Versions
actually executed are in evidence, and live documentation may describe newer APIs.

- torchvision Faster R-CNN class and extension points:
  https://docs.pytorch.org/vision/stable/_modules/torchvision/models/detection/faster_rcnn.html
- Official COCO API and evaluator:
  https://github.com/cocodataset/cocoapi
  https://github.com/cocodataset/cocoapi/blob/master/PythonAPI/pycocotools/cocoeval.py
- Pinned optional Python distribution and release provenance:
  https://pypi.org/project/pycocotools/2.0.11/
- MMDetection 3.x native inference:
  https://mmdetection.readthedocs.io/en/3.x/user_guides/inference.html
- Pydantic model/validation semantics:
  https://docs.pydantic.dev/latest/concepts/models/

The user's supplied research was used as design context, not silently promoted to
verified repository-maintenance facts. This implementation does not repeat an
unverified 2026 ecosystem census or assign external research to the project owner.
