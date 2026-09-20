"""Declared-tolerance parity for two canonical output files; no export performed."""
import math
from cvsubstrate.contracts.models import DetectionPrediction
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import digest


def audit_predictions(left:list[DetectionPrediction],right:list[DetectionPrediction],*,box_atol=1e-5,score_atol=1e-6,order='as_emitted'):
    if any(not math.isfinite(v) or v<0 for v in (box_atol,score_atol)):raise ValueError('finite nonnegative tolerances required')
    if order not in {'as_emitted','canonical_sort'}:raise ValueError('explicit supported order policy required')
    ids_l=[x.sample_id for x in left];ids_r=[x.sample_id for x in right]
    if len(set(ids_l))!=len(ids_l) or len(set(ids_r))!=len(ids_r):raise CVRSError('DUPLICATE_PREDICTIONS','duplicate image row')
    mismatches=[];maxbox=maxscore=0.0;total=0;rd={x.sample_id:x for x in right}
    if set(ids_l)!=set(ids_r):mismatches.append('image universes differ')
    for a in left:
        b=rd.get(a.sample_id)
        if b is None:continue
        if (a.width,a.height)!=(b.width,b.height):mismatches.append(f'{a.sample_id}: image dimensions differ')
        aa=list(zip(a.category_ids,a.boxes,a.scores));bb=list(zip(b.category_ids,b.boxes,b.scores))
        if order=='canonical_sort':aa.sort(key=lambda x:(x[0],x[1],x[2]));bb.sort(key=lambda x:(x[0],x[1],x[2]))
        if len(aa)!=len(bb):mismatches.append(f'{a.sample_id}: detection counts differ')
        for i,(x,y) in enumerate(zip(aa,bb)):
            total+=1
            delta=max(abs(v-w) for v,w in zip(x[1],y[1]));sd=abs(x[2]-y[2]);maxbox=max(maxbox,delta);maxscore=max(maxscore,sd)
            if x[0]!=y[0] or delta>box_atol or sd>score_atol:mismatches.append(f'{a.sample_id}: prediction {i} differs')
    return {'kind':'CANONICAL_OUTPUT_PARITY','status':'PASS' if not mismatches else 'FAIL',
        'left_digest':digest([x.model_dump(mode='json') for x in left]),'right_digest':digest([x.model_dump(mode='json') for x in right]),
        'box_absolute_tolerance':box_atol,'score_absolute_tolerance':score_atol,'order_policy':order,
        'pairs_checked':total,'maximum_box_delta':maxbox,'maximum_score_delta':maxscore,
        'mismatch_count':len(mismatches),'mismatches':mismatches[:100],
        'limits':'Output-file parity only. Does not prove model export, runtime execution, speed or same preprocessing. Canonical sorting is not optimal geometric matching.'}
