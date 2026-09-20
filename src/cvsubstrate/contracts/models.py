"""Version 1 contracts. No torch, numpy, raster, or simulator dependencies.

All geometry is continuous pixel-space xyxy in ORIGINAL image coordinates.
Integer boxes are accepted as JSON numbers, but string numbers are rejected.
Identifiers, list order, and category IDs are not silently rewritten.
"""
from __future__ import annotations
import math
import re
from pathlib import PurePosixPath
from typing import Annotated, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
SHA256 = Annotated[str, Field(pattern='^[a-f0-9]{64}$')]
ID = Annotated[str, Field(min_length=1, max_length=180, pattern='^[A-Za-z0-9][A-Za-z0-9_.:-]*$')]
PositiveInt = Annotated[int, Field(strict=True, gt=0)]
NonnegativeInt = Annotated[int, Field(strict=True, ge=0)]
Finite = Annotated[float, Field(strict=True, allow_inf_nan=False)]

def relative_path(value: str) -> str:
    """Portable relative POSIX paths only; traversal is always rejected."""
    p = PurePosixPath(value)
    if not value or p.is_absolute() or '..' in p.parts or ('\\' in value) or (':' in value):
        raise ValueError('expected a portable relative path without traversal or drive prefix')
    if str(p) != value or value == '.':
        raise ValueError('path must be normalized and identify a file')
    return value

class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, validate_assignment=True, allow_inf_nan=False)
    schema_version: Literal['1.0'] = '1.0'

    @model_validator(mode='before')
    @classmethod
    def reject_nonfinite(cls, value: Any) -> Any:

        def walk(x):
            if isinstance(x, float) and (not math.isfinite(x)):
                raise ValueError('non-finite values are prohibited, including backend metadata')
            if isinstance(x, dict):
                for v in x.values():
                    walk(v)
            if isinstance(x, (list, tuple)):
                for v in x:
                    walk(v)
        walk(value)
        return value

class LicenseInfo(Contract):
    code: str = 'unknown'
    weights: str = 'unknown'
    data: str = 'unknown'
    annotations: str = 'unknown'
    redistribution: Literal['allowed', 'prohibited', 'unknown'] = 'unknown'
    notes: str | None = None

class Category(Contract):
    id: NonnegativeInt
    name: Annotated[str, Field(min_length=1)]

class Box(Contract):
    xyxy: list[Finite] = Field(min_length=4, max_length=4)
    category_id: NonnegativeInt
    iscrowd: bool = False
    ignore: bool = False
    area: Finite | None = None

    @model_validator(mode='after')
    def geometry(self):
        x1, y1, x2, y2 = self.xyxy
        if x1 < 0 or y1 < 0 or x2 <= x1 or (y2 <= y1):
            raise ValueError('box must have nonnegative origin and strictly positive extent')
        if self.area is not None and self.area <= 0:
            raise ValueError('annotation area must be positive')
        return self

class GenerationMetadata(Contract):
    simulator: str | None = None
    simulator_version: str | None = None
    engine: str | None = None
    engine_version: str | None = None
    generation_revision: str | None = None
    scene_id: str | None = None
    asset_ids: list[str] = Field(default_factory=list)
    seed: NonnegativeInt | None = None
    units: dict[str, str] = Field(default_factory=dict)
    coordinate_convention: str | None = None
    planned: dict[str, Any] = Field(default_factory=dict)
    observed: dict[str, Any] = Field(default_factory=dict)
    # None means unmeasured, NOT zero occlusion/truncation.
    occlusion_fraction: Annotated[float, Field(strict=True, ge=0, le=1)] | None = None
    truncation_fraction: Annotated[float, Field(strict=True, ge=0, le=1)] | None = None
    visibility_definition: str | None = None
    annotation_method: str | None = None

class Sample(Contract):
    id: ID
    image: str
    sha256: SHA256
    width: PositiveInt
    height: PositiveInt
    source_kind: Literal['real', 'synthetic', 'unknown'] = 'unknown'
    domain: str = 'unknown'
    sensor: str | None = None
    lineage_group: str | None = None
    parent_ids: list[str] = Field(default_factory=list)
    boxes: list[Box] = Field(default_factory=list)
    geospatial: dict[str, Any] | None = None
    generation: GenerationMetadata | None = None
    _relative = field_validator('image')(relative_path)

    @model_validator(mode='after')
    def in_bounds(self):
        for box in self.boxes:
            if box.xyxy[2] > self.width or box.xyxy[3] > self.height:
                raise ValueError(f'box outside sample {self.id}')
        return self

