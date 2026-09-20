from pathlib import Path
from cvsubstrate.contracts.groundwork import DeploymentSpec
from cvsubstrate.execution.services import invoke_service
from cvsubstrate.provenance.io import file_digest,write_json
from cvsubstrate.provenance.artifact_set import seal_directory,assert_not_inside_sealed
from cvsubstrate.errors import CVRSError

def execute_deployment(spec,output:Path,*,operation='infer',worker_python=None,timeout=300):
    s=DeploymentSpec.model_validate(spec);out=Path(output);assert_not_inside_sealed(out)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','new deployment output required')
    if file_digest(Path(s.model_path))!=s.model_sha256:raise CVRSError('CHECKPOINT_MISMATCH','model content differs')
    inputs={k:file_digest(Path(p)) for k,p in s.input_arrays.items()};out.mkdir(parents=True)
    request={'operation':operation,'spec':s.model_dump(mode='json'),'input_sha256':inputs,'output_dir':str(out.resolve())};write_json(out/'request.json',request)
    try:result=invoke_service('deployment',request,worker_python=worker_python,timeout=timeout,log=out/'worker.log')
    except Exception as exc:
        write_json(out/'failure.json',{'status':'FAILED','code':getattr(exc,'code',type(exc).__name__),'message':str(exc)});seal_directory(out);raise
    write_json(out/'result.json',result);seal_directory(out);return result
