"""Prompt sets, source provenance, trajectories and explicit backend negotiation."""
from __future__ import annotations
from pathlib import Path
from typing import Literal,Any
from pydantic import Field,model_validator
from cvsubstrate.contracts.models import Contract,ID,SHA256,Finite,PositiveInt
from cvsubstrate.contracts.frontier import MaskRLE,PromptSpec
from cvsubstrate.provenance.io import digest,file_digest,write_json

class ReferenceAsset(Contract):
    path: str
    sha256: SHA256
    width: PositiveInt|None=None
    height: PositiveInt|None=None
    region: list[Finite]|None=None
    @model_validator(mode='after')
    def valid(self):
        if not self.path:raise ValueError('reference path required')
        if (self.width is None)!=(self.height is None):raise ValueError('reference dimensions must be paired')
        if self.region is not None:
            b=self.region
            if len(b)!=4 or not (0<=b[0]<b[2] and 0<=b[1]<b[3]):raise ValueError('invalid reference region')
            if self.width and (b[2]>self.width or b[3]>self.height):raise ValueError('reference region outside declared image')
        return self

class PromptAtom(Contract):
    id: ID
    kind: Literal['text','points','box','mask','reference_image','reference_region','concept']
    source: Literal['ORACLE','NON_ORACLE','EXTERNAL','GENERATED']
    source_sha256: SHA256|None=None
    target_id: ID|None=None
    text: str|None=None
    points: list[list[Finite]]=Field(default_factory=list)
    labels: list[Literal[0,1]]=Field(default_factory=list)
    box: list[Finite]|None=None
    mask: MaskRLE|None=None
    reference: ReferenceAsset|None=None
    concept_id: ID|None=None
    @model_validator(mode='after')
    def valid(self):
        if self.kind=='text' and not (self.text and self.text.strip()):raise ValueError('text is required')
        if self.kind=='points' and (not self.points or len(self.points)!=len(self.labels)):raise ValueError('aligned points/labels required')
        if any(len(p)!=2 or min(p)<0 for p in self.points):raise ValueError('invalid point')
        if self.kind=='box' and (self.box is None or len(self.box)!=4 or min(self.box[:2])<0 or self.box[2]<=self.box[0] or self.box[3]<=self.box[1]):raise ValueError('invalid prompt box')
        if self.kind=='mask' and self.mask is None:raise ValueError('mask prompt requires canonical mask')
        if self.kind.startswith('reference') and self.reference is None:raise ValueError('reference asset required')
        if self.kind=='reference_region' and (self.reference.region is None or len(self.reference.region)!=4):raise ValueError('reference region required')
        if self.kind=='concept' and self.concept_id is None:raise ValueError('concept ID required')
        fields={'text':'text','points':'points','box':'box','mask':'mask','reference_image':'reference','reference_region':'reference','concept':'concept_id'}
        allowed={fields[self.kind]}
        for field in {'text','points','box','mask','reference','concept_id'}-allowed:
            if getattr(self,field) not in (None,[]):raise ValueError('irrelevant prompt field '+field)
        if self.kind!='points' and self.labels:raise ValueError('labels require points')
        return self

class PromptSet(Contract):
    id: ID
    sample_id: ID
    width: PositiveInt
    height: PositiveInt
    prompts: list[PromptAtom]=Field(min_length=1)
    previous_set_sha256: SHA256|None=None
    previous_prediction_sha256: SHA256|None=None
    interaction: Literal['initial','append','replace']='initial'
    @model_validator(mode='after')
    def valid(self):
        if len({p.id for p in self.prompts})!=len(self.prompts):raise ValueError('duplicate prompt ID')
        if self.interaction!='initial' and not (self.previous_set_sha256 and self.previous_prediction_sha256):raise ValueError('iterative prompt needs both prior identities')
        if self.interaction=='initial' and (self.previous_set_sha256 or self.previous_prediction_sha256):raise ValueError('initial prompt cannot have prior state')
        for p in self.prompts:
            if any(x>=self.width or y>=self.height for x,y in p.points):raise ValueError('point outside image')
            if p.box and (p.box[2]>self.width or p.box[3]>self.height):raise ValueError('box outside image')
            if p.mask and (p.mask.width,p.mask.height)!=(self.width,self.height):raise ValueError('mask coordinate frame mismatch')
        return self
    @property
    def identity(self):return digest(self)