class Split(Contract):
    role: Literal['train', 'dev', 'selection', 'locked_test']
    sample_ids: list[ID]

    @field_validator('sample_ids')
    @classmethod
    def unique(cls, value):
        if len(set(value)) != len(value):
            raise ValueError('duplicate sample IDs in split')
        if not value:
            raise ValueError('empty split is not an evaluation/training universe')
        return value

class DatasetManifest(Contract):
    name: ID
    version: str
    categories: list[Category] = Field(min_length=1)
    samples: list[Sample] = Field(min_length=1)
    splits: dict[str, Split]
    licenses: LicenseInfo = Field(default_factory=LicenseInfo)
    notes: str | None = None
    purpose: Literal['software_fixture', 'research_dataset'] = 'research_dataset'

    @model_validator(mode='after')
    def relationships(self):
        ids = [s.id for s in self.samples]
        cats = [c.id for c in self.categories]
        if len(set(ids)) != len(ids):
            raise ValueError('duplicate sample IDs')
        if len(set(cats)) != len(cats):
            raise ValueError('duplicate category IDs')
        if len({c.name for c in self.categories}) != len(cats):
            raise ValueError('duplicate category names')
        valid = set(ids)
        for name, split in self.splits.items():
            if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]*', name):
                raise ValueError('invalid split name')
            missing = set(split.sample_ids) - valid
            if missing:
                raise ValueError(f'split {name} references missing samples: {sorted(missing)}')
        for sample in self.samples:
            if any((b.category_id not in cats for b in sample.boxes)):
                raise ValueError(f'unknown category in {sample.id}')
        return self

class DetectionPrediction(Contract):
    sample_id: ID
    width: PositiveInt
    height: PositiveInt
    boxes: list[list[Finite]]
    scores: list[Annotated[float, Field(strict=True, ge=0, le=1)]]
    category_ids: list[NonnegativeInt]
    coordinate_frame: Literal['original_image_xyxy'] = 'original_image_xyxy'
    score_semantics: str = 'backend confidence, not calibrated probability'
    transform_provenance: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode='after')
    def valid(self):
        if not len(self.boxes) == len(self.scores) == len(self.category_ids):
            raise ValueError('prediction arrays must have identical lengths')
        for xyxy, category in zip(self.boxes, self.category_ids):
            b = Box(xyxy=xyxy, category_id=category)
            if b.xyxy[2] > self.width or b.xyxy[3] > self.height:
                raise ValueError('prediction box exceeds original image bounds')
        return self

class EvaluationProtocol(Contract):
    evaluator: Literal['diagnostic_detection', 'pycocotools'] = 'pycocotools'
    evaluator_version: str = '2.0.11'
    task: Literal['hbb_detection'] = 'hbb_detection'
    iou_thresholds: list[Finite] = Field(default_factory=lambda: [round(0.5 + 0.05 * i, 2) for i in range(10)])
    recall_thresholds: list[Finite] = Field(default_factory=lambda: [i / 100 for i in range(101)])
    area_ranges: dict[str, list[Finite]] = Field(default_factory=lambda: {'all': [0.0, 10000000000.0], 'small': [0.0, 1024.0], 'medium': [1024.0, 9216.0], 'large': [9216.0, 10000000000.0]})
    max_detections: list[PositiveInt] = Field(default_factory=lambda: [1, 10, 100])
    score_threshold: Annotated[float, Field(strict=True, ge=0, le=1)] = 0.0
    ignore_policy: Literal['reject_noncrowd_ignore_preserve_crowd'] = 'reject_noncrowd_ignore_preserve_crowd'
    tile_merge_policy: dict[str, Any] = Field(default_factory=lambda: {'kind': 'none'})
    image_universe: Literal['all_samples_in_selected_split'] = 'all_samples_in_selected_split'
    use_categories: Literal[True] = True

    @model_validator(mode='after')
    def settings(self):
        for key in ('iou_thresholds', 'recall_thresholds'):
            values = getattr(self, key)
            if not values or values != sorted(set(values)) or any((x < 0 or x > 1 for x in values)):
                raise ValueError(f'{key} must be sorted, unique, finite, and within [0,1]')
        if 0 in self.iou_thresholds:
            raise ValueError('IoU threshold must be positive')
        if len(self.max_detections) != 3 or self.max_detections != sorted(set(self.max_detections)):
            raise ValueError('three strictly increasing max_detections required')
        if 'all' not in self.area_ranges:
            raise ValueError('all area range required')
        for pair in self.area_ranges.values():
            if len(pair) != 2 or pair[0] < 0 or pair[1] <= pair[0]:
                raise ValueError('invalid area range')
        if self.evaluator == 'diagnostic_detection' and self.evaluator_version != '1':
            raise ValueError('diagnostic evaluator version is 1, not a COCO version')
        if self.evaluator == 'pycocotools' and self.evaluator_version != '2.0.11':
            raise ValueError('this foundation pins pycocotools 2.0.11')
        return self

