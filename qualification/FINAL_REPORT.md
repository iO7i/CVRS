# CVRS Alpha Freeze — current report

Status: `H2_ALPHA_RELEASE_CANDIDATE_READY`

Reference Qualification 002 began on the local CVRS `0.7.1a2` controller workspace and is preserved chronologically below. Reference Qualification 001 remained frozen and was not reopened. The H2 closeout packages the final qualification state as `0.7.1a3`; earlier sections record campaign-time observations and should not be read as the current publication gate.

## Completed

- Preserved the dirty prior builder workspace without reset or overwrite.
- Created a new local Git workspace on `alpha-freeze-rq002-local`.
- Recorded source-only and workspace inventories with SHA-256 file maps.
- Captured bounded local hardware/tool/storage state.
- Added the H0 packet, RQ002 campaign contract, input/model lock placeholders,
  support matrix, limitations, and resume record.
- Validated 13 lanes and R2.01–R2.25 contract shape.
- Ran 564 passing CPU/controller tests with 105 skips, the targeted RQ002 plan
  guard after its status correction, Ruff, and a successful wheel/sdist build.
- Applied the approved storage amendment: D: 30.07 GiB observed free, 10 GiB
  reserve, 18 GiB local qualification ceiling, and Modal Tier 2 cap of $8.
- Staged the bounded COCO val2017-128 public anchor locally with per-image
  hashes and a frozen selection digest; the workstation’s HTTPS certificate
  mismatch forced the official HTTP endpoint and is preserved as a limitation.
- Completed bounded local SDK smokes without model downloads or paid compute:
  Supervision 0.30.4 preserved 128 COCO images, 906 annotations, and 80
  categories; TorchGeo 0.10.0 read four CRS-aware windows from a deterministic
  GeoTIFF fixture; FiftyOne 1.22.0 imported/exported 32 COCO images and 223
  detections while recording its explicit detection/segmentation fields and
  used-category remapping behavior.
- Built the bounded H1 local-SDK review packet for two COCO images. Both SDK
  paths preserve box counts and category names on those images; maximum
  observed coordinate drift is below `0.00003 px`. The packet also exposes the
  FiftyOne category-table/segmentation-field limitations and TorchGeo fixture
  lineage. The subsequent scoped approval is recorded below.
- Recorded the user's explicit `APPROVE_LOCAL_SDK_H1` decision against the
  frozen review-page hash. The approval is deliberately limited to the local
  SDK scope.
- Completed independent CVRS HBB paths for Supervision and FiftyOne on the
  same frozen 32-image/223-object COCO slice. Each path ran through a real SDK
  worker and returned to CVRS's canonical contract with zero audit differences
  at the preregistered `1e-9` coordinate tolerance. R2.17 and R2.18 are now
  bounded passes; FiftyOne mask fidelity is still explicitly not claimed.
- Preserved the initial failed controller attempt, which exposed an
  unnecessary NumPy dependency in box-only FiftyOne import. NumPy is now
  loaded only for mask reconstruction and a regression test proves the HBB
  path works in the minimal controller environment.
- Qualified TorchGeo 0.10.0 against a pinned, rights-linked public Rasterio
  GeoTIFF. Four real 128x128 windows preserve source identity, CRS, bands,
  nodata, bounds, transform, native values, and CVRS lineage. The native
  reader's 354/196,608 value differences at nodata boundaries are preserved
  and disclosed rather than normalized away. R2.11 passes.
- Executed MMDetection 3.3.0 with RTMDet-tiny on a T4 against two frozen COCO
  images. Native and separately wrapped runs produced the same 600 detections
  under the preregistered repeatability criterion. Strict CVRS conversion then
  rejected 95 native boxes outside canonical image bounds. No clipping,
  filtering, training, or protected-data access occurred; R2.05 therefore
  remains an evidence-backed failure.
- Executed MMDetection 2.28.2 / RetinaNet on the exact same two COCO bytes.
  Native inference, one-for-one saved-native conversion, and separate wrapped
  execution pass with 106 finite, ordered, in-bounds detections. R2.04 passes.
- Executed MMRotate 0.3.4 / Oriented R-CNN on one frozen official demo tile.
  Native, saved-native, and wrapped paths preserve all 115 detections. Eight
  of 460 out-of-image polygon vertices remain unchanged under the explicit
  oriented contract. R2.06 passes; the legacy CUDA failure remains archived.
- Executed MMSegmentation 1.2.2 / FCN-R50 on one public ADE20K example image.
  Native and wrapped outputs are exactly equal, and CVRS preserves all
  3,145,728 label values at 1536×2048. R2.07 passes; evaluator equivalence is
  not claimed because registered ADE20K ground truth was not acquired.
