# Reference integrations and source notes

Source inspections inform adapter boundaries; they are not execution certifications.
Accessed for this implementation on 17 September 2026.

## COCO

Primary implementation:
https://github.com/cocodataset/cocoapi/blob/master/PythonAPI/pycocotools/cocoeval.py

Package selected by the existing repository: `pycocotools==2.0.11`.
https://pypi.org/project/pycocotools/

The controller wrapper and independently constructed direct-reference inputs use
the same pinned package. The current build environment could not install it;
reference tests remain explicitly skipped. No diagnostic is relabeled COCO AP.
Nonfinite parity tolerances and development/locked-test misuse are rejected before
calling optional reference code.

## DOTA

Dataset descriptions and Task1 format:
https://captain-whu.github.io/DOTA/dataset
https://captain-whu.github.io/DOTA/tasks.html

Inspected function signature (`voc_eval`, IoU threshold and VOC07 option):
https://github.com/CAPTAIN-WHU/DOTA_devkit/blob/master/dota_evaluation_task1.py

`cvrs dota reference` executes a caller-supplied, hash-bound, trusted reference
module in a selected Python environment. It preserves upstream stdout and returns
native per-class outputs. It does not vendor or substitute compiled `polyiou`.
The inspected upstream revision imports legacy dependencies, including NumPy APIs
that may need an appropriate historical environment. No silent patch is applied.
Empty/undefined class problems are explicit failures, never invented detections
or selectively dropped classes. The small fake module in tests verifies only
shim plumbing and is clearly labeled as such. Genuine DOTA reference parity and
real-dataset evaluation remain NOT_RUN.

The local DOTA importer requires eight coordinates, a declared class and an
explicit 0/1 difficult flag. Out-of-image vertices and metadata hashes are retained.
It does not guess dataset version, splits, GSD, or licensing. Only PNG/JPEG source
images are accepted by this initial label importer.

## MMDetection catalogue

Each entry in `heritage/catalogue.json` retains its inspected primary source URL.
The catalogue includes TOOD, Faster R-CNN, FCOS, RetinaNet, DINO and Deformable DETR
metadata, plus an ATSS discovery-only entry. Unknown checkpoint hashes and licenses
remain unknown. Main-branch metadata is marked as a source reference, not falsely
presented as a verified execution commit. Running a historical checkpoint still
requires exact trusted source/config/checkpoint/dataset/environment identities.

## Rotated geometry

Conventions considered:
https://mmrotate.readthedocs.io/en/latest/intro.html

This release uses explicitly named angle converters and polygon interchange;
framework-wide MMRotate compatibility has not been established.

## External UAV/Unreal/Colosseum paper

The external research discussed by the owner is prior art, not the owner's paper
and not a result of this repository. Its simulation/model separation motivated
optional camera, scene, sensor and environmental provenance. No code, model result,
dataset or simulator implementation from that paper is claimed as reproduced.