class AdapterSpec(Contract):
    name: Literal['native_torch', 'mmdetection', 'external', 'ultralytics', 'rfdetr'] = 'native_torch'
    config: dict[str, Any] = Field(default_factory=dict)

class CheckpointRef(Contract):
    path: str
    sha256: SHA256
    trust: Literal['owned_weights_only', 'trusted_legacy_pickle'] = 'owned_weights_only'
    license: str = 'unknown'

class TrainingSpec(Contract):
    arm: Literal['R', 'S', 'R+S', 'S->R', 'R-replay', 'R->R'] = 'R'
    updates: PositiveInt = 2
    pretrain_updates: PositiveInt = 2
    real_per_update: PositiveInt = 1
    synthetic_per_update: PositiveInt = 1
    learning_rate: Annotated[float, Field(strict=True, gt=0)] = 0.001
    synthetic_weight: Annotated[float, Field(strict=True, gt=0)] = 1.0
    fairness: Literal['real_exposure_preserved', 'optimizer_updates_fixed'] = 'real_exposure_preserved'
    optimizer: Literal['sgd_momentum'] = 'sgd_momentum'
    precision: Literal['fp32'] = 'fp32'
    stage_transition: Literal['weights_only_reset_optimizer'] = 'weights_only_reset_optimizer'

class ExperimentSpec(Contract):
    name: ID
    dataset: str
    dataset_sha256: SHA256
    train_split: str = 'train'
    eval_split: str = 'dev'
    seed: NonnegativeInt = 17
    adapter: AdapterSpec = Field(default_factory=AdapterSpec)
    checkpoint: CheckpointRef | None = None
    training: TrainingSpec | None = None
    evaluation: EvaluationProtocol = Field(default_factory=EvaluationProtocol)
    preprocessing: dict[str, Any] = Field(default_factory=lambda: {'owner': 'worker', 'input': 'RGB uint8', 'controller_transforms': 'none', 'output_frame': 'original_image_xyxy'})
    notes: str | None = None

class FinalTestAuthorization(Contract):
    experiment_digest: SHA256
    dataset_digest: SHA256
    split: str
    approved_by: Annotated[str, Field(min_length=1)]
    approved_at: str
    purpose: Literal['final_evaluation_no_training'] = 'final_evaluation_no_training'
    acknowledge_policy_not_sandbox: Literal[True]

class TrainingTrace(Contract):
    update: PositiveInt
    stage: str
    real_sample_ids: list[str]
    synthetic_sample_ids: list[str]
    real_loss: Finite | None = None
    synthetic_loss: Finite | None = None
    nominal_synthetic_weight: Finite
    real_primary_sample_ids: list[str] = Field(default_factory=list)
    real_replay_sample_ids: list[str] = Field(default_factory=list)
    real_replay_loss: Finite | None = None
    weighted_total_loss: Finite
    gradient_influence: Literal['NOT_MEASURED'] = 'NOT_MEASURED'
    augmentation: Literal['no_stochastic_image_augmentation'] = 'no_stochastic_image_augmentation'

class AdapterCapabilities(Contract):
    input_formats: list[str] = Field(default_factory=list)
    output_formats: list[str] = Field(default_factory=list)
    training_contracts: list[str] = Field(default_factory=list)
    precisions: list[str] = Field(default_factory=list)
    adapter: str
    protocol_version: Literal['1.0'] = '1.0'
    tasks: list[str]
    operations: list[str]
    installed: bool
    execution_verified_in_this_process: bool = False
    limitations: list[str] = Field(default_factory=list)
    environment: dict[str, Any] = Field(default_factory=dict)

