"""Seed-level descriptive statistics; no silent missing-seed exclusion."""
import math
import random
import statistics


def summarize_seeds(values:dict[int,float|None]):
    if any(isinstance(k,bool) or not isinstance(k,int) or isinstance(v,bool) for k,v in values.items()):
        raise ValueError('integer seed IDs and numeric-or-null results required')
    known={int(k):float(v) for k,v in values.items() if v is not None}
    if any(not math.isfinite(v) for v in known.values()):raise ValueError('nonfinite seed result')
    vals=list(known.values());missing=sorted(int(k) for k,v in values.items() if v is None)
    return {'per_seed':{str(k):values[k] for k in sorted(values)},'available':len(vals),'missing_seeds':missing,
        'mean':statistics.fmean(vals) if vals else None,'sample_std':statistics.stdev(vals) if len(vals)>1 else None,
        'all_declared_seeds_present':not missing,'reason':None if vals else 'no measured values'}


def paired_seed_difference(left:dict[int,float|None],right:dict[int,float|None],*,bootstrap_samples=2000,seed=1701):
    if bootstrap_samples<100:raise ValueError('at least 100 bootstrap samples for an interval')
    keys=sorted(set(left)|set(right));missing=[k for k in keys if left.get(k) is None or right.get(k) is None]
    delta={k:(right[k]-left[k] if k not in missing else None) for k in keys}
    result=summarize_seeds(delta);result['unpaired_or_missing_seeds']=missing
    result['direction']='NO_MEASUREMENTS' if result['mean'] is None else ('OBSERVED_INCREASE' if result['mean']>0 else 'OBSERVED_DECREASE' if result['mean']<0 else 'OBSERVED_NO_CHANGE')
    result['bootstrap_interval_95']=None
    if result['available']>=3:
        rng=random.Random(seed);v=[x for x in delta.values() if x is not None]
        means=sorted(statistics.fmean(rng.choice(v) for _ in v) for _ in range(bootstrap_samples))
        def percentile(q):
            x=(len(means)-1)*q;i=int(x);f=x-i
            return means[i]*(1-f)+means[min(i+1,len(means)-1)]*f
        result['bootstrap_interval_95']=[percentile(.025),percentile(.975)]
    result['limits']='Paired differences on measured seeds only, with all missing pairs listed. Few-seed bootstrap intervals are unstable; not independent scientific confirmation or a causal verdict.'
    return result
