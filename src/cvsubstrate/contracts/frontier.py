"""Task-specific Slice 4/5 contracts; deliberately no heavyweight dependencies."""
from __future__ import annotations
from typing import Any, Literal
from pydantic import Field, model_validator, field_validator
from cvsubstrate.contracts.models import Contract, ID, SHA256, PositiveInt, NonnegativeInt, Finite, relative_path

class PromptSpec(Contract):
    id: ID
    sample_id: ID
    kind: Literal['text', 'points', 'box', 'mask']
    text: str | None = None
    points: list[list[Finite]] = Field(default_factory=list)
    point_labels: list[Literal[0, 1]] = Field(default_factory=list)
    box: list[Finite] | None = None
    mask_reference: str | None = None
    source: Literal['human', 'fixed_protocol', 'upstream_model', 'ground_truth_oracle']
    source_artifact_sha256: SHA256 | None = None
    @model_validator(mode='after')
    def consistent(self):
        if self.kind == 'text' and (not self.text or not self.text.strip()):
            raise ValueError('text prompt requires exact nonempty text')
        if self.kind == 'points' and (not self.points or len(self.points) != len(self.point_labels)):
            raise ValueError('points and labels must be nonempty and aligned')
        if any(len(p) != 2 or min(p) < 0 for p in self.points):
            raise ValueError('point coordinates must be nonnegative xy pixels')
        if self.kind == 'box':
            if self.box is None or len(self.box) != 4 or min(self.box[:2]) < 0 or self.box[2] <= self.box[0] or self.box[3] <= self.box[1]:
                raise ValueError('box prompt requires valid pixel xyxy')
        if self.kind == 'mask' and not self.mask_reference:
            raise ValueError('mask prompt requires reference')
        if self.kind != 'text' and self.text is not None: raise ValueError('unexpected text')
        if self.kind != 'points' and (self.points or self.point_labels): raise ValueError('unexpected point fields')
        if self.kind != 'box' and self.box is not None: raise ValueError('unexpected box')
        if self.kind != 'mask' and self.mask_reference is not None: raise ValueError('unexpected mask')
        return self

class GroundedPrediction(Contract):
    sample_id: ID
    width: PositiveInt
    height: PositiveInt
    prompt: PromptSpec
    boxes: list[list[Finite]]
    scores: list[Finite]
    phrases: list[str]
    token_spans: list[list[int] | None] = Field(default_factory=list)
    native_output_sha256: SHA256 | None = None
    @model_validator(mode='after')
    def valid(self):
        if self.prompt.sample_id != self.sample_id or self.prompt.kind != 'text': raise ValueError('wrong prompt/sample')
        if not len(self.boxes) == len(self.scores) == len(self.phrases): raise ValueError('arrays differ')
        if self.token_spans and len(self.token_spans) != len(self.boxes): raise ValueError('span count differs')
        for b, s, phrase in zip(self.boxes, self.scores, self.phrases):
            if len(b) != 4 or b[0] < 0 or b[1] < 0 or b[2] <= b[0] or b[3] <= b[1] or b[2] > self.width or b[3] > self.height: raise ValueError('box out of bounds')
            if not 0 <= s <= 1 or not phrase.strip(): raise ValueError('invalid confidence/phrase')
        return self

class MaskRLE(Contract):
    """Uncompressed COCO-column-major binary RLE, initial run always background."""
    height: PositiveInt
    width: PositiveInt
    counts: list[NonnegativeInt] = Field(min_length=1)
    order: Literal['F'] = 'F'
    @model_validator(mode='after')
    def valid(self):
        if sum(self.counts) != self.height * self.width: raise ValueError('RLE length differs from dimensions')
        if any(v == 0 for v in self.counts[1:]): raise ValueError('noncanonical zero run')
        return self

