# RFC-001 — actual cross-framework evidence slice

Status: proposed, not implemented evidence.

Run one trusted MMDetection/OneDL detector and one standard pretrained native model
under separate environments. Use allowed data, exact taxonomy, native preprocessing,
original-image output mapping, and pinned official COCO evaluation. Preserve raw
upstream predictions and compare against canonical conversion without repairing
numerical differences by altering goldens. Verify source revisions independently.

Acceptance: reference parity, config/checkpoint/source identity, native output
mapping tests, documented adapter effort, and an external user's clean reproduction.
A benchmark leaderboard, more model families, GPUs, or a dashboard are not required.
