"""Generic explicitly named standalone-worker invocation; no heavyweight imports."""
from pathlib import Path
import sys,tempfile
from cvsubstrate.execution.process import run_command
from cvsubstrate.provenance.io import read_json,write_json,file_digest
from cvsubstrate.errors import CVRSError

WORKERS={'native_campaign':'native_campaign_worker.py','task_stream':'task_stream_worker.py','quantization':'quantization_worker.py','detector_deploy':'detector_deploy_worker.py','vision':'vision_worker.py','raster_stream':'stream_worker.py','ultralytics_obb':'obb_worker.py','plugin':'plugin_worker.py','checkpoint':'checkpoint_worker.py','evaluator':'coco_reference_worker.py',
    'ultralytics':'modern_detector_worker.py','rfdetr':'modern_detector_worker.py',
    'backbone':'backbone_worker.py','deployment':'deployment_worker.py','unsafe_import':'unsafe_import_worker.py'}

def invoke_service(name,request,*,worker_python=None,timeout=180.0,log=None):
    if name not in WORKERS:raise CVRSError('WORKER_UNKNOWN',name)
    script=Path(__file__).resolve().parents[1]/'worker_shims'/WORKERS[name]
    if not script.is_file():raise CVRSError('WORKER_MISSING',WORKERS[name])
    before=file_digest(script)
    with tempfile.TemporaryDirectory(prefix='cvrs-service-') as td:
        p=Path(td);payload={**request,'protocol_version':'1.0','service':name}
        write_json(p/'request.json',payload)
        run_command([worker_python or sys.executable,str(script),'--request',str(p/'request.json'),'--response',str(p/'response.json')],timeout,log=log)
        if not (p/'response.json').is_file():raise CVRSError('WORKER_RESPONSE','response missing')
        result=read_json(p/'response.json')
    if file_digest(script)!=before:raise CVRSError('WORKER_CHANGED','script changed during execution')
    if result.get('protocol_version')!='1.0':raise CVRSError('PROTOCOL_VERSION','service protocol mismatch')
    if result.get('status')!='SUCCEEDED':
        error=result.get('error') or {};raise CVRSError(error.get('code','WORKER_FAILED'),error.get('message','worker failed'))
    if not isinstance(result.get('result'),dict):raise CVRSError('WORKER_RESPONSE','result must be a mapping')
    return result['result']
