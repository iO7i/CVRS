"""Sequential CPU-capable execution DAG; no background scheduler or cloud calls."""
from __future__ import annotations
from pathlib import Path
import time
from cvsubstrate.contracts.models import ExperimentSpec,TrainingSpec
from cvsubstrate.contracts.research import CampaignSpec
from cvsubstrate.data.manifest import load_manifest,validate_experiment
from cvsubstrate.execution.runner import run_experiment
from cvsubstrate.governance.ledger import Ledger,file_lock
from cvsubstrate.governance.policy import preregister
from cvsubstrate.protocols.planner import plan
from cvsubstrate.provenance.bundle import verify_bundle
from cvsubstrate.provenance.io import digest,experiment_identity,read_json,write_json,safe_join
from cvsubstrate.errors import CVRSError

SLUGS={'R':'real','S':'synthetic','R+S':'supplement','S->R':'synthetic-pretrain',
       'R-replay':'real-replay','R->R':'real-pretrain'}
BLOCKERS={'COCO_DEPENDENCY','EVALUATOR_VERSION','ADAPTER_NOT_INSTALLED','MISSING_CHECKPOINT',
          'WORKER_LAUNCH','NATIVE_DEPENDENCIES','MMDET_DEPENDENCIES'}


def load_campaign(path:Path):
    return CampaignSpec.model_validate(read_json(path))


def plan_campaign(campaign:CampaignSpec,base:Path):
    base=Path(base).resolve();cases=[];graph=[];first_key=None
    for backend in campaign.backends:
        original=backend.experiment.model_dump(mode='json')
        dataset=Path(original['dataset']);dataset=dataset if dataset.is_absolute() else base/dataset
        m=load_manifest(dataset)
        if m.splits[original['eval_split']].role not in {'dev','selection'}:
            raise CVRSError('CAMPAIGN_TEST_POLICY','campaigns evaluate explicitly declared dev/selection splits only, never locked test')
        measure_key=digest({'dataset_digest':digest(m),'eval_split':original['eval_split'],'protocol':original['evaluation']})
        if first_key is None:first_key=measure_key
        if first_key!=measure_key:raise CVRSError('CAMPAIGN_COMPARABILITY','campaign backends must share dataset, split and evaluation protocol')
        original['dataset']=str(dataset.resolve())
        if original.get('checkpoint'):
            cp=Path(original['checkpoint']['path']);cp=cp if cp.is_absolute() else base/cp
            original['checkpoint']['path']=str(cp.resolve())
        if original['adapter']['name']=='mmdetection' and original['adapter']['config'].get('config_path'):
            cp=Path(original['adapter']['config']['config_path']);cp=cp if cp.is_absolute() else base/cp
            original['adapter']['config']['config_path']=str(cp.resolve())
        for seed in campaign.seeds:
            for arm in campaign.arms:
                value={**original,'seed':seed}
                value['name']=(campaign.name+'.'+backend.name)[:95]+'.'+SLUGS[arm]+f'.s{seed}'
                training=dict(value.get('training') or {})
                training.update(arm=arm,updates=campaign.updates,pretrain_updates=campaign.pretrain_updates,
                    real_per_update=campaign.real_per_update,synthetic_per_update=campaign.synthetic_per_update)
                value['training']=TrainingSpec.model_validate(training).model_dump(mode='json')
                spec=ExperimentSpec.model_validate(value);validate_experiment(spec,m)
                stages=plan(spec,m);caseid=backend.name[:40]+'.'+SLUGS[arm]+f'.s{seed}.'+experiment_identity(spec)[:10]
                cases.append({'case_id':caseid,'backend':backend.name,'arm':arm,'seed':seed,
                    'experiment':spec.model_dump(mode='json'),'experiment_digest':experiment_identity(spec),
                    'worker_python':backend.worker_python,'protocol_plan':stages})
                previous=None
                for stage in stages['stages']:
                    node=caseid+'/'+stage['name']
                    graph.append({'node':node,'case_id':caseid,'depends_on':[previous] if previous else [],
                                  'weights_transition':stage['checkpoint_transition']})
                    previous=node
    result={'schema_version':'1.0','campaign_digest':digest(campaign),'phase':campaign.phase,'cases':cases,
        'execution_graph':graph,'comparison_key':first_key,'primary_metric_pointer':campaign.primary_metric,
        'control_claim':campaign.control_claim,'compute_equality':'NOT_CLAIMED',
        'training_fairness':'Different backend pretrained weights/architectures remain descriptive unless independently controlled.'}
    result['plan_digest']=digest(result);return result


def _latest_attempts(rows):
    result={}
    for r in rows:
        if r['event'] in {'CASE_STARTED','CASE_SUCCEEDED','CASE_FAILED','CASE_BLOCKED','CASE_INTERRUPTED'}:
            result[r['payload']['case_id']]=r
    return result


