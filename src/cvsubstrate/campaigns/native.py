"""Native multistage compilation with explicit budget units and checkpoint edges.

No model trainer is reimplemented. MM2/MM3 iteration loops accept fixed-update
budgets with accumulation=1; epoch trainers remain epoch trainers and cannot claim
source-preserving equality. Every stage checkpoint is resolved from actual output.
"""
from pathlib import Path
from pydantic import Field,model_validator
from typing import Literal,Any
from cvsubstrate.contracts.models import Contract,ID,SHA256
from cvsubstrate.provenance.io import read_json,write_json,digest,file_digest
class NativeStage(Contract):
    id: ID
    backend: Literal['mmdet2','mmdet3','onedl','ultralytics','rfdetr']
    budget_unit: Literal['optimizer_updates','epochs']
    budget: int=Field(gt=0)
    dataset_sha256: SHA256
    source: Literal['real','synthetic','mixed']
    job: dict[str,Any]
    initialized_from: ID|None=None
    initial_checkpoint: str|None=None
    initial_checkpoint_sha256: SHA256|None=None
    checkpoint_output: str
    @model_validator(mode='after')
    def valid(self):
        if self.backend in {'ultralytics','rfdetr'} and self.budget_unit!='epochs':raise ValueError('this native backend declares epoch budgets; fixed updates require an explicit compatible trainer recipe')
        if self.initialized_from and self.initial_checkpoint:raise ValueError('ambiguous initialization')
        if bool(self.initial_checkpoint)!=bool(self.initial_checkpoint_sha256):raise ValueError('initial checkpoint path/hash must be paired')
        from cvsubstrate.contracts.models import relative_path
        relative_path(self.checkpoint_output)
        return self
class NativeCampaign(Contract):
    id: ID
    stages: list[NativeStage]=Field(min_length=1)
    seeds: list[int]=Field(min_length=1)
    equality_requirements: list[Literal['optimizer_updates','epochs','real_exposures','synthetic_exposures','gpu_hours']]=Field(default_factory=list)
    @model_validator(mode='after')
    def valid(self):
        ids=set()
        if any(s<0 for s in self.seeds) or len(set(self.seeds))!=len(self.seeds):raise ValueError('duplicate seed')
        for s in self.stages:
            if s.id in ids or s.initialized_from and s.initialized_from not in ids:raise ValueError('duplicate or forward/cyclic stage reference')
            ids.add(s.id)
        return self

def compile_native_campaign(campaign):
    c=NativeCampaign.model_validate(campaign);rows=[]
    for s in c.stages:
        rows.append({'stage':s.id,'backend':s.backend,'budget_unit':s.budget_unit,'budget':s.budget,'source':s.source,'dataset_sha256':s.dataset_sha256,'initialization':s.initialized_from,'equality':{q:'PLANNED' if q==s.budget_unit else 'NOT_ESTABLISHED' for q in c.equality_requirements}})
    for q in c.equality_requirements:
        if all(r['equality'][q]=='PLANNED' for r in rows) and len({r['budget'] for r in rows})>1:
            for r in rows:r['equality'][q]='PLANNED_DIFFERENT'
    incompatible=[q for q in c.equality_requirements if any(r['equality'][q]!='PLANNED' for r in rows)]
    return {'campaign_sha256':digest(c),'stages':rows,'seeds':c.seeds,'unsupported_equalities':incompatible,'source_exposure_equivalence':False,'executable':not incompatible}

def run_native_campaign(campaign,out,*,worker_pythons=None,timeout=3600,resume=False):
    from cvsubstrate.execution.services import invoke_service
    from cvsubstrate.foundation.lifecycle import process_lock
    from cvsubstrate.provenance.artifact_set import assert_not_inside_sealed,verify_directory,seal_directory
    c=NativeCampaign.model_validate(campaign);plan=compile_native_campaign(c)
    if not plan['executable']:raise ValueError('unsatisfied native-budget equality: '+str(plan['unsupported_equalities']))
    out=Path(out).resolve();assert_not_inside_sealed(out);out.mkdir(parents=True,exist_ok=True)
    workers=worker_pythons or {};results=[]
    with process_lock(out/'.writer.lock'):
        statefile=out/'campaign-state.json'
        if statefile.exists():
            state=read_json(statefile)
            if not resume or state['campaign_sha256']!=plan['campaign_sha256']:raise ValueError('existing campaign needs exact-identity resume')
        else:state={'campaign_sha256':plan['campaign_sha256'],'runs':{}}
        for seed in c.seeds:
            resolved={}
            for stage in c.stages:
                key=f'{stage.id}-seed-{seed}';dest=out/key;previous=state['runs'].get(key)
                if previous and previous['status']=='SUCCEEDED':
                    if verify_directory(dest)['status']!='VERIFIED':raise ValueError('committed native stage evidence changed')
                    if file_digest(Path(previous['checkpoint']))!=previous['checkpoint_sha256']:raise ValueError('committed checkpoint changed')
                    resolved[stage.id]=previous;results.append(previous);continue
                if stage.initialized_from and stage.initialized_from not in resolved:
                    value={'id':key,'status':'BLOCKED','reason':'parent stage failed'};state['runs'][key]=value;results.append(value);write_json(statefile,state);continue
                job=dict(stage.job);job['seed']=seed;job['budget_unit']=stage.budget_unit;job['budget']=stage.budget;job['backend']=stage.backend;job['dataset_sha256']=stage.dataset_sha256;job['source']=stage.source;job['run_id']=key;job['checkpoint_filename']=Path(stage.checkpoint_output).name
                parent=resolved.get(stage.initialized_from)
                if parent:job['initial_checkpoint']=parent['checkpoint'];job['initial_checkpoint_sha256']=parent['checkpoint_sha256']
                elif stage.initial_checkpoint:job['initial_checkpoint']=stage.initial_checkpoint;job['initial_checkpoint_sha256']=stage.initial_checkpoint_sha256
                if dest.exists():
                    # Preserve previous failed attempt instead of overwriting it.
                    i=1
                    while (out/(key+f'-failed-{i}')).exists():i+=1
                    dest.rename(out/(key+f'-failed-{i}'))
                dest.mkdir();write_json(dest/'job.json',job)
                try:
                    native=invoke_service('native_campaign',{'job':job,'output_dir':str(dest/'native')},worker_python=workers.get(stage.backend),timeout=timeout,log=dest/'native.log')
                    ck=(dest/'native'/stage.checkpoint_output).resolve()
                    if not ck.is_relative_to(dest/'native') or not ck.is_file():raise ValueError('declared stage checkpoint output missing')
                    value={'id':key,'stage':stage.id,'seed':seed,'status':'SUCCEEDED','checkpoint':str(ck),'checkpoint_sha256':file_digest(ck),'initialized_from_sha256':job.get('initial_checkpoint_sha256'),'dataset_sha256':stage.dataset_sha256,'native_result':native}
                    write_json(dest/'result.json',value);seal_directory(dest);resolved[stage.id]=value
                except Exception as exc:
                    value={'id':key,'status':'FAILED','code':getattr(exc,'code','NATIVE_STAGE_FAILED'),'message':str(exc)};write_json(dest/'failure.json',value);seal_directory(dest)
                state['runs'][key]=value;results.append(value);write_json(statefile,state)
    return {'campaign_sha256':digest(c),'runs':results,'all_succeeded':all(x['status']=='SUCCEEDED' for x in results),'source_preservation_claimed':False}
SCHEMAS=[NativeStage,NativeCampaign]
