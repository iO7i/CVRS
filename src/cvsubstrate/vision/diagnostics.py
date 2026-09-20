"""Declared mask and cross-paradigm diagnostics, distinct from reference AP."""
from cvsubstrate.contracts.frontier import MaskPrediction,MaskAnnotation
from cvsubstrate.vision.masks import mask_area,mask_iou,decode_mask
from cvsubstrate.provenance.io import digest

def _boundary(mask,max_pixels):
    import numpy as np
    a=decode_mask(mask,max_pixels);pad=np.pad(a,1,constant_values=False)
    interior=pad[1:-1,1:-1]&pad[:-2,1:-1]&pad[2:,1:-1]&pad[1:-1,:-2]&pad[1:-1,2:]
    return a&~interior

def mask_diagnostics(dataset,predictions,protocol):
    gt=[MaskAnnotation.model_validate(x) for x in dataset['annotations']];ps=[MaskPrediction.model_validate(x) for x in predictions]
    images={x['id'] for x in dataset['images']}
    if {p.sample_id for p in ps}!=images or len(ps)!=len(images):raise ValueError('mask image universe mismatch')
    pred={p.sample_id:p for p in ps};records=[];threshold=float(protocol.get('iou_threshold',.5));budget=int(protocol.get('max_boundary_pixels',16777216))
    if not 0<threshold<=1:raise ValueError('invalid IoU threshold')
    used=set()
    for a in gt:
        if a.ignore or a.iscrowd:continue
        candidates=[(mask_iou(a.mask,i.mask),i) for i in pred[a.sample_id].instances if i.category_id==a.category_id and (a.sample_id,i.id) not in used]
        overlap,item=max(candidates,key=lambda x:x[0]) if candidates else (0,None)
        boundary=None
        if item is not None and overlap>=threshold:
            used.add((a.sample_id,item.id))
            if protocol.get('boundary',False):
                aa=_boundary(a.mask,budget);bb=_boundary(item.mask,budget);den=int(aa.sum()+bb.sum());boundary=2*int((aa&bb).sum())/den if den else 1.0
        records.append({'sample_id':a.sample_id,'object_id':a.instance_id,'area_px':mask_area(a.mask),'iou':overlap,'matched':item is not None and overlap>=threshold,'boundary_f1_exact_pixels':boundary,'prompt_id':None if item is None else item.prompt_id})
    receipt=None
    if protocol.get('slice'):
        from cvsubstrate.analysis.metric_plugins import slice_receipt
        receipt=slice_receipt(records,protocol['slice']);ids={(x['sample_id'],x['object_id']) for x in receipt['selected']};records=[x for x in records if (x['sample_id'],x['object_id']) in ids]
    return {'metric':'cvrs-mask-instance-diagnostics/1.0','official_AP':False,'matching':'GT-order greedy same-category unused prediction; not COCO scoring','objects':records,'support':len(records),'mean_matched_iou':sum(x['iou'] for x in records if x['matched'])/sum(x['matched'] for x in records) if any(x['matched'] for x in records) else None,'mean_best_candidate_iou':sum(x['iou'] for x in records)/len(records) if records else None,'recall':sum(x['matched'] for x in records)/len(records) if records else None,'slice_receipt':receipt,'protocol_sha256':digest(protocol)}

def compare_paradigms(left,right):
    fields=('task','dataset_sha256','split','protocol_sha256','taxonomy_sha256','prompt_set_sha256','oracle_conditioned','preprocessing_sha256','model_assets_sha256')
    details={k:('UNKNOWN' if k not in left or k not in right else 'MATCH' if left[k]==right[k] else 'DIFFERENT') for k in fields}
    required=('task','dataset_sha256','split','protocol_sha256','taxonomy_sha256','prompt_set_sha256','oracle_conditioned')
    status='COMPARABLE_UNDER_DECLARED_PROTOCOL' if all(details[x]=='MATCH' for x in required) else 'INCOMPARABLE' if details['task']=='DIFFERENT' else 'DESCRIPTIVE_ONLY'
    return {'comparability':status,'fields':details,'homogeneous_ranking_allowed':status=='COMPARABLE_UNDER_DECLARED_PROTOCOL','training_fairness':'NOT_ESTABLISHED','inputs_sha256':digest([left,right])}
