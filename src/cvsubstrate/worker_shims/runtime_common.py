"""Stdlib-only transport shared by optional workers (Python >=3.8).
Trusted process isolation, not hostile-code containment. No automatic downloads.
"""
import argparse,hashlib,importlib.metadata,importlib.util,json,os,socket,sys
from pathlib import Path

def read(path):
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:raise ValueError('duplicate JSON key '+k)
            result[k]=v
        return result
    with open(path,encoding='utf-8') as f:return json.load(f,object_pairs_hook=pairs,parse_constant=lambda s:(_ for _ in ()).throw(ValueError(s)))

def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    with tmp.open('w',encoding='utf-8') as f:json.dump(value,f,allow_nan=False,sort_keys=True);f.flush();os.fsync(f.fileno())
    os.replace(str(tmp),str(path))

def write_lines(path,rows):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8') as f:
        for row in rows:f.write(json.dumps(row,allow_nan=False,sort_keys=True)+'\n')

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def check_file(path,expected):
    p=Path(path).resolve()
    if not p.is_file() or not expected or sha(p)!=expected:raise RuntimeError('ARTIFACT_INTEGRITY: missing/changed '+p.name)
    return p

def safe_path(root,rel):
    root=Path(root).resolve();p=(root/rel).resolve()
    try:p.relative_to(root)
    except ValueError:raise RuntimeError('PATH_ESCAPE: file outside declared root')
    return p

def offline():
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',WANDB_MODE='disabled',WANDB_DISABLED='true',YOLO_AUTOINSTALL='false')
    def deny(*a,**k):raise RuntimeError('NETWORK_DISABLED: supply local versioned assets; no download fallback')
    socket.create_connection=deny
    socket.socket.connect=deny

def dependency(name,expected=None):
    try:version=importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:raise RuntimeError('DEPENDENCY_UNAVAILABLE: '+name)
    if expected and version!=expected:raise RuntimeError('DEPENDENCY_VERSION: expected '+name+'=='+expected+', found '+version)
    return version

def error_code(exc):
    """Keep arbitrary validation messages/URLs out of the machine-readable code."""
    import re
    if isinstance(exc,ImportError):return 'DEPENDENCY_UNAVAILABLE'
    declared=getattr(exc,'code',None)
    if isinstance(declared,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,79}',declared):return declared
    prefix=str(exc).split(':',1)[0]
    if re.fullmatch(r'[A-Z][A-Z0-9_]{1,79}',prefix):return prefix
    if isinstance(exc,ValueError):return 'VALIDATION_ERROR'
    if isinstance(exc,FileNotFoundError):return 'ARTIFACT_MISSING'
    if isinstance(exc,PermissionError):return 'PERMISSION_DENIED'
    if isinstance(exc,(KeyError,TypeError)):return 'VALIDATION_ERROR'
    if isinstance(exc,OSError):return 'IO_ERROR'
    return 'INTERNAL_ERROR'

def main(handler):
    p=argparse.ArgumentParser();p.add_argument('--request',required=True);p.add_argument('--response',required=True);a=p.parse_args()
    try:
        req=read(a.request)
        if req.get('protocol_version')!='1.0':raise RuntimeError('PROTOCOL_VERSION: expected 1.0')
        result=handler(req)
        value={'schema_version':'1.0','protocol_version':'1.0','status':'SUCCEEDED','result':result,'error':None}
    except Exception as exc:
        message=str(exc);code=error_code(exc)
        value={'schema_version':'1.0','protocol_version':'1.0','status':'FAILED','result':{},'error':{'code':code,'message':message}}
    write(a.response,value)

# Stable public alias used by 0.4 standalone services.
file_hash = sha
