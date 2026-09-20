"""Structured claims, effect observations and explicit independence dimensions."""
from __future__ import annotations
from typing import Literal,Any
from pydantic import Field,model_validator
from cvsubstrate.contracts.models import Contract,ID,SHA256,Finite
from cvsubstrate.provenance.io import digest

class ActorIdentity(Contract):
    id: ID
    display_name: str
    public_keys: list[SHA256]=Field(default_factory=list)
    identities: dict[str,str]=Field(default_factory=dict)
    organization: str|None=None
    verification: Literal['SELF_ASSERTED','EXTERNALLY_ATTESTED']='SELF_ASSERTED'
    attestation_evidence: list[SHA256]=Field(default_factory=list)
    @model_validator(mode='after')
    def valid(self):
        if self.verification=='EXTERNALLY_ATTESTED' and not self.attestation_evidence:raise ValueError('external identity requires evidence')
        return self

class ScientificClaim(Contract):
    title: str
    population: str
    dataset_sha256: SHA256
    split: str
    intervention: dict[str,Any]
    comparator: dict[str,Any]
    metric: str
    units: str='absolute'
    direction: Literal['greater','less','equivalent']
    minimum_effect: Finite=0.0
    equivalence_margin: Finite=0.0
    reproduction_tolerance: Finite=0.0
    protocol_sha256: SHA256
    model_scope: dict[str,Any]=Field(default_factory=dict)
    conditions: dict[str,Any]=Field(default_factory=dict)
    author_id: ID
    purpose: Literal['research','software_fixture']='research'
    @model_validator(mode='after')
    def valid(self):
        if not self.title.strip() or not self.metric.strip() or not self.population.strip():raise ValueError('title/population/metric required')
        if min(self.minimum_effect,self.equivalence_margin,self.reproduction_tolerance)<0:raise ValueError('negative effect tolerance')
        if self.intervention==self.comparator:raise ValueError('intervention and comparator must differ')
        return self
    @property
    def scope_fingerprint(self):
        value=self.model_dump(mode='json');value.pop('title');value.pop('author_id');return digest(value)

class EffectObservation(Contract):
    metric: str
    baseline: Finite
    treatment: Finite
    seed_pairs: list[dict[str,Any]]=Field(default_factory=list)
    interval: list[Finite]|None=None
    uncertainty_method: str|None=None
    @model_validator(mode='after')
    def valid(self):
        if self.interval is not None:
            if len(self.interval)!=2 or self.interval[0]>self.interval[1] or not self.uncertainty_method:raise ValueError('interval needs ordered bounds and an explicit method')
        if self.uncertainty_method and self.interval is None:raise ValueError('uncertainty method without interval')
        return self
    def assess(self,claim:ScientificClaim):
        if self.metric!=claim.metric:raise ValueError('effect metric differs from claim')
        delta=self.treatment-self.baseline;lo,hi=self.interval if self.interval is not None else (delta,delta)
        if claim.direction=='greater':
            result='SUPPORTED' if lo>claim.minimum_effect else 'CONTRADICTED' if hi < -claim.minimum_effect else 'INCONCLUSIVE' if self.interval else 'NOT_SUPPORTED'
        elif claim.direction=='less':
            result='SUPPORTED' if hi < -claim.minimum_effect else 'CONTRADICTED' if lo>claim.minimum_effect else 'INCONCLUSIVE' if self.interval else 'NOT_SUPPORTED'
        else:
            result='SUPPORTED' if -claim.equivalence_margin<=lo<=hi<=claim.equivalence_margin else 'CONTRADICTED' if hi < -claim.equivalence_margin or lo>claim.equivalence_margin else 'INCONCLUSIVE'
        return {'assertion':result,'absolute_delta':delta,'relative_delta':delta/abs(self.baseline) if self.baseline!=0 else None,
            'relative_delta_defined':self.baseline!=0,'interval':self.interval,'strength':'INTERVAL_CONDITIONED' if self.interval else 'POINT_ESTIMATE_ONLY',
            'uncertainty_method':self.uncertainty_method,'automatic_statistical_significance':False}

class EvidenceAttempt(Contract):
    claim_id: SHA256
    role: Literal['original','reproduction','reevaluation']
    actor_id: ID
    machine_id: ID
    environment_sha256: SHA256
    implementation_id: ID
    scope_fingerprint: SHA256
    outcome: Literal['completed','failed','blocked']
    effect: EffectObservation|None=None
    evidence: dict[str,SHA256]=Field(default_factory=dict)
    failure_reason: str|None=None
    purpose: Literal['research','software_fixture']='research'
    @model_validator(mode='after')
    def valid(self):
        if self.outcome=='completed' and self.effect is None:raise ValueError('completed attempt needs effect')
        if self.outcome!='completed' and not self.failure_reason:raise ValueError('failure/blocked attempt needs reason')
        return self

class IndependenceAttestation(Contract):
    attempt_id: SHA256
    reviewer_id: ID
    independent_operator: bool=False
    independent_machine: bool=False
    independent_environment: bool=False
    independent_implementation: bool=False
    independent_organization: bool=False
    evidence: list[SHA256]=Field(min_length=1)
    rationale: str=Field(min_length=20)

class EvidenceEdge(Contract):
    source: SHA256
    target: SHA256
    relation: Literal['derived_from','produced','consumed','evaluated_by','supports','contradicts','reproduces','supersedes','uses','contains','initialized_from']
    evidence: list[SHA256]=Field(default_factory=list)
    rationale: str=''
    @model_validator(mode='after')
    def valid(self):
        if self.source==self.target:raise ValueError('self evidence edge')
        return self

SCHEMAS=[ActorIdentity,ScientificClaim,EffectObservation,EvidenceAttempt,IndependenceAttestation,EvidenceEdge]
