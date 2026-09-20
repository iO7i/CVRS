# Evidence-first roadmap

## Next bounded milestone: measured interoperability

Run the optional direct COCO parity tests. Certify one actual MMDetection/OneDL
config/checkpoint in a separate environment, with verified upstream revision,
config inheritance, checkpoint identity, raw/canonical prediction arrays, and
metric agreement. Add a normal pretrained torchvision or DETR adapter without
changing core contracts. Use allowed real data and document its license.

## Then: a useful research slice

Integrate the tested HBB tiling utilities end-to-end, recording crop/resize/padding
and merge policies. Add a dataset-specific tiny-object evaluation protocol and
appropriate real/synthetic/replay controls. Make data and run artifacts usable by
an independent researcher. Add calibrated uncertainty only with a justified
resampling unit and enough independent evaluation support.

## Later, only when demonstrated

OBB geometry/evaluation; geospatial reprojection; foundation-backbone and grounding
adapters; actual simulator integrations; supported checkpoint migration; model export
and deployment parity; GPU/multi-GPU training; robust interrupted-run orchestration;
external plugin distribution; signed artifacts; stronger sandboxing; a stable 1.0 API.

Each feature needs semantic tests, real execution, documented limitations, compatible
licensing, and independent review where numerical/scientific correctness matters.
There is no promise to reimplement every historical OpenMMLab algorithm.
