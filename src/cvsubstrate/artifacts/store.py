"""Local SHA-256 object storage and content-bound action caching.

Caches never assert scientific reproducibility. A caller must declare EVERY
semantic input and implementation/environment identity when creating an action key.
"""
from __future__ import annotations
import os,re,shutil,tempfile
from pathlib import Path
from typing import Protocol,runtime_checkable
from cvsubstrate.contracts.groundwork import ArtifactRef
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import digest,file_digest,write_json,read_json,atomic_bytes

@runtime_checkable
class ArtifactStore(Protocol):
    def put(self,path:Path,media_type:str='application/octet-stream')->ArtifactRef: ...
    def get(self,sha256:str)->Path: ...
    def exists(self,sha256:str)->bool: ...
    def verify(self,sha256:str)->bool: ...
    def materialize(self,sha256:str,destination:Path)->Path: ...

class LocalArtifactStore:
    def __init__(self,root:Path):
        self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
        self.objects=self.root/'objects';self.objects.mkdir(exist_ok=True)
    def _path(self,sha):
        if not re.fullmatch('[a-f0-9]{64}',sha): raise CVRSError('ARTIFACT_ID','invalid SHA-256 object identity')
        p=self.objects/sha[:2]/sha[2:]
        if not p.resolve().is_relative_to(self.objects.resolve()) or any(q.is_symlink() for q in (self.objects,p.parent,p)):
            raise CVRSError('ARTIFACT_SYMLINK','object paths cannot traverse symlinks')
        return p
    def put(self,path,media_type='application/octet-stream'):
        src=Path(path)
        if src.is_symlink() or not src.is_file(): raise CVRSError('ARTIFACT_SOURCE','expected regular source file')
        sha=file_digest(src);dst=self._path(sha);dst.parent.mkdir(parents=True,exist_ok=True)
        if dst.exists():
            if not self.verify(sha): raise CVRSError('CACHE_CORRUPT','existing content-addressed object changed')
        else:
            fd,tmp=tempfile.mkstemp(prefix='.object-',dir=dst.parent)
            os.close(fd)
            try:
                shutil.copyfile(src,tmp)
                if file_digest(Path(tmp))!=sha: raise CVRSError('SOURCE_CHANGED','input changed during object capture')
                os.replace(tmp,dst)
            finally:
                if Path(tmp).exists():Path(tmp).unlink()
        return ArtifactRef(sha256=sha,bytes=dst.stat().st_size,media_type=media_type,name=src.name)
    def get(self,sha256):
        p=self._path(sha256)
        if not self.verify(sha256): raise CVRSError('ARTIFACT_INTEGRITY','object missing or changed')
        return p
    def exists(self,sha256): return self._path(sha256).is_file()
    def verify(self,sha256):
        p=self._path(sha256)
        return p.is_file() and file_digest(p)==sha256
    def materialize(self,sha256,destination):
        dst=Path(destination)
        if dst.exists(): raise CVRSError('OUTPUT_EXISTS','materialization never overwrites')
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(self.get(sha256),dst)
        if file_digest(dst)!=sha256: raise CVRSError('ARTIFACT_INTEGRITY','materialized object mismatch')
        return dst

class ActionCache:
    def __init__(self,root:Path):
        from cvsubstrate.artifacts.managed import ManagedArtifactStore
        self.store=ManagedArtifactStore(root);self.index=self.store.root/'actions';self.index.mkdir(exist_ok=True)
    @staticmethod
    def key(*,action,implementation_digest,parameters,inputs,environment):
        return digest({'version':'1.0','action':action,'implementation':implementation_digest,
            'parameters':parameters,'inputs':inputs,'environment':environment})
    def put(self,key,record):
        if not re.fullmatch('[a-f0-9]{64}',key): raise ValueError('invalid action key')
        value={'action_key':key,'record':record,'record_digest':digest(record)}
        path=self.index/(key+'.json')
        from cvsubstrate.foundation.lifecycle import process_lock
        with process_lock(self.store.lock):
            for item in record.get('artifacts',{}).values():self.store.get(item['sha256'])
            if path.exists() and read_json(path)!=value:raise CVRSError('CACHE_NONDETERMINISM','same action key produced different output')
            write_json(path,value)
    def get(self,key):
        if not re.fullmatch('[a-f0-9]{64}',key): raise ValueError('invalid action key')
        p=self.index/(key+'.json')
        if not p.exists():return None
        v=read_json(p)
        if v.get('action_key')!=key or v.get('record_digest')!=digest(v['record']):raise CVRSError('CACHE_CORRUPT','action record identity mismatch')
        for item in v['record'].get('artifacts',{}).values():self.store.get(item['sha256'])
        return v['record']
