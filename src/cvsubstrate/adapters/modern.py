"""Native modern-model jobs, separately declared from fixed-update CVRS training."""
from pathlib import Path
from cvsubstrate.contracts.models import ExperimentSpec,DetectionPrediction
from cvsubstrate.data.manifest import load_manifest,validate_manifest
from cvsubstrate.provenance.io import read_json,write_json,read_jsonl,digest,file_digest
from cvsubstrate.provenance.artifact_set import seal_directory,assert_not_inside_sealed
from cvsubstrate.execution.services import invoke_service
from cvsubstrate.evaluation.metrics import validate_predictions
from cvsubstrate.errors import CVRSError

def native_model_job(spec_path:Path,output:Path,*,operation='predict',worker_python=None,timeout=180.0):
    p=Path(spec_path).resolve();spec=ExperimentSpec.model_validate(read_json(p));backend=spec.adapter.name
    if backend not in {'ultralytics','rfdetr'}:raise ValueError('native modern job backend must be ultralytics or rfdetr')
    if spec.training is not None:raise ValueError('native epochs must live under adapter.config.native_training, not portable TrainingSpec')
    dataset=Path(spec.dataset);dataset=dataset if dataset.is_absolute() else p.parent/dataset;m=load_manifest(dataset)
    validate_manifest(m,dataset.parent,check_files=True)
    if digest(m)!=spec.dataset_sha256:raise CVRSError('DATASET_IDENTITY','manifest digest mismatch')
    if m.splits[spec.eval_split].role=='locked_test':raise CVRSError('PROTECTED_SPLIT','native job runner accepts development only')
    ck=spec.checkpoint.model_dump(mode='json') if spec.checkpoint else None
    if ck:
        cp=Path(ck['path']);cp=cp if cp.is_absolute() else p.parent/cp;ck['path']=str(cp.resolve())
        if file_digest(cp)!=ck['sha256']:raise CVRSError('CHECKPOINT_HASH','checkpoint changed')
    out=Path(output).resolve();assert_not_inside_sealed(out)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','new native job output required')
    out.mkdir(parents=True);write_json(out/'experiment.json',spec);write_json(out/'dataset_manifest.json',m)
    req={'operation':operation,'experiment':spec.model_dump(mode='json'),'manifest':m.model_dump(mode='json'),'checkpoint':ck,'data_root':str(dataset.parent.resolve()),'output_dir':str(out/'worker')}
    try:
        result=invoke_service(backend,req,worker_python=worker_python,timeout=timeout,log=out/'worker.log')
        if operation in {'train','predict'}:
            rows=[DetectionPrediction.model_validate(r) for r in read_jsonl(out/'worker'/'predictions.jsonl')];validate_predictions(m,spec.eval_split,rows)
        write_json(out/'result.json',result);seal_directory(out);return result
    except Exception as exc:write_json(out/'failure.json',{'status':'FAILED','message':str(exc)});seal_directory(out);raise
