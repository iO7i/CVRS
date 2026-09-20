"""Isolated ecosystem calls with explicit network and credential opt-in."""
from pathlib import Path
from typing import Any
import sys,tempfile
from cvsubstrate.adoption.contracts import BridgeJob
from cvsubstrate.adoption.common import execution_tree
from cvsubstrate.provenance.io import write_json,read_json,file_digest,digest
from cvsubstrate.provenance.artifact_set import verify_directory
from cvsubstrate.execution.process import run_command
from cvsubstrate.errors import CVRSError
from cvsubstrate.security import sanitize

BRIDGES: dict[str, dict[str, Any]]={
 'fiftyone':{'operations':['export','import'],'module':'fiftyone','network_default':False},
 'supervision':{'operations':['export','import'],'module':'supervision','network_default':False},
 'wandb':{'operations':['export','import'],'module':'wandb','network_default':False},
 'mlflow':{'operations':['export','import'],'module':'mlflow','network_default':False},
 'dvc':{'operations':['inspect','fetch'],'module':'dvc','network_default':False},
 'openml':{'operations':['inspect','import'],'module':'openml','network_default':False},
 'torchgeo':{'operations':['inspect','export'],'module':'torchgeo','network_default':False},
 'terratorch':{'operations':['train','predict'],'module':'terratorch','network_default':False},
 'timm':{'operations':['inspect'],'module':'timm','network_default':False},
 'hf':{'operations':['inspect','lock'],'module':'huggingface_hub','network_default':False},
}

def bridge_catalogue():
    return {k:{**v,'implementation':'NATIVE_API_PATH','execution_verified':False,
                 'note':'Inspect release evidence for actual execution; availability is not certification.'} for k,v in BRIDGES.items()}

def run_bridge(value):
    job=BridgeJob.model_validate(value)
    if job.bridge not in BRIDGES or job.operation not in BRIDGES[job.bridge]['operations']:
        raise CVRSError('UNSUPPORTED_CAPABILITY','unsupported bridge operation')
    if not job.trust_code:raise CVRSError('TRUST_REQUIRED','bridge SDKs and configured projects execute native code')
    if job.allow_network and not job.payload.get('acknowledge_external_transfer'):
        raise CVRSError('TRANSFER_ACK_REQUIRED','explicitly acknowledge any external metadata/artifact transfer')
    script=Path(__file__).resolve().parents[1]/'worker_shims'/'ecosystem_worker.py'
    result=None
    with execution_tree(job.output_dir) as out:
        req={'protocol_version':'1.0','bridge':job.bridge,'operation':job.operation,'payload':job.payload,
             'allow_network':job.allow_network,'output_dir':str(out)}
        with tempfile.TemporaryDirectory(prefix='cvrs-bridge-request-') as td:
            p=Path(td);write_json(p/'request.json',req)
            allowed={'wandb':['WANDB_API_KEY'],'mlflow':['MLFLOW_TRACKING_TOKEN','MLFLOW_TRACKING_USERNAME','MLFLOW_TRACKING_PASSWORD'],
                     'hf':['HF_TOKEN'],'openml':['OPENML_API_KEY']}.get(job.bridge,[]) if job.allow_network else []
            run_command([job.worker_python or sys.executable,str(script),'--request',str(p/'request.json'),'--response',str(p/'response.json')],
                        job.timeout_seconds,log=out/'worker.log',pass_env=allowed)
            response=read_json(p/'response.json')
        if response.get('status')!='SUCCEEDED':
            err=response.get('error',{});raise CVRSError(err.get('code','BRIDGE_FAILED'),err.get('message','native bridge failed'))
        result=response['result']
        write_json(out/'receipt.json',{'bridge':job.bridge,'operation':job.operation,'request_digest':digest(sanitize(job.model_dump(mode='json'))),
            'worker_sha256':file_digest(script),'result':sanitize(result),'network_enabled':job.allow_network,'native_execution':'COMPLETED'})
    return {'status':'SUCCEEDED','output':str(job.output_dir),'result':result,'integrity':verify_directory(Path(job.output_dir))}
