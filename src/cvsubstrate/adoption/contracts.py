"""Finite adoption contracts. Unknown evidence is not an automatic compatibility pass."""
from __future__ import annotations
from typing import Any, Literal
from pydantic import Field, field_validator, model_validator
from cvsubstrate.contracts.models import Contract, ID, SHA256, relative_path

class SourceObservation(Contract):
    path: str
    line: int = Field(ge=1)
    kind: str
    value: str
    confidence: Literal['literal','static_inference','candidate'] = 'literal'

class RepositoryReport(Contract):
    repository_name: str
    root_identity: SHA256
    files: dict[str,str]
    observations: list[SourceObservation]
    frameworks: list[str]
    command_candidates: list[dict[str,Any]]
    unresolved: list[str]
    git: dict[str,Any] = Field(default_factory=dict)
    truncated: bool = False
    executable_code_loaded: Literal[False] = False

class ExternalAsset(Contract):
    id: ID
    kind: Literal['weights','dataset','processor','vocabulary','code','other']
    source: str
    sha256: SHA256
    size_bytes: int | None = Field(default=None,ge=0)
    license_id: str = 'unknown'
    license_url: str | None = None
    redistribution: Literal['allowed','prohibited','unknown'] = 'unknown'
    revision: str | None = None
    filename: str | None = None

class InteropArtifact(Contract):
    id: ID
    kind: Literal['images','features','embeddings','hbb','obb','masks','semantic_labels','prompts','checkpoint','dataset','json']
    path: str
    sha256: SHA256
    shape: list[int] | None = None
    dtype: str | None = None
    coordinate_frame: str | None = None
    sample_ids: list[str] = Field(default_factory=list)
    producer: dict[str,Any] = Field(default_factory=dict)
    semantics: dict[str,Any] = Field(default_factory=dict)
    materialized: Literal[True] = True
    differentiable: Literal[False] = False
    _path=field_validator('path')(relative_path)

    @model_validator(mode='after')
    def meaningful(self):
        if self.kind in {'features','embeddings'} and (self.shape is None or self.dtype is None):
            raise ValueError('tensor artifacts require shape and dtype')
        if self.kind in {'hbb','obb','masks'} and not self.coordinate_frame:
            raise ValueError('geometry artifacts require a coordinate frame')
        if self.shape is not None and any(x < 0 for x in self.shape):
            raise ValueError('negative tensor dimension')
        if len(self.sample_ids)!=len(set(self.sample_ids)):
            raise ValueError('sample identity must be unique')
        return self

class CommandOutput(Contract):
    path: str
    kind: str = 'json'
    required: bool = True
    _path=field_validator('path')(relative_path)

class PaperCommand(Contract):
    argv: list[str] = Field(min_length=1)
    outputs: dict[str,CommandOutput] = Field(default_factory=dict)
    timeout_seconds: float = Field(default=600.0,gt=0,le=604800)
    env: dict[str,str] = Field(default_factory=dict)
    @field_validator('argv')
    @classmethod
    def safe_tokens(cls,value):
        if any('\x00' in x or '\n' in x or '\r' in x for x in value):
            raise ValueError('command tokens must not contain control characters')
        return value

class PaperRunSpec(Contract):
    name: ID
    repo: str
    python: str
    repository_digest: SHA256
    operations: dict[str,PaperCommand]
    inputs: dict[str,str] = Field(default_factory=dict)
    input_digests: dict[str,SHA256] = Field(default_factory=dict)
    purpose: Literal['research','software_fixture'] = 'research'
    trust_code: bool = False
    network: Literal['inherit','disabled'] = 'disabled'
    unresolved: list[str] = Field(default_factory=list)

class PaperRecipe(Contract):
    id: ID
    title: str
    source_urls: list[str]
    repositories: list[dict[str,Any]]
    frameworks: list[str]
    tasks: list[str]
    assets: list[dict[str,Any]] = Field(default_factory=list)
    commands: dict[str,Any] = Field(default_factory=dict)
    integration_boundary: Literal['whole_environment','independent_stages','requires_author_refactor']
    status: Literal['SOURCE_INSPECTED','CANDIDATE','EXECUTED'] = 'CANDIDATE'
    verified_revision: str | None = None
    inspected_date: str
    limitations: list[str]

class BridgeJob(Contract):
    bridge: str
    operation: Literal['export','import','inspect','predict','train','evaluate','fetch','lock']
    payload: dict[str,Any]
    output_dir: str
    worker_python: str | None = None
    trust_code: bool = False
    allow_network: bool = False
    timeout_seconds: float = Field(default=180.0,gt=0)

class PublicationSettings(Contract):
    display_name: str = 'CV Research Substrate'
    distribution_name: str = 'cv-research-substrate'
    import_name: str = 'cvsubstrate'
    cli_name: str = 'cvrs'
    repository_url: str | None = None
    authors: list[dict[str,str]] = Field(default_factory=list)
    license_id: str = 'LicenseRef-Owner-Decision-Pending'
    copyright_holder: str | None = None
    identity_approved: bool = False
    license_approved: bool = False
    security_contact: str | None = None
    private_terms: list[str] = Field(default_factory=list)

class MethodologySpec(Contract):
    dataset_digest: str | None = None
    baseline_dataset_digest: str | None = None
    evaluation: dict[str,Any] = Field(default_factory=dict)
    baseline_evaluation: dict[str,Any] = Field(default_factory=dict)
    arms: list[dict[str,Any]] = Field(default_factory=list)
    prompts: list[dict[str,Any]] = Field(default_factory=list)
    assets: list[dict[str,Any]] = Field(default_factory=list)
    test_accesses: list[dict[str,Any]] = Field(default_factory=list)
    lineage: list[dict[str,Any]] = Field(default_factory=list)
    declared_interventions: list[str] = Field(default_factory=list)

ADOPTION_SCHEMAS=[SourceObservation,RepositoryReport,ExternalAsset,InteropArtifact,CommandOutput,
                 PaperCommand,PaperRunSpec,PaperRecipe,BridgeJob,PublicationSettings,MethodologySpec]


class SemanticLabelMap(Contract):
    task: Literal['semantic_segmentation'] = 'semantic_segmentation'
    sample_id: ID
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    labels: str
    sha256: SHA256
    category_mapping: dict[str,int]
    ignore_index: int = 255
    reduce_zero_label: bool = False
    _path=field_validator('labels')(relative_path)

ADOPTION_SCHEMAS.append(SemanticLabelMap)
