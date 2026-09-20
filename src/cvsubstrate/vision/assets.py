"""Model identity covers every declared weights/processor/tokenizer/config component."""
from pathlib import Path
from typing import Literal
from pydantic import Field,model_validator
from cvsubstrate.contracts.models import Contract,ID,SHA256,relative_path
from cvsubstrate.provenance.io import file_digest,digest,safe_join

class VisionAsset(Contract):
    role: Literal['weights','processor','tokenizer','configuration','vocabulary','text_encoder','image_encoder','auxiliary']
    path: str
    sha256: SHA256
    license: str='UNKNOWN'
    @model_validator(mode='after')
    def valid(self):relative_path(self.path);return self

class VisionModelDescriptor(Contract):
    name: ID
    backend: ID
    revision: str
    assets: list[VisionAsset]=Field(min_length=1)
    preprocessing: dict=Field(default_factory=dict)
    feature_geometry: dict=Field(default_factory=dict)
    @model_validator(mode='after')
    def valid(self):
        if len({a.path for a in self.assets})!=len(self.assets):raise ValueError('duplicate asset path')
        if not any(a.role=='weights' for a in self.assets):raise ValueError('weights artifact required')
        return self
    @property
    def identity(self):
        value=self.model_dump(mode='json');value['assets']=sorted(value['assets'],key=lambda a:a['path']);return digest(value)

def inspect_assets(descriptor,root,*,reject_unlisted=False):
    d=VisionModelDescriptor.model_validate(descriptor);root=Path(root);rows=[]
    for a in d.assets:
        p=safe_join(root,a.path);rows.append({'path':a.path,'role':a.role,'status':'VERIFIED' if p.is_file() and not p.is_symlink() and file_digest(p)==a.sha256 else 'MISSING_OR_CHANGED'})
    unlisted=sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.relative_to(root).as_posix() not in {a.path for a in d.assets})
    return {'model_identity':d.identity,'assets':rows,'unlisted':unlisted,'ready':all(r['status']=='VERIFIED' for r in rows) and not (reject_unlisted and unlisted)}
SCHEMAS=[VisionAsset,VisionModelDescriptor]
