"""Optional real feature-map providers shared by standalone and native workers.

Local code and weights must be explicitly identified. No network model fetches.
"""
from pathlib import Path
from collections import OrderedDict
import hashlib,json,os

def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def tree_hash(root):
    root=Path(root).resolve();rows={}
    for p in sorted(root.rglob('*')):
        if any(part in {'.git','__pycache__','.pytest_cache'} for part in p.relative_to(root).parts):continue
        if p.is_symlink():raise ValueError('model source tree must not contain symlinks')
        if p.is_file():rows[p.relative_to(root).as_posix()]=file_hash(p)
    if not rows:raise ValueError('empty local model/source tree')
    return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest(),rows

def _load_weights(model,desc):
    import torch
    path=desc.get('weights')
    if not path:return False
    if not desc.get('weights_sha256') or file_hash(path)!=desc['weights_sha256']:raise ValueError('backbone weight digest mismatch')
    if str(path).endswith('.safetensors'):
        from safetensors.torch import load_file
        weights=load_file(path,device='cpu')
    else:weights=torch.load(path,map_location='cpu',weights_only=True)
    # No automatic stripping/remapping/dropping of a pretrained model's parameters.
    if not isinstance(weights,dict) or any(not torch.is_tensor(t) for t in weights.values()):raise ValueError('backbone needs direct tensor state_dict; convert explicitly first')
    model.load_state_dict(weights,strict=True);return True

def create_provider(desc):
    import torch
    from torch import nn
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    provider=desc['provider'];indices=list(desc.get('out_indices',[1,2,3,4]));loaded=False;source_files={}
    if desc.get('allow_downloads',False):raise ValueError('automatic downloads are not supported')
    if provider=='timm':
        import timm
        # Exact feature-wrapper state dicts are supported. Classification checkpoint
        # conversion is explicit, not a silent missing/unexpected-key workaround.
        model=timm.create_model(desc['model'],pretrained=False,features_only=True,out_indices=tuple(indices))
        loaded=_load_weights(model,desc);channels=list(model.feature_info.channels())
        def forward(x):return model(x)
    elif provider=='huggingface':
        from transformers import AutoBackbone
        root=Path(desc['model'])
        if not root.is_dir():raise ValueError('Hugging Face provider requires a fully local model directory')
        actual,source_files=tree_hash(root)
        if actual!=desc.get('local_model_directory_sha256'):raise ValueError('local Hugging Face model directory digest required/mismatch')
        model=AutoBackbone.from_pretrained(str(root),local_files_only=True,trust_remote_code=False,out_indices=indices)
        loaded=True;channels=list(model.channels)
        def forward(x):return model(pixel_values=x).feature_maps
    elif provider in {'dinov2_local','dinov3_local'}:
        if not desc.get('trust_local_repository'):raise ValueError('local DINO hubconf executes Python; explicit trust required')
        root=Path(desc['local_repository']);actual,source_files=tree_hash(root)
        if actual!=desc.get('repository_sha256'):raise ValueError('DINO repository content hash mismatch')
        model=torch.hub.load(str(root),desc['model'],source='local',pretrained=False)
        loaded=_load_weights(model,desc)
        if not hasattr(model,'get_intermediate_layers'):raise ValueError('selected DINO model lacks feature-map API')
        channels=[int(model.embed_dim)]*len(indices)
        def forward(x):return model.get_intermediate_layers(x,n=indices,reshape=True,return_class_token=False)
    else:raise ValueError('unsupported backbone provider')
    class Provider(nn.Module):
        def __init__(self):
            super().__init__();self.encoder=model;self.channels=channels;self.pretrained_loaded=loaded;self.source_files=source_files
        def forward(self,x):
            values=forward(x)
            if not isinstance(values,(list,tuple)) or len(values)!=len(self.channels):raise ValueError('feature count does not match declared interface')
            result=OrderedDict();geometry=[]
            for i,(v,c) in enumerate(zip(values,self.channels)):
                if v.ndim!=4 or v.shape[0]!=x.shape[0] or v.shape[1]!=c or min(v.shape[2:])<=0:raise ValueError('backbone must return NCHW features with declared channels')
                geometry.append({'index':i,'shape':list(v.shape),'effective_stride_y':x.shape[-2]/v.shape[-2],'effective_stride_x':x.shape[-1]/v.shape[-1]})
                if not torch.isfinite(v).all():raise ValueError('nonfinite backbone feature')
                expected=desc.get('input_contract',{}).get('expected_strides')
                if expected and (len(expected)!=len(values) or abs(geometry[-1]['effective_stride_y']-expected[i])>1e-6 or abs(geometry[-1]['effective_stride_x']-expected[i])>1e-6):raise ValueError('measured backbone geometry differs from declared stride; check input padding/feature recipe')
                result[str(i)]=v
            self.last_geometry=geometry
            return result
    return Provider()
