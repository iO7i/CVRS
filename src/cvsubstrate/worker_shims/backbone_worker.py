"""Standalone feature-extraction service, dependency isolated from the controller."""
from pathlib import Path
import importlib.metadata
from runtime_common import main,read,write,sha as file_hash,check_file,offline
from backbone_impl import create_provider

def run(request):
    if request.get('operation')=='capabilities':
        return {'operations':['extract'],'providers':['timm','huggingface','dinov2_local','dinov3_local'],'input':'explicit caller-normalized NCHW .npy','execution_verified':False}
    if request.get('operation')!='extract':raise ValueError('unsupported feature operation')
    import numpy as np
    import torch
    spec=request['spec'];desc=spec['descriptor'];out=Path(request['output_dir']);out.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(int(spec.get('threads',1)));torch.manual_seed(int(spec.get('seed',0)))
    device=spec.get('device','cpu')
    if device!='cpu' and not(device.startswith('cuda') and torch.cuda.is_available()):raise ValueError('requested device unavailable')
    input_path=check_file(spec['input_array'],spec['input_sha256']);data=np.load(input_path,allow_pickle=False)
    if data.ndim!=4 or not np.issubdtype(data.dtype,np.floating) or not np.isfinite(data).all():raise ValueError('finite caller-normalized float NCHW array required')
    offline();model=create_provider(desc).to(device).eval();x=torch.from_numpy(data).to(device)
    with torch.no_grad():features=model(x)
    files={};pooled=[]
    for name,tensor in features.items():
        a=tensor.detach().cpu().numpy();target=out/f'feature-{name}.npy';np.save(target,a,allow_pickle=False)
        files[name]={'path':target.name,'sha256':file_hash(target),'shape':list(a.shape),'dtype':str(a.dtype)};pooled.append(tensor.float().mean(dim=(-2,-1)).detach().cpu().numpy())
    embeddings=np.concatenate(pooled,axis=1);np.save(out/'embeddings.npy',embeddings,allow_pickle=False)
    result={'descriptor':desc,'pretrained_loaded':model.pretrained_loaded,'features':files,
        'embeddings':{'path':'embeddings.npy','sha256':file_hash(out/'embeddings.npy'),'shape':list(embeddings.shape),'pooling':'spatial mean per selected feature; concatenated channels'},
        'feature_geometry':getattr(model,'last_geometry',None),'input_sha256':spec['input_sha256'],'device':device,'source_files':model.source_files,'torch_version':torch.__version__,
        'scientific_relevance':'Feature extraction executed, no downstream-quality or domain-gap claim.'}
    write(out/'execution.json',result);return result

if __name__=='__main__':main(run)
