"""Cross-rank telemetry accounting. Global optimizer steps are NOT summed ranks."""
from __future__ import annotations
import json,sqlite3,hashlib
from collections import Counter
from pathlib import Path
from cvsubstrate.provenance.io import digest

def inspect_rank(path):
    db=sqlite3.connect('file:'+str(Path(path).resolve())+'?mode=ro',uri=True)
    try:
        rows=db.execute('SELECT seq,payload,hash FROM events ORDER BY seq');prev='0'*64;rank=None;run=None;steps=0;batches=0;samples=Counter();sources=Counter();parents=Counter();losses=[];checkpoints=[];world=1;untraced=0
        for seq,text,sha in rows:
            e=json.loads(text)
            if e.get('seq')!=seq or e.get('previous')!=prev or hashlib.sha256(text.encode()).hexdigest()!=sha:raise ValueError('telemetry chain changed')
            prev=sha
            if rank is not None and rank!=e['rank'] or run is not None and run!=e['run_id']:raise ValueError('mixed ledger identities')
            rank=e['rank'];run=e['run_id'];v=e['data']
            if e['kind']=='SESSION_STARTED':world=v.get('world_size',1)
            if e['kind']=='MODEL_BATCH':
                batches+=1
                for m in v['members']:samples[m['sample_id']]+=1;sources[m['source']]+=1
                lineage=v.get('parent_ids')
                if lineage:
                    for item in lineage:
                        for parent in item:parents[str(parent)]+=1
                elif v.get('mixing_policy')!='disabled_or_fully_traced':untraced+=1
            if e['kind']=='OPTIMIZER_STEP':steps+=1
            if e['kind']=='LOSS':losses.append(v)
            if e['kind']=='CHECKPOINT':checkpoints.append(v)
        return {'rank':rank,'world_size':world,'run_id':run,'head_sha256':prev,'optimizer_steps':steps,'model_batches':batches,
            'samples':dict(samples),'sources':dict(sources),'augmentation_parents':dict(parents),'untraced_batches':untraced,
            'loss_observations':losses,'checkpoints':checkpoints}
    finally:db.close()

def aggregate_ranks(paths,expected_world_size):
    rows=[inspect_rank(p) for p in paths]
    if {r['rank'] for r in rows}!=set(range(expected_world_size)) or len(rows)!=expected_world_size:raise ValueError('missing or duplicate rank ledger')
    if len({r['run_id'] for r in rows})!=1 or any(r['world_size']!=expected_world_size for r in rows):raise ValueError('run/world size mismatch')
    same=len({r['optimizer_steps'] for r in rows})==1
    samples=Counter();sources=Counter()
    for r in rows:samples.update(r['samples']);sources.update(r['sources'])
    per_rank={r['rank']:set(r['samples']) for r in rows};shared=sorted(s for s in samples if sum(s in v for v in per_rank.values())>1)
    return {'run_id':rows[0]['run_id'],'world_size':expected_world_size,'ranks':rows,
      'synchronized_optimizer_steps':rows[0]['optimizer_steps'] if same else None,'step_alignment':'ALIGNED' if same else 'MISMATCH',
      'model_exposures':dict(samples),'source_exposures':dict(sources),'cross_rank_sample_overlap':shared,
      'rank_zero_is_not_global':True,'all_reduce_execution_verified':False,
      'meaning':'Aligned rank-local optimizer counters, not proof of all-reduce or source-specific gradients.'}
