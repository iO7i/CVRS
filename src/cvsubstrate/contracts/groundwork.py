"""Contracts for the 0.4 local engineering layer; no ML imports.

Version strings describe serialized contracts, not empirical certification.
Identity fields are content hashes; local filesystem locations are not identities.
"""
from __future__ import annotations
from typing import Any, Literal
from pydantic import Field, model_validator, field_validator
from cvsubstrate.contracts.models import Contract, ID, SHA256, PositiveInt, NonnegativeInt, Finite, relative_path

class ArtifactRef(Contract):
    sha256: SHA256
    bytes: NonnegativeInt
    media_type: str = 'application/octet-stream'
    name: str | None = None

class ArtifactEnvelope(Contract):
    schema_version: Literal['1.1'] = '1.1'
    schema_name: ID
    payload_version: str = '1.0'
    payload: dict[str, Any]
    source_digest: SHA256 | None = None
    migration_history: list[dict[str, Any]] = Field(default_factory=list)

class PluginDescriptor(Contract):
    id: ID
    kind: Literal['model','dataset','evaluator','exporter','simulator_metadata','backbone','artifact_store','merge']
    protocol_version: Literal['1.0'] = '1.0'
    target: str
    tasks: list[str] = Field(default_factory=list)
    operations: list[str] = Field(default_factory=list)
    formats: list[str] = Field(default_factory=list)
    required_packages: list[str] = Field(default_factory=list)
    trust_code: bool = False
    evidence: dict[str, str] = Field(default_factory=dict)
    implementation_revision: str | None = None
    execution_status: Literal['NOT_RUN','EXECUTED'] = 'NOT_RUN'

class CapabilityRequirement(Contract):
    task: str
    operation: str
    input_format: str
    output_format: str
    dataset_fields: list[str] = Field(default_factory=list)
    precision: str | None = None

class EnvironmentManifest(Contract):
    python: str | None = None
    platform: str | None = None
    packages: list[dict[str, Any]] = Field(default_factory=list)
    imports: list[dict[str, Any]] = Field(default_factory=list)
    hardware: dict[str, Any] = Field(default_factory=dict)
    container_digest: str | None = None
    metadata_status: Literal['MEASURED','DECLARED','MIXED'] = 'DECLARED'
    execution_verified: Literal[False] = False
    unresolved: list[str] = Field(default_factory=list)

class ExecutionEvent(Contract):
    sequence: NonnegativeInt
    at: str
    run_id: str
    node_id: str | None = None
    component: str
    event_type: Literal['RUN_CREATED','WORKER_STARTED','MODEL_LOADED','TRAIN_STARTED','TRAIN_COMPLETED','CHECKPOINT_WRITTEN','INFERENCE_COMPLETED','EVALUATION_COMPLETED','RUN_SUCCEEDED','RUN_FAILED','RUN_CANCELLED','RUN_RESUMED','NODE_STARTED','NODE_SUCCEEDED','NODE_FAILED','NODE_CACHED','NODE_BLOCKED','NODE_INTERRUPTED','NODE_INVALIDATED']
    payload: dict[str, Any] = Field(default_factory=dict)
    previous_digest: SHA256 | None = None

class InputReference(Contract):
    path: str | None = None
    sha256: SHA256 | None = None
    node: ID | None = None
    artifact: str | None = None

    @model_validator(mode='after')
    def exclusive_source(self):
        local = self.path is not None
        upstream = self.node is not None
        if local == upstream:
            raise ValueError('input needs exactly one local path or upstream node')
        if local and (self.sha256 is None or self.artifact is not None):
            raise ValueError('local files need a content hash; artifact is for upstream nodes')
        if upstream and (not self.artifact or self.sha256 is not None):
            raise ValueError('upstream input needs artifact name; its digest is resolved at execution')
        if self.artifact:
            relative_path(self.artifact)
        return self

class ExecutionNode(Contract):
    id: ID
    action: str
    depends_on: list[ID] = Field(default_factory=list)
    inputs: dict[str, InputReference] = Field(default_factory=dict)
    parameters: dict[str, Any] = Field(default_factory=dict)
    cache: bool = False
    retries: NonnegativeInt = 0
    idempotent: bool = False
    @model_validator(mode='after')
    def retry_policy(self):
        if self.retries and not self.idempotent:
            raise ValueError('retries require explicit idempotent declaration')
        if self.id in self.depends_on or len(set(self.depends_on)) != len(self.depends_on):
            raise ValueError('self/duplicate dependency')
        return self

