"""General, sequential, native-contract research campaigns.

Every stage is an ordinary recorded experiment, with explicit checkpoint edges.
Declared epoch-native adapters are not treated as fixed-update trainers.
"""
from __future__ import annotations
from pathlib import Path
import copy,time,itertools
from cvsubstrate.contracts.groundwork import ResearchCampaign
from cvsubstrate.contracts.models import ExperimentSpec,TrainingSpec
from cvsubstrate.provenance.io import read_json,write_json,digest,file_digest,experiment_identity,safe_join
from cvsubstrate.provenance.bundle import verify_bundle
from cvsubstrate.governance.ledger import Ledger,file_lock
from cvsubstrate.execution.runner import run_experiment
from cvsubstrate.errors import CVRSError

def planned_budgets(c:ResearchCampaign):
    return {a.id:{'real_exposures':sum(s.updates*s.real_per_update for s in a.stages),
        'synthetic_exposures':sum(s.updates*s.synthetic_per_update for s in a.stages),
        'total_exposures':sum(s.updates*(s.real_per_update+s.synthetic_per_update) for s in a.stages),
        'optimizer_steps':sum(s.updates for s in a.stages),'gpu_hours':None,'wall_seconds':None} for a in c.arms}

def check_budgets(c:ResearchCampaign,budgets=None):
    budgets=planned_budgets(c) if budgets is None else budgets;checks=[]
    for rule in c.constraints:
        values={a:budgets.get(a,{}).get(rule.metric) for a in rule.arms}
        if any(v is None for v in values.values()):status='UNOBSERVABLE_BEFORE_EXECUTION'
        elif rule.mode=='equal':status='SATISFIED' if max(values.values())-min(values.values())<=rule.tolerance else 'VIOLATED'
        else:status='SATISFIED' if all(v<=rule.limit+rule.tolerance for v in values.values()) else 'VIOLATED'
        checks.append({'constraint':rule.model_dump(mode='json'),'values':values,'status':status})
    return {'status':'INFEASIBLE' if any(x['status']=='VIOLATED' for x in checks) else 'CONDITIONALLY_FEASIBLE' if any(x['status']=='UNOBSERVABLE_BEFORE_EXECUTION' for x in checks) else 'FEASIBLE',
        'budgets':budgets,'checks':checks,'note':'Planned exposure equality is not identical gradients, compute cost, initialization, or scientific training fairness.'}

def _base_experiment(backend,base):
    raw=backend['experiment']
    if isinstance(raw,str):
        source=(base/raw).resolve();raw=read_json(source);base=source.parent
    else:raw=copy.deepcopy(raw)
    exp=ExperimentSpec.model_validate(raw);d=exp.model_dump(mode='json');d['dataset']=str((base/d['dataset']).resolve())
    if d.get('checkpoint'):d['checkpoint']['path']=str((base/d['checkpoint']['path']).resolve())
    if d['adapter']['name']=='mmdetection' and 'config_path' in d['adapter']['config']:d['adapter']['config']['config_path']=str((base/d['adapter']['config']['config_path']).resolve())
    return d

