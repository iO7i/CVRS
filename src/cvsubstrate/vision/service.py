from pathlib import Path
from cvsubstrate.contracts.frontier import VisionJob,GroundedPrediction,MaskPrediction
from cvsubstrate.execution.services import invoke_service
from cvsubstrate.provenance.io import read_json,write_json,read_jsonl,digest,file_digest
from cvsubstrate.provenance.artifact_set import seal_directory

def vision_job(spec,output,*,worker_python=None,timeout=600):
    job=VisionJob.model_validate(read_json(Path(spec)) if isinstance(spec,(str,Path)) else spec)
    out=Path(output).resolve()
    if out.exists():raise ValueError('new vision output directory required')
    out.mkdir(parents=True);write_json(out/'job.json',job)
    try:
        result=invoke_service('vision',{'operation':job.operation,'job':job.model_dump(mode='json'),'output_dir':str(out/'worker')},worker_python=worker_python,timeout=timeout,log=out/'worker.log')
        if job.operation=='predict':
            rows=read_jsonl(out/'worker'/'predictions.jsonl')
            expected_task='grounded_detection' if job.backend in {'hf_grounding_dino','yolo_world'} else 'instance_masks'
            if result.get('task')!=expected_task or result.get('backend')!=job.backend or result.get('status')!='EXECUTED':raise ValueError('worker response does not match declared backend/task')
            cls=GroundedPrediction if expected_task=='grounded_detection' else MaskPrediction
            parsed=[cls.model_validate(r) for r in rows]
            ids=[r.sample_id for r in parsed]
            if len(ids)!=len(set(ids)) or set(ids)!={i['id'] for i in job.images}:raise ValueError('prediction image universe differs')
            prompts={p.id:digest(p) for p in job.prompts}
            native_hashes={file_digest(p) for p in (out/'worker').glob('*-native.*') if p.is_file() and not p.is_symlink()}
            images={i['id']:i for i in job.images}
            for row in parsed:
                if row.native_output_sha256 not in native_hashes:raise ValueError('native prediction artifact absent or hash changed')
                image=images[row.sample_id]
                if 'width' in image and image['width']!=row.width:raise ValueError('prediction width differs from declared image')
                if 'height' in image and image['height']!=row.height:raise ValueError('prediction height differs from declared image')
                used=[row.prompt] if isinstance(row,GroundedPrediction) else row.prompts
                for p in used:
                    if prompts.get(p.id)!=digest(p):raise ValueError('worker changed a prompt')
        write_json(out/'result.json',result);seal_directory(out);return result
    except Exception as exc:
        write_json(out/'failure.json',{'status':'FAILED','message':str(exc)});seal_directory(out);raise