class ExecutionGraph(Contract):
    name: ID
    nodes: list[ExecutionNode] = Field(min_length=1)
    continue_independent_nodes: bool = True
    @model_validator(mode='after')
    def acyclic(self):
        ids = [n.id for n in self.nodes]
        if len(ids) != len(set(ids)): raise ValueError('duplicate node ID')
        dependencies = {n.id: set(n.depends_on) | {v.node for v in n.inputs.values() if v.node} for n in self.nodes}
        if any(d - set(ids) for d in dependencies.values()): raise ValueError('unknown dependency')
        seen = set()
        while len(seen) < len(ids):
            ready = {k for k, v in dependencies.items() if k not in seen and v <= seen}
            if not ready: raise ValueError('cyclic execution graph')
            seen |= ready
        return self

class CheckpointDescriptor(Contract):
    source_framework: str
    source_revision: str | None = None
    architecture: str
    path: str
    sha256: SHA256
    serialization: Literal['torch_weights','safetensors','trusted_pickle'] = 'torch_weights'
    state_dict_key: str | None = None
    license: str = 'unknown'
    trust_legacy_pickle: bool = False

class CheckpointConversionSpec(Contract):
    source: CheckpointDescriptor
    destination_framework: str
    destination_architecture: str
    parameter_mapping: dict[str, str] = Field(default_factory=dict)
    destination_shapes: dict[str, list[NonnegativeInt]] = Field(default_factory=dict)
    allowed_missing: list[str] = Field(default_factory=list)
    allowed_drop: list[str] = Field(default_factory=list)
    output_format: Literal['torch_weights','safetensors'] = 'torch_weights'
    @model_validator(mode='after')
    def injective(self):
        if len(set(self.parameter_mapping.values())) != len(self.parameter_mapping):
            raise ValueError('parameter mappings must be injective')
        return self

class ObjectSizePolicy(Contract):
    statistic: Literal['width_px','height_px','area_px2','sqrt_area_px','max_side_px','area_m2'] = 'sqrt_area_px'
    edges: list[Finite] = Field(default_factory=lambda:[0.0,16.0,32.0,64.0])
    @model_validator(mode='after')
    def increasing(self):
        if not self.edges or self.edges[0] != 0 or self.edges != sorted(set(self.edges)):
            raise ValueError('size edges must start at zero and strictly increase')
        return self

class SliceExpression(Contract):
    name: ID
    expression: dict[str, Any]
    level: Literal['image','object'] = 'image'
    missing_policy: Literal['exclude','error'] = 'exclude'
    metadata_origin: str

class MergePolicy(Contract):
    kind: Literal['nms','soft_nms','weighted_box_fusion','oriented_nms','keep_all'] = 'nms'
    iou_threshold: float = Field(default=0.5, ge=0, le=1)
    score_threshold: float = Field(default=0.0, ge=0, le=1)
    sigma: float = Field(default=0.5, gt=0)
    score_fusion: Literal['weighted_mean','max'] = 'weighted_mean'
    max_detections: PositiveInt = 1000

class LargeImagePlan(Contract):
    source_id: ID
    source_width: PositiveInt
    source_height: PositiveInt
    scales: list[Finite] = Field(default_factory=lambda:[1.0])
    tile_width: PositiveInt = 1024
    tile_height: PositiveInt = 1024
    overlap_x: NonnegativeInt = 128
    overlap_y: NonnegativeInt = 128
    pad_edges: bool = True
    batch_size: PositiveInt = 1
    memory_budget_bytes: PositiveInt | None = None
    channels: PositiveInt = 3
    bytes_per_value: PositiveInt = 4
    merge: MergePolicy = Field(default_factory=MergePolicy)
    @model_validator(mode='after')
    def policy(self):
        if self.overlap_x >= self.tile_width or self.overlap_y >= self.tile_height: raise ValueError('invalid overlap')
        if not self.scales or any(x<=0 for x in self.scales) or len(set(self.scales))!=len(self.scales): raise ValueError('positive unique scales required')
        return self

class GeoDatasetManifest(Contract):
    name: ID
    version: str
    raster_assets: list[dict[str, Any]] = Field(min_length=1)
    dataset_digest: SHA256 | None = None
    task: str = 'hbb_detection'
    license: str = 'unknown'
    notes: str | None = None

class StageSpec(Contract):
    id: ID
    source: Literal['real','synthetic','mixed']
    updates: PositiveInt
    real_per_update: NonnegativeInt = 0
    synthetic_per_update: NonnegativeInt = 0
    real_weight: float = Field(default=1.0,gt=0)
    synthetic_weight: float = Field(default=1.0,gt=0)
    initialize_from_previous: bool = True
    transition: Literal['weights_only_reset_optimizer','resume_full_state'] = 'weights_only_reset_optimizer'
    @model_validator(mode='after')
    def counts(self):
        r,s=self.real_per_update,self.synthetic_per_update
        if r+s==0: raise ValueError('empty update')
        if self.source=='real' and (s or not r): raise ValueError('real source counts mismatch')
        if self.source=='synthetic' and (r or not s): raise ValueError('synthetic source counts mismatch')
        if self.source=='mixed' and (not r or not s): raise ValueError('mixed stage needs both sources')
        return self

