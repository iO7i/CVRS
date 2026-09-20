# Eight independent examples

The source repository contains `examples/public/01-basic-detection` through `08-reproduction-registry`. Run each `run.py` with a new output directory. They use the installed public adoption API, not paths from an earlier session.

The CPU detector, raster and mask examples create real native models with random weights and generated images. These are execution/geometry examples, not scientific benchmarks. The heritage, cross-framework and open-vocabulary examples require your genuine native checkout, runs or weights. They report missing assets rather than substitute fake results.

```bash
python examples/public/01-basic-detection/run.py ./new-detection
python examples/public/02-mmdetection-heritage/run.py ./new-heritage --repo ./old-paper
python examples/public/03-cross-framework/run.py ./comparison --left ./run-A --right ./run-B
python examples/public/04-aerial-tiling/run.py ./new-raster
python examples/public/05-sim2real/run.py ./new-campaign --execute
python examples/public/06-open-vocabulary/run.py ./new-grounding --job ./grounding-job.json
python examples/public/07-segmentation/run.py ./new-masks
python examples/public/08-reproduction-registry/run.py ./new-registry
```

See [native packs](packs.md), [paper wrapping](heritage.md), [bridges](bridges.md) and [research controls](research.md).
