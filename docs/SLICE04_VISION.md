# Slice 4 — modern vision interoperability

## Implemented task boundaries

`GroundedPrediction` keeps original-image boxes, native scores, phrases, exact prompt, provenance and optional token spans. `PromptSpec` records whether input is human, fixed-protocol, upstream-model or ground-truth-oracle. Mapping phrases to a closed taxonomy is explicit and audited; missing mappings fail instead of dropping predictions. A mapped closed-set AP does not prove open-vocabulary generalization.

`MaskPrediction` and `MaskAnnotation` use a validated, uncompressed COCO-order binary RLE. Initial runs represent background and flattened order is column-major. Instance identity, category, prompt and native quality are separate. A predicted mask-quality value is not automatically a calibrated probability. Duplicate instances, wrong dimensions and unknown prompt IDs fail validation.

Mask crop/resize/flip/paste are explicit bounded transformations. Union across tiles requires the caller to identify the same instance; the repository does not magically associate objects across independently predicted tile masks. Prompt evaluation binds prompt IDs to targets in advance, selects candidates by native quality, and reports oracle involvement. It never selects the best mask using ground-truth IoU after the fact.

Official instance mask evaluation delegates to an isolated `pycocotools==2.0.11` worker; crowd/ignore and image/category universe are explicit. That reference dependency is unavailable in this environment. Diagnostic prompt IoU and official segmentation AP are distinct outputs.

## Native integrations

- HF Grounding DINO: local processor/tokenizer/config and safetensors; text-grounded regions.
- HF SAM: local processor/SAM safetensors; point/box prompts.
- SAM2: explicitly trusted local config/checkpoint; point/box prompts. Native mask-logit/text prompting is not implemented by this adapter.
- YOLO-World: local detector and text-encoder cache; ordered phrase mapping.
- Ultralytics segmentation: native instance masks and detection confidences.
- Existing UL/RF specialist workers and timm/HF/DINO backbone providers remain separate, rather than being reimplemented.
- `torchvision_mask`: a genuine small Mask R-CNN with owned local weights for executable CPU conformance. It is not a substitute for proving pretrained SAM/GroundingDINO operation.

Every `VisionJob` validates local file hashes, image IDs and prompt provenance. The controller verifies canonical outputs, the complete image universe and preserved native prediction artifacts, then seals the bundle. Standalone image-list vision jobs are restricted to development/selection roles; protected final-test use requires a future benchmark-bound vision execution integration. A metadata role is accountability, not file secrecy.

No native worker silently downloads a model. Explicitly executable configs/checkpoints remain trusted-code boundaries. Native integrations may need changes after execution against the chosen upstream versions; version ranges alone are not compatibility evidence.

## SDK and comparability

`adapter-recipes scaffold` generates an external project and descriptor with trust disabled. Inspect it, install it in an adapter interpreter, then explicitly enable trust to execute it via `plugin run`. The builder exercised real mask inference through such a generated adapter, including malformed-input rejection and sealed artifacts.

`vision compare` compares data/split/taxonomy/evaluator/preprocessing identities, task and prompt protocols. It does not rank mask IoU against box AP or treat oracle prompting as fair autonomous detection. Training/pretraining fairness remains a separate assessment.

## Gates

| Original gate | Code and local evidence | Still required for scientific completion |
|---|---|---|
| G4.1 Contemporary specialist | UL/RF train/predict/export/native telemetry calls | Real upstream environment and checkpoint run |
| G4.2 Foundation representation | Local providers, detector wrapper, geometry receipts | Real pretrained foundation-backbone downstream experiment |
| G4.3 Open vocabulary | Grounding/phrase/prompt contracts and optional native calls | Real pretrained text-conditioned execution |
| G4.4 Segmentation | Real CPU Mask R-CNN training, exact raw-mask/RLE equality; reference worker | Official reference AP and pretrained promptable model execution |
| G4.5 Isolation | Actual external adapter and core/native process paths | Two actual conflicting external model stacks |
| G4.6 SDK | Generated external project executes native prediction without core edits | Broader adapter recipes/version coverage |
| G4.7 Cross-paradigm report | Protocol-aware reports and mismatch tests | Real four-paradigm research report |
| G4.8 Independent adapter | Runnable scaffold and documented protocol | Independently authored adapter, not builder self-verification |