class MaskInstance(Contract):
    id: ID
    mask: MaskRLE
    score: Finite
    score_kind: Literal['predicted_iou', 'detection_confidence', 'native_quality'] = 'predicted_iou'
    score_semantics: str = 'native predicted mask quality; not calibrated probability'
    category_id: NonnegativeInt | None = None
    prompt_id: ID | None = None
    @model_validator(mode='after')
    def valid(self):
        if self.score_kind=='detection_confidence' and not 0 <= self.score <= 1: raise ValueError('detection confidence outside [0,1]')
        return self

class MaskPrediction(Contract):
    sample_id: ID
    width: PositiveInt
    height: PositiveInt
    instances: list[MaskInstance]
    prompts: list[PromptSpec] = Field(default_factory=list)
    selection_policy: Literal['all_candidates', 'native_quality_max', 'single_native_output'] = 'all_candidates'
    native_output_sha256: SHA256 | None = None
    @model_validator(mode='after')
    def valid(self):
        ids = [x.id for x in self.instances]
        pids = [p.id for p in self.prompts]
        if len(ids) != len(set(ids)) or len(pids) != len(set(pids)): raise ValueError('duplicate instance/prompt ID')
        for p in self.prompts:
            if p.sample_id != self.sample_id: raise ValueError('prompt sample mismatch')
        for x in self.instances:
            if (x.mask.width, x.mask.height) != (self.width, self.height): raise ValueError('mask dimension mismatch')
            if x.prompt_id is not None and x.prompt_id not in pids: raise ValueError('unknown prompt')
        return self

class MaskAnnotation(Contract):
    sample_id: ID
    instance_id: ID
    mask: MaskRLE
    category_id: NonnegativeInt | None = None
    iscrowd: bool = False
    ignore: bool = False

class VisionJob(Contract):
    backend: Literal['hf_grounding_dino', 'sam2', 'sam_hf', 'yolo_world', 'ultralytics_seg', 'torchvision_mask']
    operation: Literal['predict', 'capabilities'] = 'predict'
    model_dir: str
    model_files: dict[str, SHA256]
    trust_local_code: bool = False
    device: str = 'cpu'
    package_versions: dict[str, str] = Field(default_factory=dict)
    images: list[dict[str, Any]] = Field(default_factory=list)
    prompts: list[PromptSpec] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    purpose: Literal['software_fixture', 'research'] = 'research'
    @field_validator('images')
    @classmethod
    def valid_images(cls, images):
        from pydantic import TypeAdapter
        seen=set()
        for image in images:
            if not {'id','path','sha256'} <= set(image):raise ValueError('image needs id/path/sha256')
            TypeAdapter(ID).validate_python(image['id']);TypeAdapter(SHA256).validate_python(image['sha256'])
            if image['id'] in seen:raise ValueError('duplicate image ID')
            seen.add(image['id'])
            if not isinstance(image['path'],str) or not image['path']:raise ValueError('image path required')
            if image.get('split_role','dev') not in {'dev','selection'}:raise ValueError('standalone vision jobs require dev/selection images; protected test needs governed evaluation')
        return images
    @model_validator(mode='after')
    def prompt_universe(self):
        ids={i['id'] for i in self.images}
        if self.operation=='predict' and not ids:raise ValueError('prediction job needs images')
        if any(p.sample_id not in ids for p in self.prompts):raise ValueError('prompt refers to unknown image')
        if len({p.id for p in self.prompts})!=len(self.prompts):raise ValueError('duplicate prompt ID')
        return self
    @field_validator('model_files')
    @classmethod
    def paths(cls,v):
        for p in v: relative_path(p)
        if not v: raise ValueError('explicit local model asset hashes required')
        return v

class MaskEvaluationProtocol(Contract):
    evaluator: Literal['pycocotools'] = 'pycocotools'
    evaluator_version: Literal['2.0.11'] = '2.0.11'
    task: Literal['instance_segmentation'] = 'instance_segmentation'
    bbox_parameters: dict[str, Any] = Field(default_factory=dict)
    prompt_policy: Literal['no_prompts', 'explicit_prompt_conditioned'] = 'no_prompts'
    split_role: Literal['dev', 'selection'] = 'dev'
    @model_validator(mode='after')
    def valid(self):
        from cvsubstrate.contracts.models import EvaluationProtocol
        native=EvaluationProtocol.model_validate(self.bbox_parameters)
        if native.evaluator!='pycocotools':raise ValueError('mask reference evaluator must use pycocotools')
        return self

