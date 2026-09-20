"""Tensor structural diff and explicit rename/reshape/cast/drop/generate rules.

No neural architecture conversion is inferred. Dtype narrowing and generated
parameters require explicit acknowledgement and are recorded as non-reversible.
"""
from pathlib import Path
import math,re
from runtime_common import sha,write
from checkpoint_worker import load_state,inventory

def diff_states(a,b):
    import torch
    result=[]
    for name in sorted(set(a)|set(b)):
        x=a.get(name);y=b.get(name)
        row={'name':name,'left_shape':list(x.shape) if x is not None else None,'right_shape':list(y.shape) if y is not None else None,
             'left_dtype':str(x.dtype) if x is not None else None,'right_dtype':str(y.dtype) if y is not None else None}
        if x is None:row['status']='GENERATED_OR_ADDED'
        elif y is None:row['status']='DROPPED_OR_MISSING'
        elif x.shape!=y.shape:row['status']='SHAPE_DIFFERENT'
        else:
            row['exact']=torch.equal(x,y) and x.dtype==y.dtype
            row['status']='EXACT' if row['exact'] else 'CHANGED'
            # Chunked double precision avoids allocating another full checkpoint.
            xf=x.detach().cpu().reshape(-1);yf=y.detach().cpu().reshape(-1)
            maxdiff=0.;sums=0.;count=0;nonfinite=0
            for off in range(0,xf.numel(),1024*1024):
                xx=xf[off:off+1024*1024];yy=yf[off:off+1024*1024]
                dtype=torch.complex128 if xx.is_complex() or yy.is_complex() else torch.float64
                d=(xx.to(dtype)-yy.to(dtype)).abs();good=torch.isfinite(d);nonfinite+=int((~good).sum())
                if good.any():values=d[good];maxdiff=max(maxdiff,float(values.max()));sums+=float(values.sum());count+=values.numel()
            row.update(max_absolute_delta=maxdiff if count else None,mean_absolute_delta=sums/count if count else None,nonfinite_deltas=nonfinite)
        result.append(row)
    return {'parameters':result,'structurally_identical':set(a)==set(b) and all(x['status']=='EXACT' for x in result),
            'meaning':'tensor comparison, not model output equivalence'}

def transform_state(source,plan):
    import torch
    rules=plan.get('rules',[]);output={};audit=[];consumed=set()
    allowed_ops={'rename','prefix','reshape','cast','drop'}
    for r in rules:
        if r.get('operation') not in allowed_ops:raise ValueError('unsupported tensor transform')
        if r['operation']=='prefix':
            if not isinstance(r.get('source_prefix'),str) or not isinstance(r.get('destination_prefix'),str):raise ValueError('prefix rule needs string prefixes')
        elif r.get('source') not in source:raise ValueError('rule references missing tensor '+str(r.get('source')))
    for key,tensor in sorted(source.items()):
        name=key;value=tensor.detach().cpu().contiguous();ops=[];dropped=False;reversible=True
        for i,r in enumerate(rules):
            op=r['operation']
            if op=='prefix':
                if not name.startswith(r['source_prefix']):continue
                name=r['destination_prefix']+name[len(r['source_prefix']):];ops.append('RENAMED');consumed.add(i)
            elif r.get('source')==key:
                consumed.add(i)
                if op=='rename':name=r['destination'];ops.append('RENAMED')
                elif op=='reshape':
                    shape=r['shape']
                    if any(not isinstance(x,int) or x<0 for x in shape) or math.prod(shape)!=value.numel():raise ValueError('reshape must preserve tensor elements')
                    value=value.reshape(shape).contiguous();ops.append('RESHAPED')
                elif op=='cast':
                    dtype=r['dtype'];allowed={'float16','bfloat16','float32','float64','int8','int16','int32','int64','uint8','bool'}
                    if dtype not in allowed:raise ValueError('unsupported dtype')
                    converted=value.to(getattr(torch,dtype));exact=torch.equal(converted.to(value.dtype),value)
                    if not exact and not r.get('allow_lossy'):raise ValueError('lossy cast requires allow_lossy=true')
                    value=converted;ops.append('CAST_EXACT' if exact else 'CAST_LOSSY');reversible &= exact
                elif op=='drop':
                    if not r.get('justification'):raise ValueError('drop needs justification')
                    ops.append('DROPPED');dropped=True;reversible=False
        if not dropped:
            if not isinstance(name,str) or not name or name in output:raise ValueError('tensor name collision/invalid name')
            output[name]=value
        audit.append({'source':key,'destination':None if dropped else name,'source_shape':list(tensor.shape),
            'destination_shape':None if dropped else list(value.shape),'operations':ops or ['EXACT'],'reversible':reversible})
    if set(range(len(rules)))-consumed:raise ValueError('unused transform rule')
    for item in plan.get('generate',[]):
        if not item.get('justification') or item['name'] in output:raise ValueError('generated parameter needs unique name and justification')
        shape=item['shape'];dtype=item.get('dtype','float32');method=item.get('method','zeros')
        if any(not isinstance(v,int) or v<0 for v in shape) or math.prod(shape)>plan.get('max_generated_elements',10000000):raise ValueError('generated shape/bound invalid')
        if dtype not in {'float16','float32','float64','int64'} or method not in {'zeros','ones','constant'}:raise ValueError('explicit deterministic generation only')
        value=torch.full(shape,item.get('value',1 if method=='ones' else 0),dtype=getattr(torch,dtype))
        output[item['name']]=value;audit.append({'source':None,'destination':item['name'],'operations':['GENERATED'],'reversible':False,'justification':item['justification']})
    expected=plan.get('destination_inventory')
    if expected is not None:
        if set(expected)!=set(output):raise ValueError('destination keys do not match complete expected inventory')
        for k,t in output.items():
            if list(t.shape)!=expected[k]['shape'] or str(t.dtype).removeprefix('torch.')!=expected[k]['dtype']:raise ValueError('destination shape/dtype mismatch '+k)
    return output,{'parameters':audit,'tensor_transform_reversible':all(a['reversible'] for a in audit),
        'conversion_confidence':'EXPLICIT_RULES_ONLY','model_output_equivalence':'NOT_ASSESSED','unresolved':[]}

def run(req):
    import torch
    if req['operation']=='diff_v1':
        a=load_state(req['left']);b=load_state(req['right']);return diff_states(a,b)
    state=load_state(req['source']);converted,report=transform_state(state,req['plan'])
    out=Path(req['output_dir']);out.mkdir(parents=True,exist_ok=True);path=out/'weights.pth'
    if path.exists():raise ValueError('conversion never overwrites')
    torch.save(converted,path);again=torch.load(path,map_location='cpu',weights_only=True)
    roundtrip=diff_states(converted,again)
    if not roundtrip['structurally_identical']:raise ValueError('converted tensor roundtrip changed values')
    report.update(source_sha256=req['source']['sha256'],destination_sha256=sha(path),serialized_roundtrip_exact=True,tensor_inventory=inventory(again),file=path.name)
    write(out/'conversion_report.json',report);return report