class WorkerRequest(Contract):
    protocol_version: Literal['1.0'] = '1.0'
    operation: Literal['capabilities', 'validate', 'predict', 'train']
    experiment: dict[str, Any] | None = None
    manifest: dict[str, Any] | None = None
    data_root: str | None = None
    output_dir: str | None = None
    checkpoint: dict[str, Any] | None = None
    final_test_authorization: dict[str, Any] | None = None

class WorkerResponse(Contract):
    protocol_version: Literal['1.0'] = '1.0'
    status: Literal['SUCCEEDED', 'FAILED']
    result: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, str] | None = None

class RunManifest(Contract):
    run_id: str
    experiment_digest: SHA256
    dataset_digest: SHA256
    state: Literal['RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED', 'INTERRUPTED']
    created_at: str
    finished_at: str | None = None
    failure: dict[str, str] | None = None
    note: str = 'Integrity evidence is not independent reproduction or scientific validity.'

class LegacyExperimentRef(Contract):
    upstream: Literal['open-mmlab/mmdetection', 'VBTI-development/onedl-mmdetection']
    revision: str
    framework_version: str | None = None
    config: str
    config_sha256: SHA256
    resolved_config_sha256: SHA256 | None = None
    config_graph_sha256: SHA256 | None = None
    checkpoint: CheckpointRef | None = None
    dataset_sha256: SHA256 | None = None
    taxonomy: list[Category] = Field(default_factory=list)
    environment_reference: str
    trust_executable_config: bool = False
    licenses: LicenseInfo = Field(default_factory=LicenseInfo)
    reference_dataset: str | None = None
    reference_protocol: dict[str, Any] = Field(default_factory=dict)
    reported_metrics: dict[str, Finite] = Field(default_factory=dict)
    status: Literal['REFERENCE_RECORDED', 'CONFIG_RESOLVED', 'INFERENCE_EXECUTED', 'OUTPUT_PARITY_VERIFIED', 'REFERENCE_METRIC_REPRODUCED', 'TRAINING_REPRODUCED'] = 'REFERENCE_RECORDED'
    compatibility_level: Literal['H0_CATALOGUED', 'H1_CONFIG_RESOLVED', 'H2_INFERENCE_EXECUTED', 'H3_OUTPUT_PARITY_VERIFIED', 'H4_REFERENCE_METRIC_REPRODUCED', 'H5_TRAINING_REPRODUCED'] = 'H0_CATALOGUED'
    evidence: dict[str, str] = Field(default_factory=dict)


class EnvironmentCapsule(Contract):
    name: ID
    adapter: str
    python: str
    packages: dict[str, str]
    source: dict[str, str | None] = Field(default_factory=dict)
    container_digest: SHA256 | None = None
    status: Literal['DECLARED', 'EXECUTION_VERIFIED'] = 'DECLARED'
    notes: str | None = None


class HeritageCertification(Contract):
    reference_digest: SHA256
    compatibility_level: Literal['H0_CATALOGUED', 'H1_CONFIG_RESOLVED', 'H2_INFERENCE_EXECUTED', 'H3_OUTPUT_PARITY_VERIFIED', 'H4_REFERENCE_METRIC_REPRODUCED', 'H5_TRAINING_REPRODUCED']
    evidence: dict[str, SHA256] = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    independently_reproduced: bool = False
    note: str = 'Certification is evidence-scoped; it does not imply official OpenMMLab endorsement.'
class ArtifactEntry(Contract):
    path: str
    sha256: SHA256
    bytes: NonnegativeInt
    _relative = field_validator('path')(relative_path)


class ArtifactManifest(Contract):
    algorithm: Literal['sha256'] = 'sha256'
    files: list[ArtifactEntry]
    root_digest: SHA256
    limits: str

    @model_validator(mode='after')
    def unique_paths(self):
        paths = [e.path for e in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError('duplicate artifact paths')
        if 'artifacts.json' in paths:
            raise ValueError('artifact manifest cannot hash itself')
        return self


SCHEMAS = [LicenseInfo, Box, Category, GenerationMetadata, Sample, Split, DatasetManifest, DetectionPrediction, EvaluationProtocol, AdapterSpec, CheckpointRef, TrainingSpec, ExperimentSpec, FinalTestAuthorization, TrainingTrace, AdapterCapabilities, WorkerRequest, WorkerResponse, RunManifest, LegacyExperimentRef, EnvironmentCapsule, HeritageCertification, ArtifactEntry, ArtifactManifest]
