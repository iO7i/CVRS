"""Read-only research-repository archaeology. Does not import the repository."""
from __future__ import annotations
import ast,re,subprocess,os,configparser,tomllib
from pathlib import Path
from cvsubstrate.adoption.common import safe_files,load_config
from cvsubstrate.adoption.contracts import RepositoryReport,SourceObservation
from cvsubstrate.provenance.io import file_digest,digest
from cvsubstrate.security import sanitize

FRAMEWORKS={'mmdet':'mmdetection','mmrotate':'mmrotate','mmseg':'mmsegmentation','mmyolo':'mmyolo',
 'mmdeploy':'mmdeploy','mmcv':'mmcv','mmengine':'mmengine','detectron2':'detectron2',
 'ultralytics':'ultralytics','rfdetr':'rfdetr','transformers':'transformers','timm':'timm',
 'torchgeo':'torchgeo','terratorch':'terratorch','sam2':'sam2','sam3':'sam3','segment_anything':'sam',
 'torch':'pytorch','torchvision':'torchvision','fiftyone':'fiftyone','supervision':'supervision','wandb':'wandb','mlflow':'mlflow'}

def git_state(root):
    root=Path(root).resolve()
    def run(*args):
        try:
            r=subprocess.run(['git','-c','core.fsmonitor=false','-C',str(root),*args],capture_output=True,timeout=10,
                             env={**os.environ,'GIT_OPTIONAL_LOCKS':'0','GIT_TERMINAL_PROMPT':'0'})
            return r.stdout.decode('utf-8','replace').strip() if r.returncode==0 else None
        except (OSError,subprocess.TimeoutExpired):return None
    revision=run('rev-parse','HEAD')
    if not revision:return {'available':False}
    status=run('status','--porcelain','--untracked-files=normal') or ''
    return {'available':True,'revision':revision,'dirty':bool(status),'status_digest':digest(status),
            'remote':sanitize(run('remote','get-url','origin') or ''),
            'submodule_declarations':(root/'.gitmodules').is_file()}

