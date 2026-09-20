"""Capture an existing verified CVRS run as an original research record.

Sealed bytes are verified. The receipt documents the recorded worker, not a
cryptographic guarantee that a publisher actually performed the computation.
"""
from pathlib import Path
from cvsubstrate.provenance.io import read_json,write_json,digest,file_digest,experiment_identity
from cvsubstrate.provenance.bundle import verify_bundle
from cvsubstrate.contracts.models import ExperimentSpec,DatasetManifest
from cvsubstrate.research.registry import ResearchRegistry

def capture_run(registry,run,dataset,*,title,question,estimand,author_id,machine_id,implementation_id,metric_names=None,absolute_tolerance=1e-6,existing_claim_id=None,attempt_kind=None):
    run=Path(run);dataset=Path(dataset)
    verification=verify_bundle(run)
    if verification['status']!='VERIFIED' or verification.get('run_state')!='SUCCEEDED':raise ValueError('source run must verify and be SUCCEEDED')
    spec=ExperimentSpec.model_validate(read_json(run/'experiment.json'))
    m=DatasetManifest.model_validate(read_json(dataset))
    if digest(m)!=spec.dataset_sha256:raise ValueError('dataset does not match original run')
    protocol=spec.evaluation.model_dump(mode='json')
    exp={'cvrs_experiment_identity':experiment_identity(spec)}
    from cvsubstrate.research.metrics import scalar_observations
    result=read_json(run/'metrics.json');metrics=scalar_observations(result)
    if metric_names:
        if not set(metric_names)<=set(metrics):raise ValueError('requested metric unavailable or undefined')
        metrics={k:metrics[k] for k in metric_names}
    if not metrics:raise ValueError('run contains no finite selected scalar metrics')
    if absolute_tolerance<0:raise ValueError('negative tolerance')
    purpose='software_fixture' if m.purpose=='software_fixture' else 'research'
    claim={'title':title,'question':question,'dataset_sha256':digest(m),'protocol_sha256':digest(protocol),'experiment_sha256':digest(exp),'estimand':estimand,
        'reported_metrics':metrics,'absolute_tolerances':{k:absolute_tolerance for k in metrics},'author_id':author_id,'implementation_id':implementation_id,'purpose':purpose}
    with ResearchRegistry(Path(registry)) as reg:
        ev={'dataset':reg.add_json(m.model_dump(mode='json')),'protocol':reg.add_json(protocol),'experiment':reg.add_json(exp),
            'predictions':reg.add_file(run/'predictions.jsonl',media_type='application/x-ndjson'),'source_integrity_manifest':reg.add_file(run/'artifacts.json',media_type='application/json'),
            'native_experiment':reg.add_file(run/'experiment.json',media_type='application/json')}
        envpath=run/'environment.json'
        ev['environment']=reg.add_file(envpath,media_type='application/json') if envpath.exists() else reg.add_json({'status':'not separately recorded','source_manifest':ev['source_integrity_manifest']})
        # Existing in-repo workers emit execution results. Import the sealed source
        # alongside a normalized receipt; never fabricate prediction arrays.
        workerresult=run/'worker_result.json'
        if not workerresult.is_file():workerresult=run/'worker/result.json'
        if not workerresult.is_file():workerresult=run/'worker/execution.json'
        if not workerresult.is_file():raise ValueError('no recorded native worker result; use metadata-only claim')
        ev['native_worker_result']=reg.add_file(workerresult,media_type='application/json')
        ev['execution']=reg.add_json({'status':'SUCCEEDED','operation':'train_predict' if spec.training else 'predict','execution_kind':'native',
            'purpose':purpose,'dataset_sha256':digest(m),'experiment_sha256':digest(exp),'predictions_sha256':ev['predictions'],'implementation_id':implementation_id,
            'worker_result_sha256':ev['native_worker_result'],'worker_adapter':spec.adapter.name,'source_run_manifest_sha256':ev['source_integrity_manifest'],
            'limits':'Recorded sealed worker execution; not independent publisher authentication'})
        ev['evaluation']=reg.add_json({'status':'EVALUATED','dataset_sha256':digest(m),'protocol_sha256':digest(protocol),'predictions_sha256':ev['predictions'],
            'metrics':metrics,'evaluator_identity':{'evaluator':spec.evaluation.evaluator,'version':spec.evaluation.evaluator_version}})
        cid=existing_claim_id or reg.register_claim(claim)
        if existing_claim_id:reg.get(cid,'claim')
        kind=attempt_kind or ('reproduction' if existing_claim_id else 'original')
        aid=reg.register_attempt({'attempt_kind':kind,'claim_id':cid,'actor_id':author_id,'machine_id':machine_id,'implementation_id':implementation_id,
            'dataset_sha256':digest(m),'protocol_sha256':digest(protocol),'experiment_sha256':digest(exp),'estimand':estimand,'outcome':'completed','metrics':metrics,'evidence':ev,'purpose':purpose})
        return {'status':'RUN_CAPTURED','claim_id':cid,'attempt_id':aid,'assessment':reg.assess_attempt(aid),'independent_reproduction_claimed':False}
