"""Explicit postprocessed-tensor to canonical HBB mapping.

This is not a model-specific logits decoder. Raw DETR logits/YOLO heads need a
native decoder inside export or a trusted external adapter. Never guess shapes,
class indexing, NMS, coordinate normalization, or background conventions.
"""
from pathlib import Path
from cvsubstrate.contracts.models import DatasetManifest,DetectionPrediction
from cvsubstrate.provenance.io import read_json,write_json,write_jsonl,file_digest,digest,safe_join
from cvsubstrate.provenance.artifact_set import verify_directory,seal_directory
from cvsubstrate.errors import CVRSError

def decode_outputs(run:Path,spec:dict,output:Path):
    import numpy as np
    run=Path(run);out=Path(output)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','decoder output must be new')
    if verify_directory(run)['status']!='VERIFIED':raise CVRSError('ARTIFACT_INTEGRITY','deployment output is not verified')
    result=read_json(run/'result.json');manifest=DatasetManifest.model_validate(spec['dataset'])
    if spec.get('dataset_sha256')!=digest(manifest):raise CVRSError('DATASET_DIGEST','explicit dataset identity required')
    if spec['coordinate_format'] not in {'xyxy_pixels','xyxy_normalized','cxcywh_normalized'}:raise ValueError('unsupported tensor coordinate format')
    names=spec['tensor_names'];arrays={}
    for field,key in names.items():
        meta=result['outputs'][key];path=safe_join(run,meta['path'])
        if file_digest(path)!=meta['sha256']:raise CVRSError('ARTIFACT_INTEGRITY','tensor changed')
        arrays[field]=np.load(path,allow_pickle=False)
    if not {'boxes','scores','labels'}<=set(arrays):raise ValueError('box, score and label tensors required')
    samples={s.id:s for s in manifest.samples};batch=spec.get('batch_dimension',False);ids=spec['sample_ids']
    if len(ids)!=len(set(ids)) or not set(ids)<=set(samples):raise ValueError('unique known image identities required')
    if not batch and len(ids)!=1:raise ValueError('unbatched tensors represent exactly one image')
    if batch and any(len(a)!=len(ids) for a in arrays.values()):raise ValueError('tensor batch count mismatch')
    mapping={int(k):int(v) for k,v in spec['category_map'].items()};known={c.id for c in manifest.categories}
    if len(set(mapping.values()))!=len(mapping) or not set(mapping.values())<=known:raise ValueError('explicit injective category mapping required')
    rows=[];audit=[]
    for index,sid in enumerate(ids):
        sample=samples[sid];values={k:a[index] if batch else a for k,a in arrays.items()}
        boxes=values['boxes'];scores=values['scores'];labels=values['labels']
        if boxes.ndim!=2 or boxes.shape[1]!=4 or scores.ndim!=1 or labels.ndim!=1 or len(boxes)!=len(scores) or len(scores)!=len(labels):raise ValueError('expected boxes[N,4], scores[N], labels[N]')
        total=len(boxes);n=total
        if 'count' in values:
            count=np.asarray(values['count'])
            if count.size!=1 or not float(count.item()).is_integer():raise ValueError('valid-count must be one integer')
            n=int(count.item())
            if not 0<=n<=total:raise ValueError('valid-count outside padded tensor')
        boxes=boxes[:n].astype(float);scores=scores[:n];labels=labels[:n]
        if not np.equal(labels,np.floor(labels)).all():raise ValueError('class IDs must be integral, not logits')
        if spec['coordinate_format']=='cxcywh_normalized':
            cx,cy,w,h=boxes.T;boxes=np.stack([cx-w/2,cy-h/2,cx+w/2,cy+h/2],axis=1)
        if spec['coordinate_format']!='xyxy_pixels':boxes*=np.array([sample.width,sample.height,sample.width,sample.height])
        if not set(int(x) for x in labels)<=set(mapping):raise CVRSError('CATEGORY_MAP','unmapped output class; no silent filtering')
        rows.append(DetectionPrediction(sample_id=sid,width=sample.width,height=sample.height,boxes=boxes.tolist(),scores=scores.tolist(),category_ids=[mapping[int(x)] for x in labels],
            score_semantics=spec['score_semantics'],transform_provenance={'decoder_spec_digest':digest(spec),'tensor_format':spec['coordinate_format'],'native_postprocessed_tensors':True}))
        audit.append({'sample_id':sid,'tensor_rows':total,'valid_rows':n,'declared_padding_rows':total-n,'filtered_valid_rows':0})
    out.mkdir(parents=True);write_jsonl(out/'predictions.jsonl',rows);report={'status':'DECODED','dataset_digest':digest(manifest),'spec_digest':digest(spec),'images':len(rows),'audit':audit,'native_metric_parity':'NOT_ESTABLISHED'}
    write_json(out/'decoder.json',spec);write_json(out/'report.json',report);seal_directory(out);return report
