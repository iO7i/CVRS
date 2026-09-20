"""Materialized artifact composition; never advertises distributed autograd."""
from pathlib import Path
from typing import Any
from cvsubstrate.adoption.contracts import InteropArtifact
from cvsubstrate.provenance.io import digest,file_digest,read_json,write_json,safe_join
from cvsubstrate.errors import CVRSError

def check_port(artifact,port):
    a=InteropArtifact.model_validate(artifact);errors=[]
    if port.get('requires_grad'):errors.append('cross-worker gradients are not supported')
    for k in ('kind','dtype','coordinate_frame'):
        if port.get(k) is not None and getattr(a,k)!=port[k]:errors.append(k+' mismatch')
    wanted=port.get('shape')
    if wanted is not None:
        if a.shape is None or len(a.shape)!=len(wanted) or any(b is not None and b!=v for v,b in zip(a.shape,wanted)):
            errors.append('shape mismatch')
    for k,v in port.get('semantics',{}).items():
        if a.semantics.get(k)!=v:errors.append('semantic mismatch: '+k)
    return {'status':'COMPATIBLE' if not errors else 'INCOMPATIBLE','errors':errors,
            'note':'Shape agreement is not learned feature compatibility. Declare layer, stride and normalization requirements.'}

def inspect_artifact(value,root):
    a=InteropArtifact.model_validate(value);p=safe_join(Path(root),a.path)
    if not p.is_file() or file_digest(p)!=a.sha256:raise CVRSError('ARTIFACT_INTEGRITY','materialized port changed')
    if a.kind in {'features','embeddings'}:
        try:import numpy as np
        except ImportError:raise CVRSError('DEPENDENCY_UNAVAILABLE','NumPy is needed to verify tensor artifacts')
        if p.suffix!='.npy':raise CVRSError('TENSOR_FORMAT','v1 cross-worker tensors must be non-pickled .npy arrays')
        arr=np.load(p,allow_pickle=False,mmap_mode='r')
        if arr.dtype.hasobject or list(arr.shape)!=a.shape or str(arr.dtype)!=a.dtype:raise CVRSError('TENSOR_METADATA','actual tensor differs from descriptor')
    return {'status':'VERIFIED','artifact_digest':digest(a)}

def compile_composition(spec):
    nodes=spec.get('nodes',[]);ids=[n['id'] for n in nodes]
    if len(ids)!=len(set(ids)):raise ValueError('duplicate composition node')
    pending={n['id']:n for n in nodes};done: list[str]=[]
    while pending:
        ready=[k for k,n in pending.items() if set(n.get('depends_on',[]))<=set(done)]
        if not ready:raise ValueError('composition cycle or missing dependency')
        for k in sorted(ready):done.append(k);pending.pop(k)
    for n in nodes:
        if n.get('cross_worker_gradients'):raise CVRSError('AUTOGRAD_BOUNDARY','keep the jointly trained model in one native worker')
        for name,b in n.get('bindings',{}).items():
            if b['node'] not in n.get('depends_on',[]):raise ValueError('bound producer must be an explicit dependency')
    return {'status':'PLANNED','order':done,'nodes':nodes,'plan_digest':digest(spec),
            'boundary':'explicit file outputs only; no automatic model refactoring'}

def run_composition(spec,root,*,trust=False):
    from cvsubstrate.adoption.wrapping import run_paper
    plan=compile_composition(spec);out=Path(root)
    if out.exists():raise ValueError('use a new composition output')
    out.mkdir(parents=True);runs: dict[str, dict[str, Any]]={};byid={n['id']:n for n in plan['nodes']}
    for name in plan['order']:
        n=byid[name]
        failed=[d for d in n.get('depends_on',[]) if runs[d]['status']!='SUCCEEDED']
        if failed:runs[name]={'status':'BLOCKED','dependencies':failed};continue
        source_spec=Path(n['paper_spec']).resolve()
        value=read_json(source_spec)
        native_repo=Path(value['repo'])
        value['repo']=str(native_repo if native_repo.is_absolute() else (source_spec.parent/native_repo).resolve())
        for key,b in n.get('bindings',{}).items():
            producer=runs[b['node']];record=producer['outputs'][b['output']]
            p=safe_join(Path(producer['bundle']),record['path'])
            if file_digest(p)!=record['sha256']:raise CVRSError('ARTIFACT_INTEGRITY','producer output changed')
            if 'descriptor' in b:
                a=read_json(Path(b['descriptor']));check=check_port(a,b.get('port',{}))
                if check['errors']:raise CVRSError('PORT_MISMATCH','; '.join(check['errors']))
                if a['sha256']!=record['sha256']:raise CVRSError('PORT_IDENTITY','descriptor is for a different output')
            value.setdefault('inputs',{})[key]=str(p)
            value.setdefault('input_digests',{})[key]=record['sha256']
        sp=out/(name+'.json');write_json(sp,value)
        runs[name]=run_paper(sp,n.get('operation','predict'),out/name,trust=trust)
    result={'status':'SUCCEEDED' if all(r['status']=='SUCCEEDED' for r in runs.values()) else 'FAILED',
            'plan_digest':plan['plan_digest'],'runs':runs}
    write_json(out/'composition.json',result)
    from cvsubstrate.provenance.artifact_set import seal_directory
    seal_directory(out);return result
