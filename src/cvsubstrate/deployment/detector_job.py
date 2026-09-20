"""A detector-specific ORT deployment job: preprocess -> runtime -> decode -> evidence."""
from pathlib import Path
from cvsubstrate.execution.services import invoke_service
from cvsubstrate.provenance.io import read_json,write_json
from cvsubstrate.provenance.artifact_set import seal_directory

def run_detector_deployment(spec,output,*,worker_python=None,timeout=600):
    value=read_json(Path(spec)) if isinstance(spec,(str,Path)) else spec
    out=Path(output).resolve()
    if out.exists():raise ValueError('new deployment output required')
    out.mkdir(parents=True);write_json(out/'spec.json',value)
    try:
        result=invoke_service('detector_deploy',{'operation':'infer','spec':value,'output_dir':str(out/'worker')},worker_python=worker_python,timeout=timeout,log=out/'worker.log')
        write_json(out/'result.json',result);seal_directory(out);return result
    except Exception as exc:
        write_json(out/'failure.json',{'status':'FAILED','message':str(exc)});seal_directory(out);raise
