"""Capture an actual paired-run effect as evidence, without claiming independence."""
from pathlib import Path
from cvsubstrate.provenance.io import read_json,file_digest,digest
from cvsubstrate.provenance.bundle import verify_bundle
from cvsubstrate.research.claims import ScientificClaim,EffectObservation,EvidenceAttempt

def _metric(value,key):
    for part in key.replace('/','.').split('.'):
        if isinstance(value,list):
            if not part.isdecimal() or int(part)>=len(value):raise ValueError('metric index missing: '+key)
            value=value[int(part)]
        elif isinstance(value,dict) and part in value:value=value[part]
        else:raise ValueError('metric path missing: '+key)
    if isinstance(value,bool) or not isinstance(value,(int,float)):raise ValueError('selected metric is not numeric')
    return float(value)

def capture_comparison(registry,claim_id,baseline_run,treatment_run,*,metric_path,actor_id,machine_id,environment_sha256,implementation_id,role='original'):
    claim=ScientificClaim.model_validate(registry.get(claim_id,'claim')['payload']);runs=[]
    for path,declared_role in [(baseline_run,claim.comparator),(treatment_run,claim.intervention)]:
        p=Path(path);verified=verify_bundle(p)
        if verified.get('status')!='VERIFIED' or verified.get('run_state')!='SUCCEEDED':raise ValueError('only verified successful runs can be captured')
        e=read_json(p/'experiment.json');m=read_json(p/'dataset_manifest.json');metrics=read_json(p/'metrics.json')
        if digest(m)!=claim.dataset_sha256 or digest(e['evaluation'])!=claim.protocol_sha256:raise ValueError('claim dataset/evaluation protocol differs from observed run')
        if e['eval_split']!=claim.split:raise ValueError('observed evaluation split differs from claim')
        if 'arm' in declared_role and (e.get('training') or {}).get('arm')!=declared_role['arm']:raise ValueError('captured training arm differs from claimed intervention/comparator')
        if 'adapter' in declared_role and e['adapter']['name']!=declared_role['adapter']:raise ValueError('captured backend differs from claim')
        if 'metric_path' in claim.conditions and claim.conditions['metric_path']!=metric_path:raise ValueError('selected metric path differs from claim conditions')
        purpose='software_fixture' if m.get('purpose')=='software_fixture' else 'research'
        if purpose!=claim.purpose:raise ValueError('fixture/research purpose mismatch')
        runs.append({'run_id':read_json(p/'run.json').get('run_id') if (p/'run.json').exists() else verified.get('run_id',file_digest(p/'artifacts.json')),'manifest_sha256':file_digest(p/'artifacts.json'),'value':_metric(metrics,metric_path),'evidence':registry.add_file(p/'artifacts.json'),'experiment_sha256':digest(e),'observed_environment_sha256':file_digest(p/'environment.json') if (p/'environment.json').exists() else None,'metric_path':metric_path,'declared_role':declared_role})
    if runs[0]['manifest_sha256']==runs[1]['manifest_sha256']:raise ValueError('comparison must use different execution artifacts')
    effect=EffectObservation(metric=claim.metric,baseline=runs[0]['value'],treatment=runs[1]['value'])
    rid=digest([x['manifest_sha256'] for x in runs])
    execution={'status':'SUCCEEDED','run_id':rid,'scope_fingerprint':claim.scope_fingerprint,'runs':runs,'environment_sha256':environment_sha256,'implementation_id':implementation_id}
    evaluation={'run_id':rid,'metric':claim.metric,'effect_digest':digest(effect),'dataset_sha256':claim.dataset_sha256,'protocol_sha256':claim.protocol_sha256}
    attempt=EvidenceAttempt(claim_id=claim_id,role=role,actor_id=actor_id,machine_id=machine_id,environment_sha256=environment_sha256,implementation_id=implementation_id,scope_fingerprint=claim.scope_fingerprint,outcome='completed',effect=effect,evidence={'execution':registry.add_json(execution),'evaluation':registry.add_json(evaluation)},purpose=claim.purpose)
    attempt_id=registry.add('attempt',attempt.model_dump(mode='json'))
    lineage=[]
    for source in [baseline_run,treatment_run]:
        graph=capture_run_lineage(registry,source);lineage.append(graph)
        registry.add_edge({'source':attempt_id,'target':graph['run'],'relation':'uses'})
        registry.add_edge({'source':attempt_id,'target':graph['evaluation'],'relation':'evaluated_by'})
    registry.add_edge({'source':attempt_id,'target':claim_id,'relation':'reproduces' if role=='reproduction' else 'uses'})
    return {'attempt_id':attempt_id,'effect':effect.assess(claim),'status':registry.status(claim_id),'lineage':lineage}


def capture_run_lineage(registry,run_path):
    """Preserve reusable outputs and explicit external checkpoint descriptors.

    Images and checkpoint bytes are not copied by default. A descriptor records
    their declared content identity and makes their external status explicit.
    """
    p=Path(run_path);verified=verify_bundle(p)
    if verified.get('status')!='VERIFIED' or verified.get('run_state')!='SUCCEEDED':raise ValueError('run lineage requires verified successful evidence')
    manifest=read_json(p/'artifacts.json');run_identity=file_digest(p/'artifacts.json')
    def artifact(path,role):
        sha=registry.add_file(path)
        return registry.add('artifact',{'sha256':sha,'role':role,'producer_run_manifest':run_identity,'disposition':'EMBEDDED'})
    data=artifact(p/'dataset_manifest.json','dataset_manifest');experiment=artifact(p/'experiment.json','experiment')
    run_id=registry.add('run',{'manifest_sha256':registry.add_file(p/'artifacts.json'),'execution_identity':run_identity,'status':'SUCCEEDED'})
    registry.add_edge({'source':run_id,'target':data,'relation':'uses'})
    registry.add_edge({'source':run_id,'target':experiment,'relation':'uses'})
    records={'run':run_id,'dataset':data,'experiment':experiment}
    if (p/'environment.json').is_file():
        records['environment']=artifact(p/'environment.json','environment');registry.add_edge({'source':run_id,'target':records['environment'],'relation':'uses'})
    # Checkpoint identity comes from the verified artifact manifest, not an assumed filename/hash.
    entries=manifest.get('files',manifest.get('artifacts',[]))
    if isinstance(entries,dict):entries=[dict(v,path=k) for k,v in entries.items()]
    checkpoints=[]
    for item in entries:
        name=item.get('path','')
        if Path(name).suffix.lower() in {'.pt','.pth','.safetensors'}:
            descriptor={'path_in_original_run':name,'sha256':item['sha256'],'bytes':item.get('bytes'),'disposition':'EXTERNAL_REQUIRED','redistribution':'NOT_INFERRED','producer_run_manifest':run_identity}
            rid=registry.add('artifact',{'sha256':registry.add_json(descriptor),'role':'external_checkpoint_descriptor','disposition':'EMBEDDED_DESCRIPTOR_ONLY'})
            registry.add_edge({'source':rid,'target':run_id,'relation':'derived_from'});checkpoints.append(rid)
    records['checkpoints']=checkpoints
    prediction=p/'predictions.jsonl'
    if prediction.is_file():
        records['predictions']=artifact(prediction,'predictions');registry.add_edge({'source':records['predictions'],'target':run_id,'relation':'derived_from'})
        for ck in checkpoints:registry.add_edge({'source':records['predictions'],'target':ck,'relation':'uses'})
    records['evaluation']=artifact(p/'metrics.json','evaluation')
    registry.add_edge({'source':records['evaluation'],'target':records.get('predictions',run_id),'relation':'derived_from'})
    return records
