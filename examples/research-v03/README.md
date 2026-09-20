# Procedural research examples

All images are software fixtures. The source tags do not turn generated images
into real aerial data. The tiny Faster R-CNN is a randomly initialized conformance
model; no pretrained checkpoint is downloaded.

From this directory (after installing `cvrs` and the native extra):

```text
cvrs campaign plan campaign.json
cvrs campaign run campaign.json --out six-arm-run
cvrs campaign run campaign.json --out six-arm-run --resume
cvrs campaign report six-arm-run --out six-arm-report
cvrs run-tiled inference.json --policy tiling.json --out tiled-runs
cvrs synthetic map sidecars/unreal-shaped.source.json --mapping sidecars/unreal-shaped.mapping.json --out mapped.json
cvrs dota import --images dota-images --labels dota-labels --categories dota-categories.json --name procedural-obb --dataset-version fixture-1 --out dota-images/dataset.json
```

The simulator-shaped exports are invented user-export examples, not native API
formats and not evidence that any simulator integration has been executed.
Run IDs/checkpoint references are execution-specific. Use the recorded checkpoint
hash to create an explicit checkpoint reference for trained tiled inference.
