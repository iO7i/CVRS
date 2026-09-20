"""Task-scoped native exchanges, decoding, and tracking evidence exports."""
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
from cvsubstrate.adoption.common import execution_tree, output_tree
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import read_json, write_json, file_digest, digest
from cvsubstrate.provenance.artifact_set import verify_directory
from cvsubstrate.execution.process import run_command
from cvsubstrate.product.interchange import RichInterchange, exchange, audit_roundtrip


def native_exchange(value: dict, target: str, destination: Path, *, worker_python: str | None = None,
                    trust: bool = False, timeout: float = 600) -> dict:
    """Export and read back a genuine SDK representation in a selected worker."""
    if not trust:
        raise CVRSError('TRUST_REQUIRED','explicit trust is required for optional native SDKs')
    source = RichInterchange.model_validate(value)
    script = Path(__file__).resolve().parents[1]/'worker_shims'/'rich_exchange_worker.py'
    native = exchange(source.model_dump(mode='json'), target, 'export')
    with execution_tree(destination) as out:
        write_json(out/'canonical-source.json', source)
        write_json(out/'native-input.json', native)
        req = {'protocol_version':'1.0','output_dir':str(out),
               'payload':{'trust_code':True,'target':target,'input':str(out/'native-input.json'),
                          'input_sha256':file_digest(out/'native-input.json')}}
        with tempfile.TemporaryDirectory() as td:
            q=Path(td);write_json(q/'request.json',req)
            run_command([worker_python or sys.executable,str(script),'--request',str(q/'request.json'),'--response',str(q/'response.json')],
                        timeout,log=out/'native.log')
            response=read_json(q/'response.json')
        if response.get('status')!='SUCCEEDED':
            error=response.get('error',{});raise CVRSError(error.get('code','NATIVE_EXCHANGE_FAILED'),error.get('message','native SDK failed'))
        restored = exchange(read_json(out/'native-view.json'),target,'import')
        audit = audit_roundtrip(source,restored)
        write_json(out/'canonical-restored.json',restored)
        write_json(out/'conversion-audit.json',audit)
        if audit['status']!='PRESERVED':
            raise CVRSError('LOSSY_EXCHANGE','native output round trip changed task semantics; inspect audit')
        write_json(out/'receipt.json',{'target':target,'worker_sha256':file_digest(script),
            'source_digest':digest(source),'result':response['result'],'audit':audit})
    return {'status':'SUCCEEDED','output':str(destination),'audit':audit,'integrity':verify_directory(destination)}


def import_fiftyone_dataset(name: str, destination: Path, *, worker_python: str | None=None, trust=False):
    if not trust or not name.strip():
        raise CVRSError('TRUST_REQUIRED','name an existing local FiftyOne dataset and authorize the SDK')
    script=Path(__file__).resolve().parents[1]/'worker_shims'/'rich_exchange_worker.py'
    with execution_tree(destination) as out:
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);write_json(p/'request.json',{'protocol_version':'1.0','output_dir':str(out),
                'payload':{'target':'fiftyone','dataset_name':name,'trust_code':True}})
            run_command([worker_python or sys.executable,str(script),'--request',str(p/'request.json'),'--response',str(p/'response.json')],600,log=out/'worker.log')
            response=read_json(p/'response.json')
        if response.get('status')!='SUCCEEDED':raise CVRSError('EXCHANGE_IMPORT_FAILED',str(response.get('error')))
        result=exchange(read_json(out/'native-view.json'),'fiftyone','import')
        write_json(out/'canonical.json',result)
        write_json(out/'receipt.json',{'source_dataset':name,'result':response['result'],'canonical_digest':digest(result),
                                     'meaning':'Current native contents, not assumed identical to the initial export.'})
    return {'status':'IMPORTED','output':str(destination),'integrity':verify_directory(destination)}


