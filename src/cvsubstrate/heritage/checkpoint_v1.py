"""Controller-side checkpoint diff/conversion; all tensor loading stays isolated."""
from pathlib import Path
from cvsubstrate.execution.services import invoke_service
from cvsubstrate.provenance.io import write_json
from cvsubstrate.provenance.artifact_set import seal_directory,assert_not_inside_sealed
from cvsubstrate.contracts.groundwork import CheckpointDescriptor

def diff_checkpoints(left,right,*,worker_python=None,timeout=180):
    a=CheckpointDescriptor.model_validate(left);b=CheckpointDescriptor.model_validate(right)
    return invoke_service('checkpoint',{'operation':'diff_v1','left':a.model_dump(mode='json'),'right':b.model_dump(mode='json')},worker_python=worker_python,timeout=timeout)

def transform_checkpoint(source,plan,output,*,worker_python=None,timeout=180):
    source=CheckpointDescriptor.model_validate(source);out=Path(output);assert_not_inside_sealed(out)
    if out.exists():raise ValueError('new checkpoint output directory required')
    out.mkdir(parents=True);write_json(out/'request.json',{'source':source.model_dump(mode='json'),'plan':plan})
    try:
        result=invoke_service('checkpoint',{'operation':'transform_v1','source':source.model_dump(mode='json'),'plan':plan,'output_dir':str(out.resolve())},worker_python=worker_python,timeout=timeout,log=out/'worker.log')
        seal_directory(out);return result
    except Exception as e:write_json(out/'failure.json',{'error':str(e),'status':'FAILED'});seal_directory(out);raise
