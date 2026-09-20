# Evaluation and comparability

## Official reference path

`evaluator: pycocotools`, version `2.0.11`, invokes `COCO`/`COCOeval` directly.
The wrapper materializes IoU/recall thresholds, area ranges, max detections,
class awareness, image/category universes, score filtering, crowd semantics, and
output coordinate conventions. It extracts AP/AR from the reference precision
and recall arrays instead of assuming summarize() slots fit custom parameters.
Empty predictions use an empty detection COCO object, not a fake detection.

The four optional reference tests independently construct ground truth and detection
inputs and compare the wrapper against direct COCOeval for perfect, empty,
duplicate, and crowd cases. They could not run in the delivery sandbox because
pycocotools was absent and package downloads failed. **No reference parity is claimed.**

## Local diagnostic path

`evaluator: diagnostic_detection`, version `1`, performs explicitly documented,
class-aware greedy matching at fixed score and IoU thresholds, with stable tie order,
max detections, crowd absorption using detection-area overlap, and support counts.
It reports precision and recall, not interpolated AP. Undefined denominators yield
null with a reason. Diagnostic pixel-area slices measure matched-ground-truth
recall, not COCO AP-small. The result is marked `DIAGNOSTIC_NOT_COCO`.

No missing package causes automatic switching between these paths. The default
experiment contract requests the official path; generated offline demo specs
explicitly select diagnostics.

## Comparing runs

Results must contain a full comparison key and its valid digest. The key includes
dataset identity, selected split/sample universe, taxonomy, and all evaluator settings.
A mismatch returns INCOMPARABLE; insufficient metadata returns DESCRIPTIVE_ONLY.
Same measurement contracts return COMPARABLE_UNDER_DECLARED_PROTOCOL, with training
fairness separately marked NOT_ASSESSED.

This comparison never ranks models or asserts significance. Different weights are
an experimental variable. Different test images, thresholds, taxonomies, and tile
policies are measurement changes that require interpretation.