class CalibrationItem(Contract):
    id: ID
    path: str
    sha256: SHA256
    split_role: Literal['train', 'calibration', 'dev']

class QuantizationSpec(Contract):
    backend: Literal['onnxruntime', 'openvino']
    model_path: str
    model_sha256: SHA256
    calibration: list[CalibrationItem] = Field(min_length=1)
    dataset_sha256: SHA256
    preprocessing_sha256: SHA256
    input_names: list[str] = Field(min_length=1)
    input_shapes: dict[str, list[int]] = Field(default_factory=dict)
    method: Literal['minmax', 'entropy', 'percentile'] = 'minmax'
    per_channel: bool = True
    weight_type: Literal['int8', 'uint8'] = 'int8'
    activation_type: Literal['int8', 'uint8'] = 'uint8'
    nodes_to_exclude: list[str] = Field(default_factory=list)
    trust_model: bool = False
    @model_validator(mode='after')
    def valid(self):
        if len({x.id for x in self.calibration}) != len(self.calibration): raise ValueError('duplicate calibration ID')
        if len(set(self.input_names)) != len(self.input_names): raise ValueError('duplicate input')
        return self

class ClaimSpec(Contract):
    title: str = Field(min_length=1, max_length=500)
    question: str = Field(min_length=1)
    dataset_sha256: SHA256
    protocol_sha256: SHA256
    experiment_sha256: SHA256
    estimand: str = Field(min_length=1)
    reported_metrics: dict[str, Finite] = Field(min_length=1)
    absolute_tolerances: dict[str, Finite] = Field(min_length=1)
    author_id: ID
    implementation_id: ID
    source_reference: str | None = None
    purpose: Literal['software_fixture', 'research'] = 'research'
    @model_validator(mode='after')
    def valid(self):
        if set(self.reported_metrics) != set(self.absolute_tolerances): raise ValueError('every metric needs one predeclared tolerance')
        if any(x < 0 for x in self.absolute_tolerances.values()): raise ValueError('negative tolerance')
        return self

class ReproductionAttempt(Contract):
    attempt_kind: Literal['original', 'reproduction', 'reevaluation'] = 'reproduction'
    claim_id: SHA256
    actor_id: ID
    machine_id: ID
    implementation_id: ID
    dataset_sha256: SHA256
    protocol_sha256: SHA256
    experiment_sha256: SHA256
    estimand: str
    outcome: Literal['completed', 'failed', 'blocked']
    metrics: dict[str, Finite] = Field(default_factory=dict)
    evidence: dict[str, SHA256] = Field(default_factory=dict)
    failure_reason: str | None = None
    purpose: Literal['software_fixture', 'research'] = 'research'
    @model_validator(mode='after')
    def valid(self):
        if self.outcome != 'completed' and not self.failure_reason: raise ValueError('failed/blocked attempt needs reason')
        if self.outcome == 'completed' and not self.metrics: raise ValueError('completed attempt needs observed metrics')
        return self

class IndependenceReview(Contract):
    attempt_id: SHA256
    reviewer_id: ID
    independent_operator_attested: bool
    independent_machine_attested: bool
    independent_implementation_attested: bool = False
    rationale: str = Field(min_length=20)
    evidence_sha256: SHA256

FRONTIER_SCHEMAS = [PromptSpec, GroundedPrediction, MaskRLE, MaskInstance, MaskPrediction,
    MaskAnnotation, VisionJob, MaskEvaluationProtocol, CalibrationItem, QuantizationSpec, ClaimSpec,
    ReproductionAttempt, IndependenceReview]