class ArmSpec(Contract):
    id: ID
    stages: list[StageSpec] = Field(min_length=1)
    @model_validator(mode='after')
    def ids(self):
        if len({s.id for s in self.stages})!=len(self.stages): raise ValueError('duplicate stage IDs')
        return self

class BudgetConstraint(Contract):
    metric: Literal['real_exposures','synthetic_exposures','total_exposures','optimizer_steps','gpu_hours','wall_seconds']
    arms: list[ID] = Field(min_length=2)
    tolerance: float = Field(default=0.0,ge=0)
    mode: Literal['equal','at_most'] = 'equal'
    limit: float | None = None
    @model_validator(mode='after')
    def limit_required(self):
        if self.mode=='at_most' and (self.limit is None or self.limit<0): raise ValueError('at_most needs nonnegative limit')
        return self

class ResearchCampaign(Contract):
    name: ID
    arms: list[ArmSpec] = Field(min_length=1)
    seeds: list[NonnegativeInt] = Field(min_length=1)
    backends: list[dict[str, Any]] = Field(min_length=1)
    constraints: list[BudgetConstraint] = Field(default_factory=list)
    phase: Literal['exploratory','confirmatory'] = 'exploratory'
    previous_seeds: list[NonnegativeInt] = Field(default_factory=list)
    selection_digest: SHA256 | None = None
    @model_validator(mode='after')
    def campaign(self):
        names=[a.id for a in self.arms]
        if len(names)!=len(set(names)) or len(self.seeds)!=len(set(self.seeds)): raise ValueError('duplicate arms/seeds')
        for c in self.constraints:
            if set(c.arms)-set(names): raise ValueError('constraint references unknown arms')
        if self.phase=='confirmatory' and (len(self.seeds)<3 or set(self.seeds)&set(self.previous_seeds) or not self.selection_digest): raise ValueError('confirmation needs >=3 fresh seeds and selection identity')
        return self

class BenchmarkSpec(Contract):
    name: ID
    version: str
    datasets: dict[str, SHA256]
    allowed_training_datasets: list[SHA256] = Field(default_factory=list)
    split_roles: dict[str, Literal['train','dev','selection','locked_test']]
    taxonomy_digest: SHA256
    task: Literal['hbb_detection','obb_detection'] = 'hbb_detection'
    evaluation: dict[str, Any]
    tiling: dict[str, Any] = Field(default_factory=dict)
    seed_policy: dict[str, Any] = Field(default_factory=dict)
    required_artifacts: list[str] = Field(default_factory=lambda:['predictions.jsonl','metrics.json','experiment.json'])
    locked_test_policy: Literal['explicit_counted_approval'] = 'explicit_counted_approval'
    @model_validator(mode='after')
    def paths(self):
        for p in self.required_artifacts: relative_path(p)
        return self

class BackboneDescriptor(Contract):
    provider: Literal['timm','huggingface','dinov2_local','dinov3_local']
    model: str
    weights: str | None = None
    weights_sha256: SHA256 | None = None
    revision: str | None = None
    out_indices: list[NonnegativeInt] = Field(default_factory=lambda:[1,2,3,4])
    trust_local_repository: bool = False
    local_repository: str | None = None
    repository_sha256: SHA256 | None = None
    local_model_directory_sha256: SHA256 | None = None
    license: str = 'unknown'
    allow_downloads: Literal[False] = False
    input_contract: dict[str,Any] = Field(default_factory=lambda:{'color':'RGB','range':'caller-normalized','spatial':'NCHW'})

class DeploymentSpec(Contract):
    name: ID
    source: CheckpointDescriptor | None = None
    backend: Literal['torch_export','onnx','onnxruntime','tensorrt','openvino']
    model_path: str
    model_sha256: SHA256
    input_arrays: dict[str,str] = Field(default_factory=dict)
    precision: Literal['fp32','fp16','bf16','int8'] = 'fp32'
    options: dict[str,Any] = Field(default_factory=dict)
    device: str = 'cpu'
    trust_executable_artifact: bool = False

GROUNDWORK_SCHEMAS = [ArtifactRef, ArtifactEnvelope, PluginDescriptor, CapabilityRequirement, EnvironmentManifest,
    ExecutionEvent, InputReference, ExecutionNode, ExecutionGraph, CheckpointDescriptor, CheckpointConversionSpec,
    ObjectSizePolicy, SliceExpression, MergePolicy, LargeImagePlan, GeoDatasetManifest, StageSpec, ArmSpec,
    BudgetConstraint, ResearchCampaign, BenchmarkSpec, BackboneDescriptor, DeploymentSpec]
