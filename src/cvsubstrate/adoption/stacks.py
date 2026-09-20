"""User-facing native stack packs with explicit input and output boundaries."""
from pathlib import Path
import tempfile,sys
from cvsubstrate.adoption.environments import PACKS
from cvsubstrate.adoption.common import execution_tree
from cvsubstrate.provenance.io import write_json,read_json,read_jsonl,digest,file_digest
from cvsubstrate.provenance.artifact_set import verify_directory
from cvsubstrate.execution.process import run_command
from cvsubstrate.errors import CVRSError

def execute_stack(family,operation,payload,destination,*,worker_python=None,trust=False,timeout=600):
    if family not in PACKS:raise ValueError('unknown stack family')
    if operation not in PACKS[family]['operations']:raise CVRSError('UNSUPPORTED_OPERATION',family+' / '+operation)
    if not trust:raise CVRSError('TRUST_REQUIRED','native configs, model files and package code execute in the configured interpreter')
    if family in {'ultralytics','rfdetr'}:
        from cvsubstrate.adapters.modern import native_model_job
        if 'experiment' not in payload:raise ValueError('this pack requires a canonical ExperimentSpec path in payload.experiment')
        return native_model_job(payload['experiment'],destination,operation={'train':'train'}.get(operation,operation),worker_python=worker_python,timeout=timeout)
    if family in {'grounding-dino','sam','sam2'}:
        from cvsubstrate.vision.service import vision_job
        job=payload.get('job',payload)
        expected={'grounding-dino':'hf_grounding_dino','sam':'hf_sam','sam2':'sam2'}[family]
        if job.get('backend')!=expected:raise ValueError('VisionJob backend differs from selected stack pack')
        return vision_job(job,destination,worker_python=worker_python,timeout=timeout)
    if family in {'torchgeo','terratorch'}:
        from cvsubstrate.bridges.service import run_bridge
        mapped={'sample':'export','native_train':'train'}.get(operation,operation)
        return run_bridge({'bridge':family,'operation':mapped,'payload':payload,'output_dir':str(destination),
            'worker_python':worker_python or sys.executable,'trust_code':True,'timeout_seconds':timeout})
    if family=='core':
        from cvsubstrate.adoption.inspect import inspect_repository
        from cvsubstrate.adoption.methodology import reviewer_report
        return inspect_repository(payload['repo']).model_dump(mode='json') if operation=='inspect' else reviewer_report(payload['capsule'])
    source_report=None
    if payload.get('repo'):
        from cvsubstrate.adoption.inspect import inspect_repository
        source_report=inspect_repository(payload['repo']).model_dump(mode='json')
        if payload.get('repository_digest') and source_report['root_identity']!=payload['repository_digest']:raise ValueError('native repository identity changed')
    script=Path(__file__).resolve().parents[1]/'worker_shims'/'stack_worker.py' 
    with execution_tree(destination) as out:
        request={'protocol_version':'1.0','operation':operation,'payload':{**payload,'family':family,'trust_code':True},'output_dir':str(out)}
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);write_json(p/'request.json',request)
            run_command([worker_python or sys.executable,str(script),'--request',str(p/'request.json'),'--response',str(p/'response.json')],timeout,log=out/'worker.log')
            response=read_json(p/'response.json')
        if response.get('status')!='SUCCEEDED':
            e=response.get('error',{});raise CVRSError(e.get('code','STACK_FAILED'),e.get('message','native operation failed'))
        if (out/'predictions.jsonl').exists():
            for row in read_jsonl(out/'predictions.jsonl'):
                if row.get('task','hbb_detection')=='hbb_detection':
                    from cvsubstrate.contracts.models import DetectionPrediction
                    DetectionPrediction.model_validate(row)
                elif row['task']=='semantic_segmentation':
                    from cvsubstrate.adoption.contracts import SemanticLabelMap
                    SemanticLabelMap.model_validate(row)
                elif row['task']=='obb_detection':
                    if not len(row['polygons'])==len(row['scores'])==len(row['category_ids']):raise ValueError('OBB output count mismatch')
        write_json(out/'stack-receipt.json',{'family':family,'operation':operation,'payload_digest':digest(payload),
                 'worker_sha256':file_digest(script),'result':response['result'],'source_checkout':source_report})
    return {'status':'SUCCEEDED','output':str(destination),'result':response['result'],'integrity':verify_directory(Path(destination))}
