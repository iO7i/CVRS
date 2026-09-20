"""Execute explicit prompt trajectories using existing isolated native workers."""
from pathlib import Path
from cvsubstrate.vision.prompts import PromptSet,negotiate_prompts,legacy_prompts,validate_trajectory,native_prompt_groups
from cvsubstrate.contracts.frontier import VisionJob
from cvsubstrate.provenance.io import read_json,write_json,file_digest,digest
from cvsubstrate.provenance.artifact_set import seal_directory,assert_not_inside_sealed

def execute_trajectory(job,sets,out,*,worker_python=None,timeout=600):
    from cvsubstrate.vision.service import vision_job
    base=VisionJob.model_validate(job);sets=[PromptSet.model_validate(s) for s in sets]
    negotiation=negotiate_prompts(base.backend,sets)
    if not negotiation['satisfiable']:raise ValueError('unsupported native prompt kinds: '+str(negotiation['unsupported']))
    if len(base.images)!=1 or any(s.sample_id!=base.images[0]['id'] for s in sets):raise ValueError('one image per prompt trajectory')
    out=Path(out);assert_not_inside_sealed(out)
    if out.exists():raise ValueError('new trajectory output required')
    out.mkdir(parents=True);effective=[];records=[]
    try:
        for index,s in enumerate(sets):
            if index:
                if s.previous_set_sha256!=sets[index-1].identity or s.previous_prediction_sha256!=records[-1]['prediction_sha256']:raise ValueError('trajectory references do not match actually executed predecessor')
            elif s.interaction!='initial':raise ValueError('first prompt set must be initial')
            effective=effective+s.prompts if s.interaction=='append' else list(s.prompts)
            if len({p.id for p in effective})!=len(effective):raise ValueError('reused effective prompt ID')
            lowered=legacy_prompts(PromptSet(id=s.id,sample_id=s.sample_id,width=s.width,height=s.height,prompts=effective),out/'prompt-assets')
            native=base.model_copy(deep=True);native.prompts=lowered;native.config['prompt_groups']=native_prompt_groups(PromptSet(id=s.id,sample_id=s.sample_id,width=s.width,height=s.height,prompts=effective))
            path=out/f'step-{index:03d}'
            result=vision_job(native.model_dump(mode='json'),path,worker_python=worker_python,timeout=timeout)
            records.append({'prompt_set':s.model_dump(mode='json'),'prediction_sha256':file_digest(path/'worker'/'predictions.jsonl'),'native_result':result})
        receipt=validate_trajectory(records);write_json(out/'trajectory.json',{'records':records,'validation':receipt,'model_assets_sha256':digest(base.model_files),'state_reuse':'explicit prior-output identities; native image session reconstructed per step'})
        seal_directory(out);return receipt
    except Exception as exc:
        write_json(out/'failure.json',{'code':getattr(exc,'code','TRAJECTORY_FAILED'),'message':str(exc),'completed_steps':records});seal_directory(out);raise

def continue_prompt_step(job,previous_step,new_set,out,**kwargs):
    """Bind a user correction to observed previous hashes, never an invented output."""
    from cvsubstrate.provenance.artifact_set import verify_directory
    if verify_directory(Path(previous_step))['status']!='VERIFIED':raise ValueError('previous trajectory integrity failed')
    previous=read_json(Path(previous_step)/'trajectory.json');records=previous['records']
    if not records:raise ValueError('empty prior trajectory')
    s=PromptSet.model_validate(new_set)
    last=records[-1]
    if s.previous_prediction_sha256!=last['prediction_sha256'] or s.previous_set_sha256!=digest(last['prompt_set']):raise ValueError('wrong predecessor')
    effective=[]
    for r in records:
        p=PromptSet.model_validate(r['prompt_set']);effective=effective+p.prompts if p.interaction=='append' else p.prompts
    effective=effective+s.prompts if s.interaction=='append' else s.prompts
    native=VisionJob.model_validate(job);out=Path(out)
    if out.exists():raise ValueError('fresh continuation output required')
    out.mkdir(parents=True)
    effective_set=PromptSet(id=s.id,sample_id=s.sample_id,width=s.width,height=s.height,prompts=effective)
    native.prompts=legacy_prompts(effective_set,out/'assets')
    if len(native.images)!=1 or native.images[0]['id']!=s.sample_id:raise ValueError('continuation image mismatch')
    if not negotiate_prompts(native.backend,[effective_set])['satisfiable']:raise ValueError('unsupported continuation prompts')
    if previous.get('model_assets_sha256') and previous['model_assets_sha256']!=digest(native.model_files):raise ValueError('continuation model assets changed')
    native.config['prompt_groups']=native_prompt_groups(effective_set)
    from cvsubstrate.vision.service import vision_job
    result=vision_job(native.model_dump(mode='json'),out/'native',**kwargs)
    receipt={'prompt_set':s.model_dump(mode='json'),'prediction_sha256':file_digest(out/'native'/'worker'/'predictions.jsonl'),'native_result':result}
    merged=[*records,receipt];write_json(out/'trajectory.json',{'records':merged,'validation':validate_trajectory(merged),'parent_trajectory_sha256':file_digest(Path(previous_step)/'trajectory.json'),'model_assets_sha256':digest(native.model_files)});seal_directory(out);return receipt