def execute_campaign(path:Path,output:Path,*,resume=False,retry_failed=False,worker_python=None):
    path=Path(path).resolve();output=Path(output).resolve();campaign=load_campaign(path)
    plan_value=plan_campaign(campaign,path.parent)
    if output.exists() and not resume:raise CVRSError('OUTPUT_EXISTS','campaign output exists; use explicit resume')
    if resume and not output.exists():raise CVRSError('RESUME_MISSING','campaign to resume does not exist')
    output.mkdir(parents=True,exist_ok=True)
    with file_lock(output/'.campaign.lock'):
        ledger=Ledger(output/'events.jsonl')
        if resume:
            prior=read_json(output/'plan.json')
            if prior!=plan_value:raise CVRSError('CAMPAIGN_CHANGED','cannot resume a different campaign/data/configuration')
            ledger.rows()
        else:
            write_json(output/'campaign.json',campaign);write_json(output/'plan.json',plan_value)
            preregister(ledger,campaign,plan_value['plan_digest'])
        for case in plan_value['cases']:
            previous=_latest_attempts(ledger.rows()).get(case['case_id'])
            if previous and previous['event']=='CASE_SUCCEEDED':
                rp=safe_join(output,previous['payload']['run'])
                verified=verify_bundle(rp)
                if verified['status']!='VERIFIED' or verified.get('run_state')!='SUCCEEDED':
                    raise CVRSError('RESUME_EVIDENCE_CHANGED','completed run evidence is no longer valid')
                continue
            if previous and previous['event'] in {'CASE_FAILED','CASE_BLOCKED','CASE_INTERRUPTED'} and not retry_failed:
                continue
            if previous and previous['event']=='CASE_STARTED':
                # Never guess whether a prior worker still runs. The campaign lock
                # is only a local exclusion guard; preserve the orphan run evidence.
                if not retry_failed:continue
                ledger.append('CASE_INTERRUPTED',{'case_id':case['case_id'],'reason':'explicit retry after incomplete attempt'})
            specpath=output/'specs'/(case['case_id']+'.json')
            if specpath.exists() and read_json(specpath)!=case['experiment']:
                raise CVRSError('CASE_SPEC_CHANGED','existing case specification changed')
            if not specpath.exists():write_json(specpath,case['experiment'])
            ledger.append('CASE_STARTED',{'case_id':case['case_id'],'experiment_digest':case['experiment_digest']})
            start=time.perf_counter()
            try:
                run=run_experiment(specpath,output/'runs'/case['case_id'],
                    worker_python=worker_python or case['worker_python'],timeout=campaign.timeout_seconds)
                verified=verify_bundle(run)
                if verified['status']!='VERIFIED' or verified.get('run_state')!='SUCCEEDED':
                    raise CVRSError('CASE_EVIDENCE','run was not successfully sealed and verified')
                ledger.append('CASE_SUCCEEDED',{'case_id':case['case_id'],'run':run.relative_to(output).as_posix(),
                    'wall_seconds':time.perf_counter()-start,'experiment_digest':case['experiment_digest']})
            except KeyboardInterrupt:
                ledger.append('CASE_INTERRUPTED',{'case_id':case['case_id'],'reason':'operator interruption'});raise
            except Exception as exc:
                code=exc.code if isinstance(exc,CVRSError) else type(exc).__name__
                event='CASE_BLOCKED' if code in BLOCKERS else 'CASE_FAILED'
                ledger.append(event,{'case_id':case['case_id'],'error_code':code,'error':str(exc),
                    'wall_seconds':time.perf_counter()-start})
        latest=_latest_attempts(ledger.rows());counts={name:0 for name in ['SUCCEEDED','FAILED','BLOCKED','INTERRUPTED','NOT_RUN']}
        cases=[]
        for case in plan_value['cases']:
            row=latest.get(case['case_id']);state=row['event'].removeprefix('CASE_') if row else 'NOT_RUN'
            if state=='STARTED':state='INTERRUPTED'
            counts[state]+=1;cases.append({'case_id':case['case_id'],'state':state,'attempt':row['payload'] if row else None})
        result={'schema_version':'1.0','status':'SUCCEEDED' if counts['SUCCEEDED']==len(cases) else 'PARTIAL',
            'campaign_digest':digest(campaign),'plan_digest':plan_value['plan_digest'],'counts':counts,'cases':cases,
            'ledger':ledger.verify(),'scope':'Each native CPU fixture result proves execution/accounting, not a real-world Sim2Real claim.'}
        # This summary is derived. events.jsonl is the append-only primary history.
        write_json(output/'summary.json',result)
        return result
