# Incremental migration

## Existing COCO predictions

Keep your inference unchanged. Use the existing canonical import/conversion and reference evaluator paths, recording category mapping, score filtering and source-image coordinates. Inspect the conversion audit before comparing numbers.

## OpenMMLab or Detectron2

Preserve the working interpreter and native graph. Use `inspect-repo`, then a dedicated stack payload or an explicit paper wrapper. Retain the original config/base files and checkpoint identity.

## Ultralytics or RF-DETR

Supply a canonical ExperimentSpec to their native pack. Native epoch-based training is not silently equated to fixed-update/source-preserving campaigns.

## Plain PyTorch

Use the public adapter SDK or reviewed argv wrapper. A model need not inherit a CVRS model class. Normalize only the output contract you actually understand.

## Analysis and tracking

Export selected canonical artifacts into your existing tools. HBB-only bridges reject mask-bearing inputs instead of silently dropping them. No dashboard migration is required.

## Exit without lock-in

Canonical JSON/JSONL, COCO/DOTA/GeoJSON/mask encodings, portable evidence and local registry exports remain readable without a hosted CVRS service. Optional formats have their own loss/semantics reports.
