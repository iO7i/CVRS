"""Oriented native jobs with lossless corner canonicalization and owned evidence."""
from pathlib import Path
from cvsubstrate.contracts.research import OrientedDataset,OrientedPrediction
from cvsubstrate.provenance.io import read_json,read_jsonl,write_json,write_jsonl,digest
from cvsubstrate.provenance.artifact_set import assert_not_inside_sealed,seal_directory
from cvsubstrate.execution.services import invoke_service
from cvsubstrate.geometry.polygons import canonical_polygon
from cvsubstrate.errors import CVRSError

def run_oriented_job(path,output,*,operation='predict',worker_python=None,timeout=300):
    path=Path(path).resolve();spec=read_json(path);dp=(path.parent/spec['dataset']).resolve();m=OrientedDataset.model_validate(read_json(dp))
    if digest(m)!=spec['dataset_sha256']:raise CVRSError('DATASET_IDENTITY','oriented manifest digest differs')
    spec['checkpoint']=str((path.parent/spec['checkpoint']).resolve())
    req={'operation':operation,'spec':spec,'dataset':m.model_dump(mode='json'),'data_root':str(dp.parent)}
    if operation=='train':
        tp=(path.parent/spec['training_dataset']).resolve();tm=OrientedDataset.model_validate(read_json(tp))
        if digest(tm)!=spec['training_dataset_sha256']:raise CVRSError('DATASET_IDENTITY','oriented train manifest differs')
        if set(s.sha256 for s in m.samples)&set(s.sha256 for s in tm.samples):raise CVRSError('SPLIT_LEAKAGE','identical train/dev images')
        if {s.lineage_group for s in m.samples if s.lineage_group}&{s.lineage_group for s in tm.samples if s.lineage_group}:raise CVRSError('LINEAGE_LEAKAGE','same scene in train/dev')
        req.update(training_dataset=tm.model_dump(mode='json'),training_root=str(tp.parent))
    out=Path(output).resolve();assert_not_inside_sealed(out)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','new oriented output required')
    out.mkdir(parents=True);write_json(out/'request.json',spec);write_json(out/'dataset.json',m);req['output_dir']=str(out/'worker')
    try:
        result=invoke_service('ultralytics_obb',req,worker_python=worker_python,timeout=timeout,log=out/'worker.log')
        raw=read_jsonl(out/'worker/native-predictions.jsonl');rows=[]
        if len(raw)!=len(m.samples) or set(x['sample_id'] for x in raw)!=set(s.id for s in m.samples):raise CVRSError('IMAGE_UNIVERSE','oriented outputs differ from declared data')
        for x in raw:rows.append(OrientedPrediction(sample_id=x['sample_id'],polygons=[canonical_polygon(p) for p in x['polygons']],scores=x['scores'],category_ids=x['category_ids']))
        write_jsonl(out/'predictions.jsonl',[x.model_dump(mode='json') for x in rows])
        result['conversion']={'native_count':sum(len(x['scores']) for x in raw),'canonical_count':sum(len(x.scores) for x in rows),'transformation':'corner order only; no fitted rectangle or coordinate clipping'}
        write_json(out/'result.json',result);seal_directory(out);return result
    except Exception as exc:
        write_json(out/'failure.json',{'status':'FAILED','code':getattr(exc,'code',type(exc).__name__),'message':str(exc)});seal_directory(out);raise
