"""Measured-plan-ready R/S/mixing/pretrain/replay controls with separate RNG streams.

R-replay mirrors R+S with a second REAL forward/loss group instead of synthetic.
R->R mirrors synthetic pretraining with a real-only pretraining stage. Equal
exposure and loss grouping do not imply equal wall time or learned gradients.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import random
from cvsubstrate.contracts.models import DatasetManifest,ExperimentSpec
from cvsubstrate.data.manifest import validate_experiment
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import digest


def source_seed(seed:int,source:str,update:int=0)->int:
    return int.from_bytes(hashlib.sha256(f'cvrs-stream-v1|{seed}|{source}|{update}'.encode()).digest()[:8],'big')%2**31


def stream(ids:list[str],count:int,seed:int)->list[str]:
    if count<0:raise ValueError('negative exposure count')
    if count and not ids:raise CVRSError('MISSING_SOURCE','the plan requires an empty source pool')
    rng=random.Random(seed);values=[]
    while len(values)<count:
        batch=list(ids);rng.shuffle(batch);values.extend(batch)
    return values[:count]


def plan(spec:ExperimentSpec,m:DatasetManifest)->dict:
    validate_experiment(spec,m)
    t=spec.training
    if t is None:raise CVRSError('NO_TRAINING','a protocol plan requires a training specification')
    byid={s.id:s for s in m.samples};ids=m.splits[spec.train_split].sample_ids
    pools={source:[i for i in ids if byid[i].source_kind==source] for source in ['real','synthetic','unknown']}
    definitions={
        'R':[('real','R',t.updates)],'S':[('synthetic','S',t.updates)],
        'R+S':[('supplement','R+S',t.updates)],
        'S->R':[('pretrain','S',t.pretrain_updates),('finetune','R',t.updates)],
        'R-replay':[('replay-control','R-replay',t.updates)],
        'R->R':[('real-pretrain','R',t.pretrain_updates),('finetune','R',t.updates)],
    }
    if t.arm=='R->R' and t.real_per_update!=t.synthetic_per_update:
        raise CVRSError('CONTROL_EXPOSURE','R->R requires equal real/synthetic samples per update to match S->R pretraining exposure')
    stages=[];all_real=[];all_syn=[];all_primary=[];all_replay=[];global_update=0
    for name,arm,updates in definitions[t.arm]:
        real_seed=source_seed(spec.seed,'real-pretrain' if name=='real-pretrain' else 'real')
        real=stream(pools['real'],updates*t.real_per_update,real_seed) if arm in {'R','R+S','R-replay'} else []
        syn=stream(pools['synthetic'],updates*t.synthetic_per_update,source_seed(spec.seed,'synthetic')) if arm in {'S','R+S'} else []
        replay=stream(pools['real'],updates*t.synthetic_per_update,source_seed(spec.seed,'real-replay')) if arm=='R-replay' else []
        steps=[]
        for i in range(updates):
            global_update+=1
            r=real[i*t.real_per_update:(i+1)*t.real_per_update]
            s=syn[i*t.synthetic_per_update:(i+1)*t.synthetic_per_update]
            rr=replay[i*t.synthetic_per_update:(i+1)*t.synthetic_per_update]
            step={'update':global_update,'stage_update':i+1,'real':r+rr,'synthetic':s,
                'real_forward_seed':source_seed(spec.seed,'real-forward',i+1),
                'synthetic_forward_seed':source_seed(spec.seed,'synthetic-forward',i+1)}
            if rr:
                step['real_primary']=r;step['real_replay']=rr
                step['real_replay_forward_seed']=source_seed(spec.seed,'synthetic-forward',i+1)
            steps.append(step);all_real+=r+rr;all_syn+=s;all_primary+=r;all_replay+=rr
        stages.append({'name':name,'arm':arm,'optimizer_reset':name=='finetune',
            'checkpoint_transition':t.stage_transition if name=='finetune' else 'none','steps':steps})
    counts={'real_exposures':len(all_real),'synthetic_exposures':len(all_syn),
        'real_unique':len(set(all_real)),'synthetic_unique':len(set(all_syn)),
        'real_replayed_exposures':len(all_real)-len(set(all_real)),
        'synthetic_replayed_exposures':len(all_syn)-len(set(all_syn)),
        'optimizer_updates':global_update,'unknown_source_samples_excluded':len(pools['unknown']),
        'additional_real_control_exposures':len(all_replay),'primary_real_exposures':len(all_primary)}
    result={'schema_version':'1.0','arm':t.arm,'held_constant_claim':t.fairness,'stages':stages,
        'planned_counts':counts,'measured_counts':None,'nominal_synthetic_loss_weight':t.synthetic_weight,
        'loss_semantics':'One optimizer step; source detector losses are separately mean-reduced. R+S: real + weight*synthetic. R-replay: primary-real + same weight*additional-real.',
        'cautions':['Equal real exposure is not equal compute/total exposure.',
            'Source-specific RNG streams preserve the primary real sampling/forward seeds, not equal gradients or proposals after weights diverge.',
            'Native fixture worker has no stochastic image augmentation.',
            'S->R and R->R reset optimizer and scheduler at the stage boundary but retain learned weights.',
            'A replay control matches scheduled exposure and nominal source-loss grouping, not measured GPU time.'],
        'sample_exposure_counts':{'real':dict(Counter(all_real)),'synthetic':dict(Counter(all_syn))}}
    result['plan_digest']=digest(result);return result
