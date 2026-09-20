"""Native export recipes; MM uses trusted MMDeploy instead of invented symbolic ops."""
from pathlib import Path
import sys,os
from cvsubstrate.provenance.io import file_digest,write_json
from cvsubstrate.provenance.artifact_set import seal_directory
from cvsubstrate.execution.process import run_command

def export_mmdeploy(spec,output,*,worker_python=None,timeout=600):
    if not spec.get('trust_configs_and_checkpoint'):raise ValueError('explicit executable artifact trust required')
    paths={}
    for key in ['deploy_entry','deploy_config','model_config','checkpoint','example_image']:
        p=Path(spec[key]).resolve()
        if file_digest(p)!=spec[key+'_sha256']:raise ValueError(key+' changed')
        paths[key]=p
    out=Path(output).resolve()
    if out.exists():raise ValueError('new export output required')
    out.mkdir(parents=True);write_json(out/'request.json',spec)
    command=[worker_python or sys.executable,str(paths['deploy_entry']),str(paths['deploy_config']),str(paths['model_config']),str(paths['checkpoint']),str(paths['example_image']),
        '--work-dir',str(out/'native'),'--device',spec.get('device','cpu'),'--dump-info']
    env=dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',WANDB_MODE='disabled')
    try:
        run_command(command,timeout,log=out/'export.log',env=env,cwd=paths['deploy_entry'].parents[1])
        graphs=[p for p in (out/'native').rglob('*.onnx')]
        if not graphs:raise ValueError('MMDeploy did not emit an ONNX graph')
        result={'status':'EXPORTED_NOT_FIDELITY_CERTIFIED','graphs':[{'path':p.relative_to(out).as_posix(),'sha256':file_digest(p)} for p in graphs],
            'decode_profile':'mmdet_end2end when output tensors are dets/labels; validate actual graph signature'}
        write_json(out/'result.json',result);seal_directory(out);return result
    except Exception as exc:
        write_json(out/'failure.json',{'status':'FAILED','message':str(exc)});seal_directory(out);raise
