"""Capsule dependency closure: describe, verify and explicitly bind external assets."""
from __future__ import annotations
from pathlib import Path
from typing import Literal
from pydantic import Field,model_validator
from cvsubstrate.contracts.models import Contract,SHA256,ID,relative_path
from cvsubstrate.provenance.io import file_digest,safe_join,digest

class Dependency(Contract):
    id: ID
    sha256: SHA256
    disposition: Literal['EMBEDDED','EXTERNAL_REQUIRED','OPTIONAL','RESTRICTED']
    path: str|None=None
    license: str='UNKNOWN'
    depends_on: list[ID]=Field(default_factory=list)
    @model_validator(mode='after')
    def valid(self):
        if self.path is not None:relative_path(self.path)
        if self.disposition=='EMBEDDED' and self.path is None:raise ValueError('embedded asset needs relative path')
        return self

class DependencyClosure(Contract):
    dependencies: list[Dependency]
    @model_validator(mode='after')
    def valid(self):
        ids={d.id for d in self.dependencies}
        if len(ids)!=len(self.dependencies):raise ValueError('duplicate dependency')
        if any(set(d.depends_on)-ids for d in self.dependencies):raise ValueError('unknown dependency reference')
        visiting=set();done=set();lookup={d.id:d for d in self.dependencies}
        def visit(k):
            if k in visiting:raise ValueError('dependency cycle')
            if k in done:return
            visiting.add(k)
            for d in lookup[k].depends_on:visit(d)
            visiting.remove(k);done.add(k)
        for k in ids:visit(k)
        return self

def inspect_closure(closure:DependencyClosure,root:Path,bindings:dict[str,str]|None=None):
    bindings=bindings or {};known={d.id for d in closure.dependencies}
    if set(bindings)-known:raise ValueError('unrecognized dependency binding')
    rows=[]
    for d in closure.dependencies:
        p=safe_join(root,d.path) if d.disposition=='EMBEDDED' else Path(bindings[d.id]) if d.id in bindings else None
        status='MISSING'
        if p is not None:
            status='VERIFIED' if p.is_file() and not p.is_symlink() and file_digest(p)==d.sha256 else 'MISMATCH'
        rows.append({'id':d.id,'sha256':d.sha256,'disposition':d.disposition,'status':status,
                     'required':d.disposition!='OPTIONAL','license':d.license})
    return {'closure_digest':digest(closure),'ready':all(r['status']=='VERIFIED' or not r['required'] for r in rows),'dependencies':rows,
            'automatically_downloaded':False,'license_authorization_inferred':False}
SCHEMAS=[Dependency,DependencyClosure]
