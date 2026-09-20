"""Checkpoint identity, isolated inventory, and explicit audited tensor conversion."""
from pathlib import Path
from cvsubstrate.contracts.groundwork import CheckpointDescriptor,CheckpointConversionSpec
from cvsubstrate.execution.services import invoke_service
from cvsubstrate.provenance.artifact_set import seal_directory,assert_not_inside_sealed
from cvsubstrate.provenance.io import write_json
from cvsubstrate.errors import CVRSError

def inspect_checkpoint(value,*,worker_python=None,timeout=180.0):
    spec=CheckpointDescriptor.model_validate(value)
    return invoke_service('checkpoint',{'operation':'inspect','spec':spec.model_dump(mode='json')},worker_python=worker_python,timeout=timeout)

def convert_checkpoint(value,output:Path,*,worker_python=None,timeout=180.0):
    spec=CheckpointConversionSpec.model_validate(value);out=Path(output);assert_not_inside_sealed(out)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','checkpoint conversion creates a new directory')
    out.mkdir(parents=True);write_json(out/'request.json',spec)
    try:
        result=invoke_service('checkpoint',{'operation':'convert','spec':spec.model_dump(mode='json'),'output_dir':str(out.resolve())},worker_python=worker_python,timeout=timeout,log=out/'worker.log')
        seal_directory(out);return result
    except Exception as exc:
        write_json(out/'failure.json',{'message':str(exc),'status':'FAILED'});seal_directory(out);raise
