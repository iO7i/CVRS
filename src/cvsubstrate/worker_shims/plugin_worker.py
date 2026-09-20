"""Explicitly trusted external Python plugin execution; JSON transport only."""
import importlib,importlib.util,json
from pathlib import Path
from runtime_common import main,write,offline,file_hash

def run(request):
    descriptor=request['descriptor'];operation=request['operation'];out=Path(request.get('output_dir','.'))
    if operation!='capabilities':out.mkdir(parents=True,exist_ok=True)
    if not descriptor.get('trust_code'):raise ValueError('PLUGIN_TRUST: explicit plugin code trust required')
    if descriptor.get('protocol_version')!='1.0':raise ValueError('PROTOCOL_VERSION: unsupported plugin protocol')
    module_name,attribute=descriptor['target'].split(':',1)
    if operation not in descriptor['operations'] and operation!='capabilities':raise ValueError('UNSUPPORTED_CAPABILITY: operation not declared')
    offline();module=importlib.import_module(module_name);factory=getattr(module,attribute);plugin=factory()
    source=Path(module.__file__)
    if request.get('source_sha256') and file_hash(source)!=request['source_sha256']:raise ValueError('PLUGIN_IDENTITY: module source changed')
    try:
        capabilities=plugin.capabilities()
        if not isinstance(capabilities,dict) or capabilities.get('protocol_version')!='1.0':raise ValueError('WORKER_PROTOCOL: invalid capabilities')
        if operation=='capabilities':value=capabilities
        else:
            method=getattr(plugin,operation,None)
            if not callable(method):raise ValueError('UNSUPPORTED_CAPABILITY: method missing')
            value=method({**request.get('payload',{}),'artifact_directory':str(out.resolve())})
        if not isinstance(value,dict):raise ValueError('WORKER_PROTOCOL: plugin result must be a mapping')
        json.dumps(value,allow_nan=False)
        return {'plugin':descriptor['id'],'operation':operation,'result':value,'module_source_sha256':file_hash(source),
            'capabilities':capabilities,'isolation':'trusted subprocess, not a security sandbox'}
    finally:
        close=getattr(plugin,'close',None)
        if callable(close):close()

if __name__=='__main__':main(run)