def compile_campaign(campaign:ResearchCampaign|dict,base:Path):
    c=campaign if isinstance(campaign,ResearchCampaign) else ResearchCampaign.model_validate(campaign)
    budget=check_budgets(c)
    if budget['status']=='INFEASIBLE':raise CVRSError('BUDGET_CONSTRAINT','declared simultaneous fairness/budget constraints cannot be met')
    names=[b['name'] for b in c.backends]
    if len(names)!=len(set(names)):raise ValueError('duplicate backend name')
    cases=[];comparison=None
    from cvsubstrate.contracts.models import DatasetManifest
    for backend in c.backends:
        raw=_base_experiment(backend,Path(base).resolve());m=DatasetManifest.model_validate(read_json(raw['dataset']))
        if digest(m)!=raw['dataset_sha256']:raise CVRSError('DATA_INTEGRITY','campaign dataset digest mismatch')
        if m.splits[raw['eval_split']].role not in {'dev','selection'}:raise CVRSError('PROTECTED_SPLIT','campaign selection cannot inspect a locked test')
        key=digest({'dataset':digest(m),'split':raw['eval_split'],'evaluator':raw['evaluation']})
        if comparison and key!=comparison:raise CVRSError('INCOMPARABLE','campaign detector backends have different evaluation populations/protocols')
        comparison=key
        for arm in c.arms:
            for seed in c.seeds:
                cid=f'{backend["name"]}.{arm.id}.s{seed}';stages=[]
                for j,stage in enumerate(arm.stages):
                    ed=copy.deepcopy(raw);ed['name']=(c.name+'.'+cid+'.'+stage.id)[:180];ed['seed']=seed
                    t=ed.get('training') or {};t.update(arm={'real':'R','synthetic':'S','mixed':'R+S'}[stage.source],updates=stage.updates,
                        real_per_update=max(1,stage.real_per_update),synthetic_per_update=max(1,stage.synthetic_per_update),synthetic_weight=stage.synthetic_weight)
                    ed['training']=TrainingSpec.model_validate(t).model_dump(mode='json')
                    supported=ed['adapter']['name']=='native_torch' or bool(backend.get('capabilities',{}).get('fixed_update_training'))
                    if ed['adapter']['name']=='native_torch':ed['adapter']['config']['stage_policy']={'real_weight':stage.real_weight,'transition':stage.transition if j and stage.initialize_from_previous else 'weights_only_reset_optimizer','stage_id':stage.id}
                    elif stage.real_weight!=1 or stage.transition=='resume_full_state':
                        supported=bool(backend.get('capabilities',{}).get('stage_policy'))
                    if j and not stage.initialize_from_previous:ed['checkpoint']=raw.get('checkpoint')
                    stages.append({'id':stage.id,'index':j,'experiment':ExperimentSpec.model_validate(ed).model_dump(mode='json'),
                        'checkpoint_from_previous':j>0 and stage.initialize_from_previous,'transition':stage.transition,
                        'implementation_support':'AVAILABLE' if supported else 'REQUIRES_FIXED_UPDATE_WORKER_CAPABILITY'})
                cases.append({'case_id':cid,'backend':backend['name'],'worker_python':backend.get('worker_python'),
                    'evaluator_python':backend.get('evaluator_python'),'arm':arm.id,'seed':seed,'stages':stages})
    result={'schema_version':'1.0','campaign_digest':digest(c),'cases':cases,'budgets':budget,'comparison_digest':comparison,
        'phase':c.phase,'selection_digest':c.selection_digest,'execution_order':'backend, arm, seed, sequential stage',
        'sampling':'Independent deterministic source streams per ExperimentSpec; each stage restarts its explicit sample schedule. Full state means optimizer/scheduler/Torch RNG continuity, not a hidden dataloader cursor.'}
    result['plan_digest']=digest(result);return result

def execute_research_campaign(path:Path,output:Path,*,resume=False,retry_failed=False,worker_python=None,timeout=300):
    path=Path(path).resolve();out=Path(output).resolve();c=ResearchCampaign.model_validate(read_json(path));plan=compile_campaign(c,path.parent)
    if out.exists() and not resume:raise CVRSError('OUTPUT_EXISTS','use a fresh campaign path or explicit resume')
    if resume and not out.exists():raise CVRSError('RESUME_MISSING','no campaign exists')
    out.mkdir(parents=True,exist_ok=True)
    with file_lock(out/'.dsl.lock'):
        ledger=Ledger(out/'events.jsonl')
        if resume:
            if read_json(out/'plan.json')!=plan:raise CVRSError('RESUME_CHANGED','campaign/code inputs changed')
        else:
            write_json(out/'campaign.json',c);write_json(out/'plan.json',plan)
            ledger.append('RESEARCH_CAMPAIGN_DECLARED',{'campaign_digest':digest(c),'phase':c.phase,'seeds':c.seeds,'selection_digest':c.selection_digest})
        all_cases=[]
        for case in plan['cases']:
            case_results=[];previous=None
            for stage in case['stages']:
                nid=case['case_id']+'.'+stage['id'];history=[r for r in ledger.rows() if r['payload'].get('node_id')==nid];last=history[-1] if history else None
                if last and last['event']=='STAGE_SUCCEEDED':
                    run=safe_join(out,last['payload']['run']);verified=verify_bundle(run)
                    if verified['status']!='VERIFIED' or verified.get('run_state')!='SUCCEEDED':raise CVRSError('EVIDENCE_CHANGED','prior stage evidence no longer verifies')
                    previous=run;case_results.append(last['payload']);continue
                if last and not retry_failed:
                    case_results.append({'node_id':nid,'status':'NOT_RETRIED','previous':last});break
                ed=copy.deepcopy(stage['experiment'])
                if stage['checkpoint_from_previous']:
                    if previous is None:case_results.append({'node_id':nid,'status':'BLOCKED','reason':'previous checkpoint missing'});break
                    ck=previous/'worker'/'checkpoint.pt'
                    if not ck.is_file():raise CVRSError('CHECKPOINT_MISSING','prior worker must expose owned checkpoint.pt or use a custom graph action')
                    ed['checkpoint']={'path':str(ck),'sha256':file_digest(ck),'trust':'owned_weights_only','license':'unknown'}
                specpath=out/'specs'/(nid+'.json');write_json(specpath,ed)
                ledger.append('STAGE_STARTED',{'node_id':nid,'experiment_digest':experiment_identity(ExperimentSpec.model_validate(ed))})
                start=time.perf_counter()
                try:
                    if stage['implementation_support']!='AVAILABLE':raise CVRSError('UNSUPPORTED_CAPABILITY','worker does not declare fixed-update stage semantics; epoch counts are not interchangeable')
                    run=run_experiment(specpath,out/'runs'/nid,worker_python or case['worker_python'],timeout,evaluator_python=case['evaluator_python'])
                    v=verify_bundle(run)
                    if v.get('run_state')!='SUCCEEDED':raise CVRSError('EXECUTION_FAILED','stage did not seal a successful run')
                    previous=run;execution=read_json(run/'worker'/'execution.json');result={'node_id':nid,'status':'SUCCEEDED','run':run.relative_to(out).as_posix(),
                        'measured_counts':execution.get('measured_counts'),'wall_seconds':time.perf_counter()-start,'gpu_hours':None}
                    ledger.append('STAGE_SUCCEEDED',result);case_results.append(result)
                except KeyboardInterrupt:
                    ledger.append('STAGE_INTERRUPTED',{'node_id':nid,'status':'INTERRUPTED'});raise
                except Exception as exc:
                    result={'node_id':nid,'status':'FAILED','code':getattr(exc,'code',type(exc).__name__),'message':str(exc),'wall_seconds':time.perf_counter()-start}
                    ledger.append('STAGE_FAILED',result);case_results.append(result);break
            all_cases.append({'case_id':case['case_id'],'arm':case['arm'],'backend':case['backend'],'seed':case['seed'],
                'status':'SUCCEEDED' if len(case_results)==len(case['stages']) and all(r.get('status')=='SUCCEEDED' for r in case_results) else 'FAILED_OR_INCOMPLETE','stages':case_results})
        result={'schema_version':'1.0','plan_digest':plan['plan_digest'],'status':'SUCCEEDED' if all(x['status']=='SUCCEEDED' for x in all_cases) else 'PARTIAL',
            'cases':all_cases,'measured_budget_checks':measured_budget_checks(c,all_cases),'planned_budgets':plan['budgets'],'ledger':ledger.verify(),'claims':'Execution accounting only; no scientific effect is inferred.'}
        write_json(out/'summary.json',result);return result

