from pathlib import Path
from cvsubstrate.provenance.io import read_json, write_json
from cvsubstrate.execution.services import invoke_service

def stream_job(spec_path,output,*,worker_python=None,timeout=600,resume=False,max_tiles=None):
    spec=read_json(Path(spec_path));out=Path(output).resolve()
    return invoke_service('raster_stream',{'operation':'run','spec':spec,'output_dir':str(out),'resume':resume,'max_tiles':max_tiles},worker_python=worker_python,timeout=timeout,log=out.parent/(out.name+'-worker.log'))
