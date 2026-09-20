"""Tiny-object/FROC diagnostics, deliberately distinct from official COCO/DOTA AP.

Matching is greedy by score within each image/class; score ties are admitted as
whole groups in operating curves. Size slices refer to matched GROUND TRUTH,
while their FP/image budget remains the global image-population budget.
"""
from __future__ import annotations
from collections import Counter,defaultdict
import math
from cvsubstrate.contracts.models import DatasetManifest,DetectionPrediction
from cvsubstrate.contracts.research import TinyEvaluationPolicy
from cvsubstrate.data.tiling import iou
from cvsubstrate.evaluation.metrics import validate_predictions
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import digest


def size_bin(area,edges):
    size=math.sqrt(area)
    for i,lo in enumerate(edges):
        hi=edges[i+1] if i+1<len(edges) else None
        if hi is None or size<hi:return f'[{lo:g},{hi:g})' if hi is not None else f'[{lo:g},inf)'
    raise AssertionError('unreachable')


def _stats(tp,fp,ignored,total,images,bin_hits,bin_totals,threshold):
    return {'score_threshold':threshold,'true_positives':tp,'false_positives':fp,'ignored_detections':ignored,
        'ground_truth':total,'images':images,'recall':tp/total if total else None,
        'precision':tp/(tp+fp) if tp+fp else None,'miss_rate':1-tp/total if total else None,
        'false_positives_per_image':fp/images if images else None,
        'size_slices':{k:{'ground_truth':n,'matched':bin_hits.get(k,0),
            'recall':bin_hits.get(k,0)/n if n else None} for k,n in bin_totals.items()}}


def _population(samples,predictions,ids,policy):
    events=[];total=0;totals=Counter()
    for sid in ids:
        sample=samples[sid];pred=predictions[sid]
        gt=[b for b in sample.boxes if not b.iscrowd and not b.ignore]
        ignore=[b for b in sample.boxes if b.iscrowd or b.ignore]
        used=set();total+=len(gt)
        for b in gt:totals[size_bin((b.xyxy[2]-b.xyxy[0])*(b.xyxy[3]-b.xyxy[1]),policy.size_edges)]+=1
        order=sorted(range(len(pred.scores)),key=lambda i:(-pred.scores[i],i))[:policy.max_detections_per_image]
        for i in order:
            box,score,cat=pred.boxes[i],pred.scores[i],pred.category_ids[i]
            candidates=[(iou(box,b.xyxy),j) for j,b in enumerate(gt) if j not in used and b.category_id==cat]
            overlap,j=max(candidates,default=(-1.0,-1),key=lambda v:(v[0],-v[1]))
            event={'score':score,'sample_id':sid,'prediction_index':i,'result':'FP','gt_bin':None}
            if overlap>=policy.iou:
                used.add(j);b=gt[j]
                event.update(result='TP',gt_bin=size_bin((b.xyxy[2]-b.xyxy[0])*(b.xyxy[3]-b.xyxy[1]),policy.size_edges),
                    gt_border_distance_px=min(b.xyxy[0],b.xyxy[1],sample.width-b.xyxy[2],sample.height-b.xyxy[3]))
            else:
                area=(box[2]-box[0])*(box[3]-box[1])
                for b in ignore:
                    if b.category_id!=cat:continue
                    v=b.xyxy
                    inter=max(0,min(box[2],v[2])-max(box[0],v[0]))*max(0,min(box[3],v[3])-max(box[1],v[1]))
                    overlap=inter/area if b.iscrowd else iou(box,v)
                    if overlap>=policy.iou:event['result']='IGNORED';break
            events.append(event)
    all_bins=[f'[{lo:g},{policy.size_edges[i+1]:g})' if i+1<len(policy.size_edges) else f'[{lo:g},inf)'
              for i,lo in enumerate(policy.size_edges)]
    for key in all_bins:totals.setdefault(key,0)
    grouped=defaultdict(list)
    for e in events:grouped[e['score']].append(e)
    tp=fp=ignored=0;hits=Counter();curve=[_stats(0,0,0,total,len(ids),hits,totals,None)]
    for score,group in sorted(grouped.items(),reverse=True):
        for e in group:
            if e['result']=='TP':tp+=1;hits[e['gt_bin']]+=1
            elif e['result']=='FP':fp+=1
            else:ignored+=1
        curve.append(_stats(tp,fp,ignored,total,len(ids),hits,totals,score))
    fixed=curve[0]
    for point in curve[1:]:
        if point['score_threshold']>=policy.fixed_score_threshold:fixed=point
    fppi={}
    for budget in policy.fppi_budgets:
        choices=[x for x in curve if x['false_positives_per_image']<=budget]
        best=max(choices,key=lambda x:(x['true_positives'],-x['false_positives'],2.0 if x['score_threshold'] is None else x['score_threshold']))
        fppi[str(budget)]={**best,'budget_fppi':budget,'threshold_selection_scope':'this development population only'}
    border_slices={}
    for distance in policy.border_distances_px:
        total_border=sum(min(b.xyxy[0],b.xyxy[1],samples[sid].width-b.xyxy[2],samples[sid].height-b.xyxy[3])<=distance
            for sid in ids for b in samples[sid].boxes if not b.iscrowd and not b.ignore)
        hits_border=sum(e['result']=='TP' and e['score']>=policy.fixed_score_threshold and e.get('gt_border_distance_px',float('inf'))<=distance for e in events)
        border_slices[str(distance)]={'maximum_nearest_border_distance_px':distance,'ground_truth':total_border,'matched':hits_border,'recall':hits_border/total_border if total_border else None}
    return {'border_recall_at_fixed_threshold':border_slices,'fixed_threshold':{**fixed,'requested_score_threshold':policy.fixed_score_threshold},
        'recall_at_fppi':fppi,'curve':curve,'matched_events':events,
        'no_ground_truth_reason':'zero positive nonignored ground-truth objects' if not total else None}


