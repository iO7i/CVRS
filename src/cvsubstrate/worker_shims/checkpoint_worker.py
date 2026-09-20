"""Explicitly trusted checkpoint inventory and exact tensor-key conversion."""
from pathlib import Path
from runtime_common import main,read,write,sha,check_file,dependency,offline

def load_state(source):
    if source.get('serialization')=='trusted_pickle' and not source.get('trust_legacy_pickle'):
        raise RuntimeError('CHECKPOINT_TRUST: unsafe legacy pickle requires explicit trust')
    dependency('torch');import torch
    path=check_file(source['path'],source['sha256'])
    if source.get('serialization')=='safetensors':
        dependency('safetensors');from safetensors.torch import load_file
        state=load_file(str(path),device='cpu')
    else:
        unsafe=source.get('serialization')=='trusted_pickle'
        if unsafe and not source.get('trust_legacy_pickle'):raise RuntimeError('CHECKPOINT_TRUST: unsafe legacy pickle requires explicit trust')
        state=torch.load(str(path),map_location='cpu',weights_only=not unsafe)
    key=source.get('state_dict_key')
    if key:
        for part in key.split('/'):
            if not isinstance(state,dict) or part not in state:raise RuntimeError('CHECKPOINT_KEY: state_dict_key not present')
            state=state[part]
    if not isinstance(state,dict) or any(not isinstance(k,str) or not isinstance(v,torch.Tensor) for k,v in state.items()):raise RuntimeError('CHECKPOINT_CONTENT: select an explicit tensor-only state dictionary')
    return state

def inventory(state):return {k:{'shape':list(v.shape),'dtype':str(v.dtype),'elements':v.numel()} for k,v in sorted(state.items())}

def run(req):
    offline();op=req['operation']
    if op in {'diff_v1','transform_v1'}:
        from checkpoint_transform import run as v1_run
        return v1_run(req)
    spec=req['spec'];source=spec.get('source',spec);state=load_state(source)
    if op=='inspect':return {'source_sha256':source['sha256'],'tensors':inventory(state),'numerical_equivalence':'NOT_ASSESSED'}
    if op!='convert':raise RuntimeError('OPERATION_UNSUPPORTED: '+op)
    import torch
    mapping=spec.get('parameter_mapping',{});drops=set(spec.get('allowed_drop',[]));converted={};audit=[]
    if set(mapping)-set(state):raise RuntimeError('PARAMETER_MAPPING: mapping references missing source tensors')
    if drops-set(state):raise RuntimeError('PARAMETER_MAPPING: allowed_drop references missing source tensors')
    for k,tensor in state.items():
        if k in drops:audit.append({'source':k,'destination':None,'operation':'explicit_drop'});continue
        name=mapping.get(k,k)
        if name in converted:raise RuntimeError('PARAMETER_COLLISION: '+name)
        converted[name]=tensor.detach().cpu().contiguous()
        audit.append({'source':k,'destination':name,'operation':'rename' if name!=k else 'identity'})
    shapes=spec.get('destination_shapes',{})
    missing=sorted(set(shapes)-set(converted));unexpected=sorted(set(converted)-set(shapes)) if shapes else []
    if set(missing)-set(spec.get('allowed_missing',[])):raise RuntimeError('MISSING_PARAMETERS: '+str(missing))
    if unexpected:raise RuntimeError('UNEXPECTED_PARAMETERS: '+str(unexpected))
    for k,shape in shapes.items():
        if k in converted and list(converted[k].shape)!=shape:raise RuntimeError('PARAMETER_SHAPE: '+k)
    out=Path(req['output_dir']);out.mkdir(parents=True,exist_ok=True)
    if spec.get('output_format')=='safetensors':
        dependency('safetensors');from safetensors.torch import save_file
        p=out/'weights.safetensors';save_file(converted,str(p));from safetensors.torch import load_file
        again=load_file(str(p))
    else:
        p=out/'weights.pth';torch.save(converted,str(p));again=torch.load(str(p),map_location='cpu',weights_only=True)
    same=all(torch.equal(t,again[k]) for k,t in converted.items()) and set(again)==set(converted)
    if not same:raise RuntimeError('CHECKPOINT_ROUNDTRIP: serialized tensors changed')
    report={'status':'CONVERTED','source_sha256':source['sha256'],'destination_sha256':sha(p),'file':p.name,
        'mapping':audit,'missing_parameters':missing,'unexpected_parameters':unexpected,'tensor_inventory':inventory(again),
        'tensor_roundtrip_exact':same,'model_output_parity':'NOT_EXECUTED','limits':'Tensor renaming/preservation is not cross-architecture equivalence.'}
    write(out/'conversion_report.json',report);return report
if __name__=='__main__':main(run)
