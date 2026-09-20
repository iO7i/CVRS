"""Loss-aware HBB dataset interchange; semantic maps are not instance masks."""
from pathlib import Path
from cvsubstrate.contracts.models import DatasetManifest,DetectionPrediction
from cvsubstrate.provenance.io import digest,read_jsonl,write_json,safe_join

def detection_bundle(manifest,predictions,root):
    m=DatasetManifest.model_validate(manifest);byid: dict[str, DetectionPrediction] = {}
    for v in predictions:
        prediction=DetectionPrediction.model_validate(v)
        if prediction.sample_id in byid:raise ValueError('duplicate prediction sample')
        byid[prediction.sample_id]=prediction
    sample_ids={s.id for s in m.samples}
    if set(byid)-sample_ids:raise ValueError('predictions reference unknown images')
    cats={c.id for c in m.categories};rows=[]
    for s in m.samples:
        current=byid.get(s.id)
        if current and ((current.width,current.height)!=(s.width,s.height) or set(current.category_ids)-cats):raise ValueError('prediction geometry/taxonomy mismatch')
        rows.append({'id':s.id,'image':str(safe_join(Path(root),s.image)),'image_sha256':s.sha256,'width':s.width,'height':s.height,
                     'ground_truth':[b.model_dump(mode='json') for b in s.boxes],
                     'prediction':current.model_dump(mode='json') if current else None,
                     'metadata':{'domain':s.domain,'source_kind':s.source_kind,'lineage_group':s.lineage_group}})
    return {'schema_version':'1.0','task':'hbb_detection','dataset_digest':digest(m),'categories':[c.model_dump(mode='json') for c in m.categories],
            'samples':rows,'licenses':m.licenses.model_dump(mode='json'),'losses':[],
            'scope':'HBB with exact original-pixel coordinates. Other task bridges require their own representation.'}

def supervision_roundtrip(bundle):
    """In-process public API for users already running Supervision."""
    import numpy as np,supervision as sv
    output=[]
    for s in bundle['samples']:
        p=s.get('prediction')
        if p is None:continue
        d=sv.Detections(xyxy=np.asarray(p['boxes'],dtype=float).reshape(-1,4),confidence=np.asarray(p['scores'],dtype=float),
                        class_id=np.asarray(p['category_ids'],dtype=int))
        output.append({'sample_id':s['id'],'detections':d,'cvrs_provenance':{'dataset_digest':bundle['dataset_digest'],'width':s['width'],'height':s['height']}})
    return output

def from_supervision(detections,*,sample_id,width,height):
    if getattr(detections,'mask',None) is not None:raise ValueError('use a mask-aware bridge; do not silently discard masks')
    if detections.confidence is None or detections.class_id is None:raise ValueError('scores and category mapping must be explicit')
    return DetectionPrediction(sample_id=sample_id,width=width,height=height,boxes=detections.xyxy.tolist(),scores=detections.confidence.tolist(),category_ids=detections.class_id.tolist())
