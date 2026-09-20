"""An explicit execution bridge to a locally supplied DOTA Task1 evaluator.

Does not vendor/reimplement polyiou or claim a local diagnostic is official AP.
The default upstream API inspected is CAPTAIN-WHU/DOTA_devkit voc_eval.
A caller must pin and trust its own source tree and compiled dependencies.
"""
from pathlib import Path
from typing import Literal
import sys
from cvsubstrate.contracts.models import Contract,SHA256
from cvsubstrate.contracts.research import OrientedDataset,OrientedPrediction
from cvsubstrate.data.dota import export_task1
from cvsubstrate.provenance.artifact_set import seal_directory
from cvsubstrate.provenance.io import file_digest,write_json,read_json,digest
from cvsubstrate.execution.process import run_command
from cvsubstrate.errors import CVRSError


class DotaReference(Contract):
    repository: Literal['CAPTAIN-WHU/DOTA_devkit'] = 'CAPTAIN-WHU/DOTA_devkit'
    source_revision: str
    module_path: str
    module_sha256: SHA256
    trust_executable_code: bool = False
    iou_threshold: float = .5
    use_07_metric: bool = True
    note: str = 'Declared source identity; inspect the local source tree and compiled polyiou. No automatic certification.'


def run_reference(m:OrientedDataset,rows:list[OrientedPrediction],reference:DotaReference,output:Path,*,worker_python=None,timeout=180.):
    if not reference.trust_executable_code:raise CVRSError('REFERENCE_TRUST','DOTA module is executable code; explicit trust required')
    module=Path(reference.module_path)
    if not module.is_absolute() or module.is_symlink() or not module.is_file() or file_digest(module)!=reference.module_sha256:
        raise CVRSError('REFERENCE_IDENTITY','reference module must exist at an absolute hash-verified path')
    if not 0<reference.iou_threshold<=1:raise ValueError('IoU threshold must be in (0,1]')
    output=Path(output).resolve()
    if output.exists():raise CVRSError('OUTPUT_EXISTS','DOTA reference output must be new')
    # Export validates dev role and exact image universe. Preserve, do not amend,
    # empty categories that some legacy evaluator revisions cannot process.
    output.mkdir(parents=True)
    export_task1(m,rows,output/'detections')
    write_json(output/'dataset.json',m);write_json(output/'reference.json',reference)
    cats={c.id:c.name for c in m.categories};positive={c:0 for c in cats}
    gt=output/'ground_truth';gt.mkdir()
    for sample in m.samples:
        lines=[]
        for ann in sample.annotations:
            values=[format(v,'.17g') for p in ann.polygon for v in p]+[cats[ann.category_id],'1' if ann.difficult else '0']
            lines.append(' '.join(values))
            positive[ann.category_id]+=not ann.difficult
        (gt/(sample.id+'.txt')).write_text('\n'.join(lines)+('\n' if lines else ''),'utf-8')
    (output/'images.txt').write_text(''.join(s.id+'\n' for s in m.samples),'utf-8')
    request={'module_path':str(module),'module_sha256':reference.module_sha256,'classes':list(cats.values()),
        'detpath':str(output/'detections'/'Task1_{:s}.txt'),'annopath':str(gt/'{:s}.txt'),
        'imagesetfile':str(output/'images.txt'),'iou':reference.iou_threshold,'use_07_metric':reference.use_07_metric}
    write_json(output/'request.json',request)
    try:
        if any(n==0 for n in positive.values()):
            raise CVRSError('REFERENCE_EMPTY_CLASS','full declared class mean is undefined with zero-positive classes; use diagnostics or a predeclared supported protocol, never silently exclude classes')
        shim=Path(__file__).resolve().parents[1]/'worker_shims'/'dota_reference_worker.py'
        run_command([worker_python or sys.executable,str(shim),'--request',str(output/'request.json'),'--response',str(output/'response.json')],timeout,log=output/'worker.log')
        value=read_json(output/'response.json')
        if value.get('status')!='SUCCEEDED':raise CVRSError('REFERENCE_FAILED',str(value.get('error','no successful reference response')))
        if file_digest(module)!=reference.module_sha256:raise CVRSError('REFERENCE_CHANGED','module changed during evaluation')
        result={'status':'REFERENCE_EXECUTED','kind':'DOTA_EXTERNAL_REFERENCE_RESULT','dataset_digest':digest(m),
            'reference':reference.model_dump(mode='json'),'native_result':value['result'],
            'official_source_authenticity':'caller-declared repository/revision and measured file hash; not independently authenticated',
            'parity_verified':False,'limits':'Execution bridge only. Genuine official-reference parity and real DOTA benchmark certification require separate evidence.'}
        write_json(output/'result.json',result)
    except Exception as exc:
        result={'status':'BLOCKED_OR_FAILED','error_code':getattr(exc,'code',type(exc).__name__),'reason':str(exc),'reference_metrics_fabricated':False}
        write_json(output/'result.json',result);seal_directory(output);raise
    seal_directory(output);return result
