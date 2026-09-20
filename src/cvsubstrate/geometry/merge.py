"""Deterministic merge strategies with explicit semantics and audit trails.

These algorithms are local research implementations, not claims of equivalence
to any vendor's similarly named algorithm. Coordinates are continuous pixels.
"""
from __future__ import annotations
import math
from typing import Any
from cvsubstrate.contracts.groundwork import MergePolicy
from cvsubstrate.geometry.polygons import canonical_polygon, polygon_iou

def box_iou(a, b):
    w=max(0.0,min(a[2],b[2])-max(a[0],b[0]));h=max(0.0,min(a[3],b[3])-max(a[1],b[1]))
    inter=w*h;union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
    return inter/union if union>0 else 0.0

def _validate(items, oriented):
    ids=set();result=[]
    for i,item in enumerate(items):
        r=dict(item);r.setdefault('id',str(i));r.setdefault('weight',1.0)
        if r['id'] in ids:raise ValueError('duplicate detection identity')
        ids.add(r['id'])
        if not isinstance(r.get('category_id'),int) or isinstance(r['category_id'],bool):raise ValueError('integer category required')
        if not math.isfinite(r.get('score',float('nan'))) or not 0<=r['score']<=1:raise ValueError('invalid score')
        if not math.isfinite(r['weight']) or r['weight']<=0:raise ValueError('positive source weight required')
        if oriented:r['polygon']=canonical_polygon(r['polygon'])
        else:
            b=r.get('box',[])
            if len(b)!=4 or any(not math.isfinite(v) for v in b) or b[2]<=b[0] or b[3]<=b[1]:raise ValueError('invalid box')
            r['box']=list(map(float,b))
        r['members']=[r['id']];result.append(r)
    return sorted(result,key=lambda r:(-r['score'],str(r['id'])))

def merge_detections(items:list[dict[str,Any]],policy:MergePolicy|dict)->dict:
    p=policy if isinstance(policy,MergePolicy) else MergePolicy.model_validate(policy)
    oriented=p.kind=='oriented_nms'
    if not oriented and any('polygon' in r and 'box' not in r for r in items):raise ValueError('polygon input requires oriented_nms')
    rows=_validate(items,oriented);initial=len(rows);audit=[];kept=[]
    rows=[r for r in rows if r['score']>=p.score_threshold]
    if p.kind=='keep_all':kept=rows
    elif p.kind=='weighted_box_fusion':
        clusters=[]
        for row in rows:
            candidates=[(box_iou(row['box'],c['box']),i) for i,c in enumerate(clusters) if c['category_id']==row['category_id']]
            candidates.sort(key=lambda pair:(-pair[0],pair[1]))
            if candidates and candidates[0][0]>p.iou_threshold:
                c=clusters[candidates[0][1]];c['_rows'].append(row)
            else:
                c={**row,'_rows':[row]};clusters.append(c)
            weights=[r['score']*r['weight'] for r in c['_rows']];den=sum(weights)
            # Zero-score inputs have no confidence weight; retain declared source weights.
            if den==0:weights=[r['weight'] for r in c['_rows']];den=sum(weights)
            c['box']=[sum(r['box'][j]*w for r,w in zip(c['_rows'],weights))/den for j in range(4)]
            c['score']=max(r['score'] for r in c['_rows']) if p.score_fusion=='max' else sum(r['score']*r['weight'] for r in c['_rows'])/sum(r['weight'] for r in c['_rows'])
            c['members']=[r['id'] for r in c['_rows']]
        for c in clusters:
            c.pop('_rows');kept.append(c);audit.append({'fused':c['members'],'output_id':c['id']})
    else:
        while rows:
            rows.sort(key=lambda r:(-r['score'],str(r['id'])))
            best=rows.pop(0);kept.append(best);survivors=[]
            for row in rows:
                overlap=(polygon_iou(best['polygon'],row['polygon']) if oriented else box_iou(best['box'],row['box'])) if best['category_id']==row['category_id'] else 0.0
                if p.kind=='soft_nms':
                    # Gaussian Soft-NMS applies to same-class overlap; sigma is recorded.
                    old=row['score'];row['score']*=math.exp(-(overlap*overlap)/p.sigma)
                    if row['score']!=old:audit.append({'decayed':row['id'],'by':best['id'],'before':old,'after':row['score'],'iou':overlap})
                    if row['score']>=p.score_threshold:survivors.append(row)
                elif overlap>p.iou_threshold:
                    audit.append({'suppressed':row['id'],'by':best['id'],'iou':overlap})
                else:survivors.append(row)
            rows=survivors
    kept.sort(key=lambda r:(-r['score'],str(r['id'])))
    truncated=kept[p.max_detections:];kept=kept[:p.max_detections]
    return {'algorithm_version':'cvrs-merge-1','policy':p.model_dump(mode='json'),'input_count':initial,
        'output_count':len(kept),'truncated_ids':[r['id'] for r in truncated],'detections':kept,'audit':audit,
        'semantics':'class-aware; strict IoU > threshold; Gaussian Soft-NMS; online confidence/source-weighted WBF; stable score/ID ordering'}