PROMPT_CAPABILITIES={
 'hf_grounding_dino':{'text'},'yolo_world':{'text'},
 'sam_hf':{'points','box','mask'},'sam2':{'points','box','mask'},
 'ultralytics_seg':set(),'torchvision_mask':set(),
}

def register_prompt_backend(backend,kinds):
    allowed={'text','points','box','mask','reference_image','reference_region','concept'}
    if not isinstance(backend,str) or not backend or backend in PROMPT_CAPABILITIES:raise ValueError('unique backend name required')
    kinds=set(kinds)
    if kinds-allowed:raise ValueError('unknown prompt modality')
    PROMPT_CAPABILITIES[backend]=kinds

def native_prompt_groups(prompt_set):
    groups={}
    for p in prompt_set.prompts:
        groups.setdefault(p.target_id or p.id,[]).append(p.id)
    return [{'target_id':k,'prompt_ids':v} for k,v in groups.items()]

def negotiate_prompts(backend,sets):
    if backend not in PROMPT_CAPABILITIES:raise ValueError('unknown backend; register an explicit prompt capability set')
    unsupported=sorted({p.kind for s in sets for p in s.prompts}-PROMPT_CAPABILITIES[backend])
    return {'backend':backend,'supported':sorted(PROMPT_CAPABILITIES[backend]),'unsupported':unsupported,'satisfiable':not unsupported,
            'oracle_conditioned':any(p.source=='ORACLE' for s in sets for p in s.prompts),
            'prompt_set_digest':digest(sets)}

def legacy_prompts(prompt_set:PromptSet,out:Path):
    """Loss-audited lowering to native point/box/text/mask requests."""
    rows=[];mapping={'ORACLE':'ground_truth_oracle','NON_ORACLE':'fixed_protocol','EXTERNAL':'human','GENERATED':'upstream_model'}
    for p in prompt_set.prompts:
        if p.kind.startswith('reference') or p.kind=='concept':raise ValueError('backend-specific exemplar/concept recipe required; not silently rewritten to text')
        kwargs={'id':p.id,'sample_id':prompt_set.sample_id,'kind':p.kind,'source':mapping[p.source],'source_artifact_sha256':p.source_sha256}
        if p.kind=='text':kwargs['text']=p.text
        elif p.kind=='points':kwargs.update(points=p.points,point_labels=p.labels)
        elif p.kind=='box':kwargs['box']=p.box
        else:
            f=Path(out)/(digest(p.mask)+'.mask.json');f.parent.mkdir(parents=True,exist_ok=True)
            if f.exists() and file_digest(f)!=__import__('hashlib').sha256(__import__('cvsubstrate.provenance.io',fromlist=['canonical_bytes']).canonical_bytes(p.mask)+b'\n').hexdigest():raise ValueError('mask artifact collision')
            write_json(f,p.mask);kwargs['mask_reference']=str(f.resolve());kwargs['source_artifact_sha256']=file_digest(f)
        rows.append(PromptSpec(**kwargs))
    return rows

def validate_trajectory(steps:list[dict]):
    previous=None;previous_output=None;effective=[];receipts=[]
    for step in steps:
        p=PromptSet.model_validate(step['prompt_set']);output=step['prediction_sha256']
        if not isinstance(output,str) or len(output)!=64 or any(x not in '0123456789abcdef' for x in output):raise ValueError('prediction SHA required')
        if previous is not None:
            if p.previous_set_sha256!=previous.identity or p.previous_prediction_sha256!=previous_output:raise ValueError('trajectory dependency mismatch')
            if (p.sample_id,p.width,p.height)!=(previous.sample_id,previous.width,previous.height):raise ValueError('trajectory image changed')
            if p.interaction=='initial':raise ValueError('subsequent prompts must append/replace')
        elif p.interaction!='initial':raise ValueError('first trajectory step must be initial')
        effective=(effective+p.prompts) if p.interaction=='append' else list(p.prompts)
        if len({x.id for x in effective})!=len(effective):raise ValueError('appended prompt reuses ID')
        receipts.append({'prompt_set_sha256':p.identity,'prediction_sha256':output,'effective_prompt_ids':[x.id for x in effective]})
        previous=p;previous_output=output
    return {'trajectory_digest':digest(receipts),'steps':receipts,'independent_execution':False}
SCHEMAS=[ReferenceAsset,PromptAtom,PromptSet]