def tiny_diagnostics(m: DatasetManifest,split: str,rows:list[DetectionPrediction],policy:TinyEvaluationPolicy):
    if split not in m.splits or m.splits[split].role!='dev':
        raise CVRSError('EVAL_ROLE','threshold-sweeping diagnostics are development-only; no locked-test tuning')
    validate_predictions(m,split,rows)
    samples={s.id:s for s in m.samples};pred={p.sample_id:p for p in rows};ids=m.splits[split].sample_ids
    groups=defaultdict(list);density_groups=defaultdict(list)
    for sid in ids:
        groups[samples[sid].domain].append(sid)
        count=sum(not b.iscrowd and not b.ignore for b in samples[sid].boxes)
        for i,lo in enumerate(policy.density_edges):
            hi=policy.density_edges[i+1] if i+1<len(policy.density_edges) else None
            if hi is None or count<hi:
                density_groups[f'[{lo},{hi})' if hi is not None else f'[{lo},inf)'].append(sid);break
    return {'schema_version':'1.0','kind':'TINY_FROC_DIAGNOSTICS_NOT_OFFICIAL_AP',
        'dataset_digest':digest(m),'split':split,'protocol':policy.model_dump(mode='json'),
        'aggregate':_population(samples,pred,ids,policy),
        'density_definition':'positive nonignored ground-truth objects per source image; bins derived without model predictions',
        'density_slices':{k:_population(samples,pred,v,policy) for k,v in sorted(density_groups.items())},
        'domain_slices':{k:_population(samples,pred,v,policy) for k,v in sorted(groups.items())},
        'limits':['Not COCO AP, DOTA AP, probability calibration, or a claim of deployment performance.',
            'Size = sqrt(horizontal bbox pixel area); NOT segmentation area or physical size.',
            'FPPI threshold selection occurs on this development set; freeze thresholds before final evaluation.',
            'All predictions tied at a score enter together; there is no favorable partial tie selection.',
            'Size-slice recall uses globally matched ground truth and the global FP/image budget.']}