def set_pointer(document,pointer,value):
    if not pointer.startswith('/') or pointer=='/':raise ValueError('non-root RFC6901 pointer required')
    keys=[k.replace('~1','/').replace('~0','~') for k in pointer[1:].split('/')];node=document
    for key in keys[:-1]:node=node[int(key)] if isinstance(node,list) else node[key]
    key=keys[-1]
    if isinstance(node,list):node[int(key)]=value
    elif key in node:node[key]=value
    else:raise ValueError('sweeps may modify existing fields only')

def expand_sweep(base:dict,axes:dict,output:Path,*,max_cases=10000):
    if not axes or any(not isinstance(v,list) or not v for v in axes.values()):raise ValueError('nonempty finite sweep axes required')
    count=1
    for v in axes.values():count*=len(v)
    if count>max_cases:raise ValueError('sweep exceeds explicit case limit')
    out=Path(output)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','sweep output must be new')
    out.mkdir(parents=True);keys=sorted(axes);cases=[];seen=set()
    for values in itertools.product(*(axes[k] for k in keys)):
        child=copy.deepcopy(base)
        for k,v in zip(keys,values):set_pointer(child,k,v)
        # Accept only a valid known experiment/campaign, not arbitrary untyped job strings.
        model=ResearchCampaign.model_validate(child) if 'arms' in child else ExperimentSpec.model_validate(child)
        value=model.model_dump(mode='json');identity=digest(value)
        if identity in seen:raise ValueError('duplicate semantic sweep case')
        seen.add(identity);name=identity+'.json';write_json(out/name,value);cases.append({'digest':identity,'path':name,'parameters':dict(zip(keys,values))})
    report={'base_digest':digest(base),'axes':axes,'cases':cases,'count':len(cases)};write_json(out/'sweep.json',report)
    from cvsubstrate.provenance.artifact_set import seal_directory
    seal_directory(out);return report


def measured_budget_checks(c,cases):
    groups={}
    for case in cases:
        key=(case['backend'],case['seed']);g=groups.setdefault(key,{})
        counts=[r.get('measured_counts') for r in case['stages']]
        if case['status']!='SUCCEEDED' or any(v is None for v in counts):
            g[case['arm']]={k:None for k in planned_budgets(c)[case['arm']]};continue
        def total(key):
            values=[r.get(key) for r in counts]
            return sum(values) if all(isinstance(v,(int,float)) for v in values) else None
        real=total('real_exposures');syn=total('synthetic_exposures')
        g[case['arm']]={'real_exposures':real,'synthetic_exposures':syn,
            'total_exposures':real+syn if real is not None and syn is not None else None,
            'optimizer_steps':total('optimizer_updates'),'wall_seconds':sum(r.get('wall_seconds',0) for r in case['stages']),'gpu_hours':None}
    return [{'backend':b,'seed':seed,**check_budgets(c,g)} for (b,seed),g in sorted(groups.items())]
