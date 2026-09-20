"""Custom pixel/physical-size stratified metrics. Not official COCO or DOTA AP."""
from collections import Counter,defaultdict
from cvsubstrate.contracts.groundwork import ObjectSizePolicy
from cvsubstrate.contracts.models import DatasetManifest,DetectionPrediction
from cvsubstrate.contracts.research import TinyEvaluationPolicy
from cvsubstrate.evaluation.tiny import tiny_diagnostics
from cvsubstrate.geometry.merge import box_iou
from cvsubstrate.provenance.io import digest

def object_size(box,policy:ObjectSizePolicy,gsd=None):
    w=box[2]-box[0];h=box[3]-box[1]
    values={'width_px':w,'height_px':h,'area_px2':w*h,'sqrt_area_px':(w*h)**0.5,'max_side_px':max(w,h)}
    if policy.statistic=='area_m2':
        if not gsd or len(gsd)!=2 or min(gsd)<=0:return None
        return w*h*gsd[0]*gsd[1]
    return values[policy.statistic]

def label(value,edges):
    if value is None:return 'unknown'
    for i,lo in enumerate(edges):
        hi=edges[i+1] if i+1<len(edges) else None
        if hi is None or value<hi:return f'[{lo:g},{hi:g})' if hi is not None else f'[{lo:g},inf)'
    raise ValueError('invalid size')

def _ap(events,total):
    if not total:return None
    groups=defaultdict(list)
    for e in events:groups[e['score']].append(e)
    tp=fp=0;curve=[]
    for score,group in sorted(groups.items(),reverse=True):
        tp+=sum(e['kind']=='TP' for e in group);fp+=sum(e['kind']=='FP' for e in group)
        curve.append((tp/total,tp/(tp+fp) if tp+fp else 0))
    return sum(max([p for r,p in curve if r>=i/100]+[0.0]) for i in range(101))/101

def size_metrics(m:DatasetManifest,split:str,rows:list[DetectionPrediction],size_policy:ObjectSizePolicy|dict,*,iou=0.5,threshold=0.5,gsd_by_image=None):
    p=size_policy if isinstance(size_policy,ObjectSizePolicy) else ObjectSizePolicy.model_validate(size_policy)
    if not 0<iou<=1 or not 0<=threshold<=1:raise ValueError('invalid thresholds')
    diagnostics=tiny_diagnostics(m,split,rows,TinyEvaluationPolicy(iou=iou,fixed_score_threshold=threshold))
    samples={s.id:s for s in m.samples};predictions={r.sample_id:r for r in rows};gsd_by_image=gsd_by_image or {};events=[];totals=Counter()
    for sid in m.splits[split].sample_ids:
        s=samples[sid];r=predictions[sid];gt=[b for b in s.boxes if not b.ignore and not b.iscrowd];ignored=[b for b in s.boxes if b.ignore or b.iscrowd];used=set()
        bins=[label(object_size(b.xyxy,p,gsd_by_image.get(sid)),p.edges) for b in gt]
        totals.update(bins)
        for i in sorted(range(len(r.scores)),key=lambda j:(-r.scores[j],j)):
            candidates=[(box_iou(r.boxes[i],b.xyxy),j) for j,b in enumerate(gt) if j not in used and b.category_id==r.category_ids[i]]
            overlap,j=max(candidates,default=(-1,-1),key=lambda t:(t[0],-t[1]))
            if overlap>=iou:used.add(j);kind='TP';bucket=bins[j]
            else:
                kind='FP';bucket=label(object_size(r.boxes[i],p,gsd_by_image.get(sid)),p.edges)
                # Explicit local ignore rule matches noncrowd IoU / crowd intersection-over-detection.
                for b in ignored:
                    if b.category_id!=r.category_ids[i]:continue
                    q=r.boxes[i];v=b.xyxy;inter=max(0,min(q[2],v[2])-max(q[0],v[0]))*max(0,min(q[3],v[3])-max(q[1],v[1]))
                    ov=inter/((q[2]-q[0])*(q[3]-q[1])) if b.iscrowd else box_iou(q,v)
                    if ov>=iou:kind='IGNORED';break
            events.append({'sample_id':sid,'kind':kind,'score':r.scores[i],'size_bin':bucket})
    result={}
    for b in sorted(set(totals)|{e['size_bin'] for e in events}):
        ev=[e for e in events if e['size_bin']==b and e['kind']!='IGNORED'];selected=[e for e in ev if e['score']>=threshold]
        tp=sum(e['kind']=='TP' for e in selected);fp=sum(e['kind']=='FP' for e in selected);n=totals[b]
        result[b]={'ground_truth':n,'true_positives':tp,'false_positives':fp,'recall':tp/n if n else None,
            'precision':tp/(tp+fp) if tp+fp else None,'miss_rate':1-tp/n if n else None,
            'diagnostic_AP101':_ap(ev,n),'FP_per_image':fp/len(m.splits[split].sample_ids)}
    return {'kind':'SIZE_DIAGNOSTICS_NOT_OFFICIAL_AP','dataset_digest':digest(m),'split':split,'size_policy':p.model_dump(mode='json'),
        'iou':iou,'fixed_score_threshold':threshold,'bins':result,'global_fppi':diagnostics['aggregate']['recall_at_fppi'],
        'borders':diagnostics['aggregate']['border_recall_at_fixed_threshold'],'density':diagnostics['density_slices'],
        'semantics':'Global class-aware greedy matches; matched detections use GT size, unmatched detections use predicted size. AP101 interpolates per-size event curves, not official area-range AP. FPPI threshold sweeps are development-only.'}
