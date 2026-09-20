# Native stack packs

Every job runs a whole supported native graph. Configs, checkpoints and input images must have explicit hashes. Call `stack run FAMILY OPERATION payload.json --out NEW --python NATIVE_PYTHON --trust`.

| Pack | Job input | Output/task |
|---|---|---|
| MMDetection2 / MMDetection3 / OneDL | config + checkpoint + category mapping + images | HBB; original outputs retained |
| MMRotate | same plus explicit native angle convention | oriented quadrilaterals, not axis-aligned approximations |
| MMseg0 / MMseg1 | config + checkpoint + images + ignore/reduce-zero policy | original-size integer semantic label arrays |
| MMYOLO | native config + checkpoint + category mapping + images | HBB |
| MMDeploy | hashed native deploy entrypoint, deploy/model configs, checkpoint and image | native exported artifacts; fidelity not assumed |
| Detectron2 | YACS config, checkpoint, mapping and images | boxes and optional native instance masks; DefaultTrainer is native training |
| Ultralytics / RF-DETR | `{"experiment":"canonical-experiment.json"}` | existing canonical native train/predict/export service |
| Grounding DINO / SAM / SAM2 | `{"job": ...}` using the registered VisionJob schema | grounded regions or prompted masks |
| SAM3 | local model assets + images + exact text prompts | grounded-mask sidecar, explicit prompt source |
| TorchGeo | dataset class, kwargs and explicit sampling/query specification | native arrays and geospatial metadata |
| TerraTorch | hashed config, optional checkpoint and native CLI args | native outputs, selected task requires its own decoder |

For native MM training, supply the actual `tools/train.py` (or paper-specific entrypoint) and hash. This is not a universal dataset rewrite or a claim that every custom training loop emits equivalent telemetry.

## Minimal native detection payload

```json
{
  "repo":"/path/to/source",
  "config":"/path/to/config.py","config_sha256":"REPLACE_WITH_SHA256",
  "checkpoint":"/path/to/checkpoint.pth","checkpoint_sha256":"REPLACE_WITH_SHA256",
  "category_mapping":{"0":3,"1":17},
  "images":[{"id":"sample-1","path":"/path/to/image.png","sha256":"REPLACE_WITH_SHA256"}],
  "device":"cpu"
}
```

This is a template, not a valid job until the real hashes/assets are supplied. Run `schema inspect VisionJob` for prompted-model fields. Defaults never download weights.

## Preparation recipes

PWOOD, SegEarth-OV3, DEIM and Bridge recipes record inspected primary sources. UAV-SynthScene is an external-paper archetype without a verified code checkout. None is labeled executed. `recipe materialize` makes the unresolved assets and revisions visible rather than inventing a ready-to-run environment.