def inspect_repository(root,max_files=8000,max_bytes=48*1024*1024):
    root=Path(root).resolve()
    if not root.is_dir():raise ValueError('repository must be a local directory')
    def eligible(p,rel):return p.suffix.lower() in {'.py','.toml','.txt','.in','.yml','.yaml','.json','.md','.cfg','.sh','.cpp','.cc','.c','.cu','.cuh','.h','.hpp'} or p.name in {'Dockerfile','Makefile','uv.lock','Pipfile'}
    entries,truncated=safe_files(root,max_files=max_files,max_bytes=max_bytes,include=eligible)
    obs=[];frameworks=set();files={};candidates=[];unresolved=[]
    def add(rel,line,kind,value,confidence='literal'):
        obs.append(SourceObservation(path=rel,line=max(1,line),kind=kind,value=str(value)[:600],confidence=confidence))
    for p,rel in entries:
        files[rel]=file_digest(p)
        if p.stat().st_size>2*1024*1024:
            unresolved.append('file hashed but too large for static parse: '+rel);continue
        try:text=p.read_text('utf-8')
        except (UnicodeError,OSError):continue
        if p.suffix=='.py':
            try:tree=ast.parse(text)
            except SyntaxError:
                unresolved.append('Python syntax not parsed by this interpreter: '+rel);continue
            for node in ast.walk(tree):
                if isinstance(node,(ast.Import,ast.ImportFrom)):
                    names=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module or '']
                    for name in names:
                        add(rel,node.lineno,'import',name)
                        if name.split('.')[0] in FRAMEWORKS:frameworks.add(FRAMEWORKS[name.split('.')[0]])
                if isinstance(node,ast.Call) and ((isinstance(node.func,ast.Name) and node.func.id=='setup') or (isinstance(node.func,ast.Attribute) and node.func.attr=='setup')):
                    for kw in node.keywords:
                        if kw.arg in {'install_requires','python_requires'}:
                            try:
                                val=ast.literal_eval(kw.value)
                                if kw.arg=='python_requires':add(rel,node.lineno,'python_constraint',val)
                                elif isinstance(val,(list,tuple)):
                                    for req in val:add(rel,node.lineno,'requirement',req)
                            except (ValueError,TypeError):unresolved.append('dynamic setup dependency: '+rel)
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                    if node.func.attr in {'from_pretrained','load','hf_hub_download','snapshot_download'}:
                        if node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str):
                            add(rel,node.lineno,'model_asset_candidate',node.args[0].value,'candidate')
                    if (node.func.attr=='getenv' and isinstance(node.func.value,ast.Name) and node.func.value.id=='os') or (node.func.attr=='get' and isinstance(node.func.value,ast.Attribute) and node.func.value.attr=='environ'):
                        if node.args and isinstance(node.args[0],ast.Constant):add(rel,node.lineno,'environment_dependency',node.args[0].value)
                if isinstance(node,ast.Assign):
                    for t in node.targets:
                        if isinstance(t,ast.Name) and t.id in {'_base_','custom_imports'}:
                            try:add(rel,node.lineno,t.id,repr(ast.literal_eval(node.value)))
                            except (ValueError,TypeError):add(rel,node.lineno,'dynamic_config',t.id,'static_inference')
            if p.stem.lower() in {'train','test','eval','evaluate','infer','inference','predict','demo'}:
                op='train' if p.stem=='train' else 'predict'
                candidates.append({'operation':op,'argv':['${python}','${repo}/'+rel],
                                   'path':rel,'status':'REQUIRES_ARGUMENT_REVIEW','native_output_format':'unknown'})
        if p.name=='pyproject.toml':
            try:
                v=tomllib.loads(text);project=v.get('project',{})
                if project.get('requires-python'):add(rel,1,'python_constraint',project['requires-python'])
                for req in project.get('dependencies',[]):add(rel,1,'requirement',req)
                for group,reqs in project.get('optional-dependencies',{}).items():
                    for req in reqs:add(rel,1,'optional_requirement',group+':'+req)
            except (ValueError,TypeError):unresolved.append('invalid pyproject: '+rel)
        if (p.name.startswith('requirements') or 'requirements' in p.relative_to(root).parts) and p.suffix in {'.txt','.in'}:
            for line,s in enumerate(text.splitlines(),1):
                s=s.strip()
                if s and not s.startswith('#'):
                    if s.startswith(('-r','-c','-e','--')):add(rel,line,'requirement_directive',s)
                    else:add(rel,line,'requirement',s.split(' #',1)[0])
        if p.name=='setup.cfg':
            try:
                cfg=configparser.ConfigParser(interpolation=None);cfg.read_string(text)
                if cfg.has_option('options','python_requires'):add(rel,1,'python_constraint',cfg.get('options','python_requires'))
                if cfg.has_option('options','install_requires'):
                    for req in cfg.get('options','install_requires').splitlines():
                        if req.strip():add(rel,1,'requirement',req.strip())
            except configparser.Error:unresolved.append('setup.cfg not statically parsed: '+rel)
        if p.name in {'environment.yml','environment.yaml'}:
            try:
                env=load_config(p)
                for d in env.get('dependencies',[]):
                    if isinstance(d,str):add(rel,1,'conda_requirement',d)
                    elif isinstance(d,dict):
                        for req in d.get('pip',[]):add(rel,1,'requirement',req)
            except Exception:unresolved.append('environment YAML not resolved: '+rel)
        if p.name.startswith('Dockerfile'):
            for line,s in enumerate(text.splitlines(),1):
                if s.strip().upper().startswith('FROM '):add(rel,line,'container_base',s.strip()[5:])
        if p.suffix=='.md':
            for line,s in enumerate(text.splitlines(),1):
                for req in re.findall(r'\b(?:torch|torchvision|mmcv(?:-full)?|mmdet|mmsegmentation|python)(?:==|>=|<=|<|>)[0-9][\w.*+<>=!,.-]*',s):
                    add(rel,line,'documented_requirement',req,'candidate')
                for url in re.findall(r'https://(?:huggingface\.co|download\.openmmlab\.com)/[^\s)>"`]+',s):
                    add(rel,line,'asset_url_candidate',sanitize(url),'candidate')
        for f in FRAMEWORKS:
            if p.name.lower().startswith(f):frameworks.add(FRAMEWORKS[f])
    if len(frameworks-{'pytorch'})>1:
        unresolved.append('multiple frameworks do not prove separable stages; shared model code/autograd must stay in one compatible worker or be explicitly refactored')
    if not candidates:unresolved.append('no unambiguous training/inference entrypoint found')
    unresolved.append('native prediction/checkpoint locations and exact CLI arguments require author confirmation')
    return RepositoryReport(repository_name=root.name,root_identity=digest(files),files=files,
        observations=obs,frameworks=sorted(frameworks),command_candidates=candidates,
        unresolved=unresolved,git=git_state(root),truncated=truncated)
