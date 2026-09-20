"""Tensor and matched-detection fidelity; native metric comparability is separate."""
from pathlib import Path
from cvsubstrate.provenance.io import read_json,file_digest,safe_join,digest
from cvsubstrate.geometry.merge import box_iou
from cvsubstrate.errors import CVRSError

def compare_arrays(left_dir,right_dir,*,atol=1e-6,rtol=1e-5,name_mapping=None):
    import numpy as np
    if atol<0 or rtol<0:raise ValueError('nonnegative predeclared tolerances required')
    a=read_json(Path(left_dir)/'execution.json');b=read_json(Path(right_dir)/'execution.json')
    if a.get('input_sha256')!=b.get('input_sha256'):raise CVRSError('INCOMPARABLE','different input tensors')
    outputs_a=a.get('outputs');outputs_b=b.get('outputs')
    if not outputs_a or not outputs_b:raise ValueError('both jobs must have actual inference outputs')
    mapping=name_mapping or {k:k for k in outputs_a}
    if set(mapping)!=set(outputs_a) or set(mapping.values())!=set(outputs_b) or len(set(mapping.values()))!=len(mapping):raise ValueError('complete injective output-name mapping required')
    results={}
    for ka,kb in mapping.items():
        pa=safe_join(Path(left_dir),outputs_a[ka]['path']);pb=safe_join(Path(right_dir),outputs_b[kb]['path'])
        if file_digest(pa)!=outputs_a[ka]['sha256'] or file_digest(pb)!=outputs_b[kb]['sha256']:raise CVRSError('ARTIFACT_INTEGRITY','output bytes changed')
        x=np.load(pa,allow_pickle=False);y=np.load(pb,allow_pickle=False)
        if x.shape!=y.shape:results[ka]={'pass':False,'reason':'shape differs','left_shape':list(x.shape),'right_shape':list(y.shape)};continue
        d=np.abs(x.astype('float64')-y.astype('float64'));finite=np.isfinite(x).all() and np.isfinite(y).all()
        results[ka]={'pass':bool(finite and np.allclose(x,y,atol=atol,rtol=rtol,equal_nan=False)),'max_abs':float(d.max()) if d.size else 0.0,
            'mean_abs':float(d.mean()) if d.size else 0.0,'left_dtype':str(x.dtype),'right_dtype':str(y.dtype),'elements':int(x.size)}
    return {'kind':'TENSOR_BOUNDARY_FIDELITY','status':'WITHIN_TOLERANCE' if all(r['pass'] for r in results.values()) else 'DIFFERS',
        'atol':atol,'rtol':rtol,'outputs':results,'left_timing':a.get('timing'),'right_timing':b.get('timing'),
        'claim_scope':'matching inputs/outputs at this tensor boundary only; not detector AP or end-to-end service fidelity'}

def compare_detections(left,right,*,match_iou=0.5,box_atol=1e-3,score_atol=1e-4):
    from cvsubstrate.contracts.models import DetectionPrediction
    a={};b={}
    for destination,rows in [(a,left),(b,right)]:
        for raw in rows:
            row=DetectionPrediction.model_validate(raw)
            if row.sample_id in destination:raise ValueError('duplicate image')
            destination[row.sample_id]=row
    if set(a)!=set(b):raise CVRSError('INCOMPARABLE','different image universes')
    images={};all_good=True
    for sid,x in a.items():
        y=b[sid]
        if (x.width,x.height)!=(y.width,y.height):raise CVRSError('INCOMPARABLE','dimensions differ')
        pairs=sorted([(box_iou(bx,by),i,j) for i,bx in enumerate(x.boxes) for j,by in enumerate(y.boxes) if x.category_ids[i]==y.category_ids[j]],key=lambda q:(-q[0],q[1],q[2]))
        used_a=set();used_b=set();matched=[]
        for overlap,i,j in pairs:
            if overlap<match_iou or i in used_a or j in used_b:continue
            used_a.add(i);used_b.add(j);bd=max(abs(u-v) for u,v in zip(x.boxes[i],y.boxes[j]));sd=abs(x.scores[i]-y.scores[j]);matched.append({'left':i,'right':j,'iou':overlap,'box_max_abs':bd,'score_abs':sd,'within_tolerance':bd<=box_atol and sd<=score_atol})
        ua=sorted(set(range(len(x.boxes)))-used_a);ub=sorted(set(range(len(y.boxes)))-used_b)
        passed=not ua and not ub and all(z['within_tolerance'] for z in matched);all_good &= passed
        images[sid]={'pass':passed,'pairs':matched,'unmatched_left':ua,'unmatched_right':ub}
    return {'kind':'DETECTION_OUTPUT_FIDELITY','status':'WITHIN_TOLERANCE' if all_good else 'DIFFERS','images':images,
        'matching':'deterministic descending-IoU greedy one-to-one same-class matching; not an AP evaluator','match_iou':match_iou,'box_atol':box_atol,'score_atol':score_atol}

def compare_metrics(left,right):
    if left.get('comparison_digest')!=right.get('comparison_digest') or not left.get('comparison_digest'):raise CVRSError('INCOMPARABLE','metric comparison keys differ')
    differences={}
    def walk(a,b,prefix=''):
        if isinstance(a,dict) and isinstance(b,dict):
            for k in sorted(set(a)|set(b)):walk(a.get(k),b.get(k),prefix+'/'+k)
        elif isinstance(a,(int,float)) and not isinstance(a,bool) and isinstance(b,(int,float)) and not isinstance(b,bool):differences[prefix]={'left':a,'right':b,'delta':b-a}
        elif a!=b:differences[prefix]={'left':a,'right':b,'delta':None}
    walk(left.get('metrics',{}),right.get('metrics',{}));return {'kind':'METRIC_DELTA','comparison_digest':left['comparison_digest'],'differences':differences}
