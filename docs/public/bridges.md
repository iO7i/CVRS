# Join the tools a lab already uses

`cvrs bridge list` lists finite native operations. `cvrs bridge run job.json --trust` executes a selected SDK in its worker. A remote operation additionally needs `--allow-network` and `acknowledge_external_transfer` in its payload. No service is contacted by merely listing bridges.

| Bridge | Implemented boundary |
|---|---|
| FiftyOne | HBB dataset/prediction export with source identity and ignore/crowd metadata; selected local prediction import |
| Supervision | HBB arrays with exact class IDs, scores and pixel coordinates; mask-bearing data is rejected by the HBB-only importer |
| W&B | Offline-first run/metric/evidence export; immutable-version artifact import with network opt-in |
| MLflow | Local or explicitly remote run metadata/artifacts; explicit existing-model URI registration; run metadata import |
| DVC | Pinned revision reference resolution and bounded checksum-verified reads |
| HF | Revision-resolved metadata; explicit selected-file locking; local full-component identity |
| TorchGeo | Explicit native dataset/sampler query and non-pickle raster/mask export |
| TerraTorch | Native installed CLI entrypoint for fit/predict; task-specific output normalization remains explicit |
| timm | Local model/feature geometry and checkpoint identity, no implicit pretrained download |
| OpenML | Explicit task/run metadata mapping; no automatic detection-to-tabular benchmark fiction |
| Code Ocean | Upload-preparation files and environment/run requirements, not a remotely created or verified capsule |

These bridges do not replace the native product. An external library's absence is a structured error. Source media, model weights and private artifacts are excluded unless the caller specifically authorizes them.

## Prepare a detection bundle

```bash
cvrs bridge bundle-detections dataset.json predictions.jsonl --image-root ./data --out bridge-input.json
```

Example Supervision job:

```json
{"bridge":"supervision","operation":"export","output_dir":"new-export","payload":{"bundle":"bridge-input.json"}}
```

Review [security](security.md) before a cloud transfer. Native signatures are version-sensitive and remain provisional until your pinned environment is exercised.

## Synthetic producers

`bridge simulator` reads BlenderProc-style COCO annotations and Replicator BasicWriter bounding-box arrays/labels. Unreal/Colosseum/Isaac/custom sidecars require an explicit field mapping. Raw metadata and unknown fields remain preserved. No simulator is installed or launched. Missing camera/scene/seed metadata stays unknown.