def decode_arrays(path: Path, spec: dict, destination: Path) -> dict:
    """Decode a declared TerraTorch/custom NPZ boundary without heuristic guessing.

    Supported: NHW semantic maps, NCHW class logits (explicit argmax), and
    detection arrays boxes[N,K,4], scores[N,K], labels[N,K], optional counts[N].
    All arrays are loaded with allow_pickle=False and a byte budget.
    """
    import numpy as np
    import zipfile
    from cvsubstrate.contracts.models import DetectionPrediction
    from cvsubstrate.adoption.contracts import SemanticLabelMap
    from cvsubstrate.provenance.io import write_jsonl
    if file_digest(path)!=spec['sha256']:
        raise CVRSError('DECODER_INPUT_CHANGED','native array identity differs')
    budget=spec.get('max_bytes',256*1024*1024)
    with zipfile.ZipFile(path) as z:
        if sum(i.file_size for i in z.infolist())>budget:
            raise CVRSError('DECODE_BUDGET','decompressed arrays exceed declared byte budget')
    metadata=spec['samples'];task=spec['task'];mapping={int(k):int(v) for k,v in spec['category_mapping'].items()}
    rows=[];semantic_arrays=[]
    if len({s["id"] for s in metadata}) != len(metadata):raise ValueError("duplicate sample identity")
    with np.load(path,allow_pickle=False) as data:
        if task=='semantic_segmentation':
            a=data[spec['array']]
            if spec['layout']=='NCHW':
                if a.ndim!=4 or not np.isfinite(a).all():raise ValueError('expected finite NCHW logits')
                a=a.argmax(axis=1)
            elif spec['layout']!='NHW':raise ValueError('declare NHW labels or NCHW logits')
            if a.ndim!=3 or len(a)!=len(metadata):raise ValueError('semantic sample/array shape mismatch')
            for index,sample in enumerate(metadata):
                label=a[index]
                if label.shape!=(sample['height'],sample['width']):raise ValueError('decoder never resizes labels silently')
                if not np.isfinite(label).all() or not np.equal(label,np.floor(label)).all():raise ValueError('labels must be finite integers')
                ignore=spec.get('ignore_index',255)
                unknown=set(int(v) for v in np.unique(label))-set(mapping)-{ignore}
                if unknown:raise ValueError('unmapped semantic categories: '+str(sorted(unknown)))
                converted=np.full_like(label,ignore,dtype=np.int64)
                for old,new in mapping.items():converted[label==old]=new
                semantic_arrays.append((sample,converted,ignore))
        elif task=='hbb_detection':
            boxes,scores,labels=data[spec.get('boxes','boxes')],data[spec.get('scores','scores')],data[spec.get('labels','labels')]
            if boxes.ndim!=3 or boxes.shape[2]!=4 or scores.shape!=boxes.shape[:2] or labels.shape!=scores.shape or len(boxes)!=len(metadata):
                raise ValueError('declared detection array shapes disagree')
            counts=data[spec['counts']] if spec.get('counts') else [boxes.shape[1]]*len(boxes)
            for i,s in enumerate(metadata):
                if len(counts)!=len(metadata) or not np.isfinite(counts[i]) or int(counts[i])!=counts[i]:raise ValueError('counts must match samples and be finite integers')
                count=int(counts[i])
                if count<0 or count>boxes.shape[1]:raise ValueError('invalid native detection count')
                b=boxes[i,:count].astype(float)
                if spec.get('box_format','xyxy')=='cxcywh':
                    cx,cy,w,h=[b[:,j].copy() for j in range(4)]
                    b=np.stack([cx-w/2,cy-h/2,cx+w/2,cy+h/2],axis=1)
                elif spec.get('box_format','xyxy')!='xyxy':raise ValueError('unsupported explicit box layout')
                if spec.get('normalized',False):b*=np.array([s['width'],s['height'],s['width'],s['height']])
                categories=[]
                for v in labels[i,:count]:
                    if int(v)!=v or int(v) not in mapping:raise ValueError('unmapped or noninteger detection category')
                    categories.append(mapping[int(v)])
                rows.append(DetectionPrediction(sample_id=s['id'],width=s['width'],height=s['height'],
                    boxes=b.tolist(),scores=scores[i,:count].tolist(),category_ids=categories).model_dump(mode='json'))
        else:raise CVRSError('DECODER_UNSUPPORTED','select a semantic-map or HBB decoder; other tasks need a registered explicit boundary')
    with output_tree(destination) as out:
        for index,(sample,array,ignore) in enumerate(semantic_arrays):
            rel='labels/'+str(index)+'.npy';p=out/rel;p.parent.mkdir(exist_ok=True)
            np.save(p,array,allow_pickle=False)
            rows.append(SemanticLabelMap(sample_id=sample['id'],width=sample['width'],height=sample['height'],
                labels=rel,sha256=file_digest(p),category_mapping={str(n):n for n in sorted(set(mapping.values()))},
                ignore_index=ignore,reduce_zero_label=False).model_dump(mode='json'))
        write_json(out/'decoder.json',spec);write_jsonl(out/'predictions.jsonl',rows)
        write_json(out/'receipt.json',{'source_sha256':file_digest(path),'decoder_digest':digest(spec),
            'samples':len(rows),'task':task,'geometry':'original_image','native_execution':'NOT_INFERRED'})
    return {'status':'DECODED','samples':len(rows),'output':str(destination)}


def tracking_handoff(run: Path, destination: Path, *, approved_files: list[str] | None=None) -> dict:
    """Retain CVRS evidence semantics when exporting into W&B/MLflow.

    No upload occurs. Media/weights are excluded unless individually approved.
    """
    from cvsubstrate.provenance.bundle import verify_bundle
    from cvsubstrate.provenance.io import safe_join
    verification=verify_bundle(run)
    if verification['status']!='VERIFIED':raise CVRSError('INVALID_EVIDENCE','source run must verify')
    if (run/'run.json').is_file():manifest=read_json(run/'run.json')
    else:manifest={}
    metrics=read_json(run/'metrics.json') if (run/'metrics.json').exists() else {}
    identities={}
    for key,filename in [('experiment','experiment.json'),('dataset','dataset_manifest.json'),('environment','environment.json'),('artifacts','artifacts.json')]:
        if (run/filename).is_file():identities[key+'_sha256']=file_digest(run/filename)
    copied=[]
    with output_tree(destination) as out:
        import shutil
        for rel in approved_files or []:
            src=safe_join(run,rel)
            if not src.is_file() or src.is_symlink():raise ValueError('approve existing regular files only')
            target=out/'approved'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,target)
            copied.append({'path':'approved/'+rel,'sha256':file_digest(target)})
        write_json(out/'tracking.json',{'parameters':{'cvrs':identities},'metrics':metrics,'identities':identities,
                                      'run_id':manifest.get('run_id'), 'reproduction':'NOT_INFERRED',
                                      'approved_files':copied,'external_transfer':'NOT_AUTHORIZED_BY_HANDOFF'})
        write_json(out/'receipt.json',{'source_integrity':verification,'identities':identities,'copied_files':copied,'uploaded':False})
    return {'status':'PREPARED_OFFLINE','output':str(destination),'files':len(copied)}
