# Explicit implementation boundaries — 0.5.1a1

The closure checklist is finite software scope, not a promise of universally correct research, automatic arbitrary-model migration, or every cross-product of task, framework and deployment runtime.

## Native integration remains provisional

MMDetection2/3/OneDL, Ultralytics, RF-DETR, SAM/SAM2, HF GroundingDINO, YOLO-World, foundation-feature providers and accelerator export/quantization paths contain native calls. Most have not run against installed external model libraries and pretrained checkpoints here. The generic CPU model paths do not certify those APIs. Real integration may expose further code defects; merely installing a GPU cannot be promised to close them.

The MM binding recipe supports a direct HBB CocoDataset while preserving its native pipeline. Composite training wrappers require explicit dataset-binding recipes. MM fixed-update execution verifies observed optimizer calls and restricts unsupported accumulation recipes. UL/RF paths remain native epoch trainers. The campaign compiler rejects unsupported equality constraints. It does not invent per-source gradient attribution or augmentation parentage when a native pipeline does not emit it. Distributed telemetry can aggregate declared per-rank observations; there is no automatic distributed scheduler or proof of collective communication.

## Raster and masks

The new HBB/quad/mask stream bounds its admitted tiles, decoded pixels, configured GDAL/SQLite caches, per-tile prediction bytes and sparse-mask run counts. Optional RSS admission observes process pressure. These are not hard limits on arbitrary model allocations, CUDA drivers or third-party memory. The raster source must have appropriately bounded blocks; giant compressed blocks can be rejected. The source does not need to fit in memory, but disk capacity, output size and evaluator memory still matter.

Mask association is an explicit deterministic greedy same-class cross-tile IoU winner/union policy. It is not perfect instance identity, multi-object tracking or embedding association. Sparse union/placement preserves its declared pixel-grid semantics. Complex RLE may exceed a configured run limit and fail rather than grow without bound. Mask GeoJSON output is labeled as bounding-region geometry, not an exact mask vectorization. Coordinate transforms retain the declared CRS; unknown GSD/altitude remain unknown.

The sensor contract represents optical, SAR and multi-band metadata and normalization. The included tiny torchvision conformance networks have three input channels. A real multispectral model must declare and implement matching channel semantics; the stream does not synthesize such an architecture.

## Prompting and evaluations

PromptSet can represent text, positive/negative points, boxes, masks, exemplar images/regions and concepts. Native SAM/SAM2 recipes implement the supported point/box/mask combinations and iterative corrections. The stock models do not accept arbitrary exemplar/concept inputs; the negotiation layer rejects these rather than silently changing meaning. Supporting a prompt data type is distinct from claiming every model supports it.

Canonical task outputs remain separate. COCO HBB, COCO masks and DOTA OBB run through their reference evaluators when available. Grounding/open-set, mask-boundary and size diagnostics have their own definitions. None is renamed official AP. Image-population slices preserve all selected-image objects and the negative-image universe; official object-size metrics use reference area/ignore semantics.

Frozen final artifact-only analyses across tasks use counted input-bound approvals. This is accountability through the tool, not cryptographic confidentiality of local test files. Direct filesystem access is outside the policy's control.

## Artifacts, protocols and registry

The v1 facade and component protocol identities are explicit. Only registered migrations and preserved historical fixtures are promised; unknown schemas fail. The canonical JSON definition is CVRS sorted finite Python JSON, not RFC8785/JCS. Model/config/asset IDs only cover declared captured inputs; unresolved imports are reported, not guessed.

Worker processes isolate dependency environments. They are not hostile-code sandboxes. Configs, plugins, native model code and explicitly trusted checkpoint serializers can execute code. Timeouts/cancellation terminate owned processes, but OS-specific behavior is only exercised on the current Linux environment.

Ed25519 signatures bind records/exchanges to keys. Identity attestations remain explicit and externally reviewable; a valid signature does not prove scientific truth, different operators, or organizational independence. R4/R5 require evidence and reviews; this release earns no genuine independent scientific R4/R5 result.

Independent registry copies merge immutable records and event branches transactionally. There is no hosted server or distributed locking across machines. Private keys are never bundled. Legacy registry migration preserves unknown old content rather than inventing structured claims or trust.

## Not included in these five slices

Cloud stores/schedulers, live simulator control, video/pose/3D/robotics, arbitrary future model coverage, dataset/model hosting and Slice 6 public productization are outside the frozen closure denominator. The source license and final brand remain owner decisions. Nothing was published remotely.

## Meaning of the local smoke

All newly trained models use procedural fixtures and random initialization. Original/reproduction pairs run on the same machine by the same builder. Their R3 label is scoped to the recorded fixture metrics, not an independent paper reproduction. A low declared mask threshold exercises nonempty random-model masks; it is not a research recommendation. Failed earlier development runs remain historical evidence and are not mixed into the final pass count.
