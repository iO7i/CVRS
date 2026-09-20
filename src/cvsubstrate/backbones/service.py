from pathlib import Path
from cvsubstrate.contracts.groundwork import BackboneDescriptor
from cvsubstrate.execution.services import invoke_service
from cvsubstrate.provenance.io import file_digest,write_json
from cvsubstrate.provenance.artifact_set import seal_directory,assert_not_inside_sealed
from cvsubstrate.errors import CVRSError

def extract_features(spec,output:Path,*,worker_python=None,timeout=300):
    value=dict(spec);value['descriptor']=BackboneDescriptor.model_validate(spec['descriptor']).model_dump(mode='json')
    if file_digest(Path(value['input_array']))!=value['input_sha256']:raise CVRSError('DATA_INTEGRITY','input tensor digest mismatch')
    out=Path(output);assert_not_inside_sealed(out)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','choose a new feature output')
    out.mkdir(parents=True);write_json(out/'request.json',value)
    try:result=invoke_service('backbone',{'operation':'extract','spec':value,'output_dir':str(out.resolve())},worker_python=worker_python,timeout=timeout,log=out/'worker.log')
    except Exception as exc:
        write_json(out/'failure.json',{'code':getattr(exc,'code',type(exc).__name__),'message':str(exc),'status':'FAILED'});seal_directory(out);raise
    write_json(out/'result.json',result);seal_directory(out);return result