- Exported the frozen RTMDet path with MMDeploy 1.3.1 and ran it twice through
  ONNX Runtime 1.16.3 on CPU. Export/checker and exact runtime repeatability
  pass, but transport fidelity and strict canonical conversion fail because
  six adjacent outputs reorder and 22/300 raw boxes exceed image bounds.
  R2.08 remains a truthful failure without geometry modification.
- Executed Ultralytics 8.4.0 / YOLO26n on the same two frozen COCO images.
  Native inference, saved-native conversion, and separate wrapped execution
  agree exactly on 304 finite, ordered, in-bounds detections. The native ONNX
  export passes checking and repeats exactly under CPU ONNX Runtime, but
  deployment fidelity fails because ORT emits 305 detections and does not
  preserve native ordering, coordinates, or scores. TensorRT was not run.
- Froze the Grounding DINO tiny model, implementation, prompts, thresholds,
  and two images. The first qualification attempt reached native
  post-processing but the wrapper rejected an orchestrator request missing
  `protocol_version`; ephemeral predictions were not returned. The failure is
  preserved and no automatic paid retry occurred.
- Prepared one combined approval packet for exactly one corrected Grounding
  DINO retry and the gated SAM 3 / DINOv3 acquisitions. It records revisions,
  checkpoint identities/sizes, licenses, access requirements, runtimes, and a
  `$0.40` additional ceiling.
- Prepared the consolidated OpenMMLab H1 review packet after all three required
  native lanes received actual dispositions.
- Reconciled provider billing at `$0.10523341`, including preserved failed
  attempts, leaving `$7.89476659` under the approved RQ002 cap.

## Not completed by design

- H1 is approved only for the limited local-SDK scope. The requested OpenMMLab
  core sequence and deployment lane have actual dispositions; remaining
  foundation-model lanes, mask fidelity, and H2 remain unrun or incomplete.
- R2.17 and R2.18 pass for bounded HBB interchange. R2.19 remains partial
  because zero-silent-loss evidence does not yet cover the other geometry
  families and model lanes.
- D: fell to 2.58 GiB free during verification for causes outside this
  workspace. Pruning only qualification-owned environments, caches, raw COCO
  transport bytes, and duplicate SDK image copies recovered it to 5.95 GiB.
  That is still below the 10 GiB reserve, so new local acquisition is blocked
  until unrelated storage pressure is resolved; no unrelated files were
  deleted.
- Mypy is not clean under the existing broad configuration. The three modern
  detector/vision worker files touched by this phase now pass targeted mypy;
  the broader historical baseline remains a disclosed limitation.

## Release conclusion

RQ002 remains active and overall `NOT_QUALIFIED`. R2.05 and R2.08 preserve real
compatibility failures, Ultralytics adds a native/CVRS pass plus an ONNX
fidelity failure, and Grounding DINO passes its approved corrected retry. SAM 3
and DINOv3 remain access-blocked. Their public fallback block is complete:
SAM 2.1 truthfully fails at native mask postprocessing after GPU forward, while
DINOv2 passes bounded global/dense feature extraction, exact reload, and
two-image self-retrieval. The consolidated modern H1 packet is ready for human
review. This is not yet an alpha qualification or a claim that all native lanes
are supported.

## H2 alpha-freeze closeout

H2 is complete as `H2_ALPHA_CANDIDATE_READY`. This does not turn the preserved
lane failures or external blockers green. The frozen foundation outcomes are:
DINOv2 `PASS`; SAM 2.1 `FAIL_NATIVE_RUNTIME_COMPATIBILITY`; SAM 3 and DINOv3
`BLOCKED_EXTERNAL_ACCESS`. Grounding DINO's successful corrected retry was
reused and not rerun. No further model substitution occurred.

The `0.7.1a3` candidate passes 567 controller tests, Ruff, maintained-scope
mypy, strict documentation and local-link checks, direct wheel installation,
and independent sdist rebuild/installation. A wheel-only clean room with no
source checkout or ML frameworks verified the RQ001/RQ002 evidence capsule,
rendered the final 20-lane browser, re-evaluated saved DINOv2 retrieval without
model inference, and rejected tampered and missing evidence.

The package remains an unpublished public-alpha candidate, not 1.0. Owner identity, repository and Apache-2.0 license metadata are now configured; publication still requires the final mechanical release gates and explicit remote push. The authoritative H2 review, matrix, release checks, clean-room report, dependency audits, and offline browser are under `qualification/h2/`.
