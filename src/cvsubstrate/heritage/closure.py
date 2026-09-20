"""Static executable-config dependency closure with unresolved inputs retained.

Does not import a config or inspect arbitrary environment values. Every copied
local module/base has an independent digest. Dynamic imports/env lookups are
reported, not interpreted. A complete *static* closure is not a security claim.
"""
from __future__ import annotations
import ast,os,subprocess
from pathlib import Path
from cvsubstrate.provenance.io import file_digest,digest,write_json,safe_join
from cvsubstrate.provenance.artifact_set import seal_directory
from cvsubstrate.errors import CVRSError

def config_closure(config:Path,source_root:Path,*,environment_names=(),environment_values=None):
    root=Path(source_root).resolve();start=Path(config).resolve()
    if not start.is_relative_to(root):raise CVRSError('CONFIG_ROOT','config outside declared source root')
    files={};edges=[];unresolved=[];seen=set();env_access=set();imports=set()
    def local_module(name,relative_to):
        choices=[relative_to.joinpath(*name.split('.')).with_suffix('.py'),root.joinpath(*name.split('.')).with_suffix('.py'),root.joinpath(*name.split('.'))/'__init__.py']
        return next((p for p in choices if p.is_file() and p.resolve().is_relative_to(root)),None)
    def visit(path):
        p=Path(path).resolve()
        if not p.is_relative_to(root):raise CVRSError('CONFIG_ESCAPE','dependency outside source root')
        rel=p.relative_to(root).as_posix()
        if rel in seen:return
        seen.add(rel)
        if p.is_symlink() or not p.is_file():unresolved.append({'file':rel,'reason':'missing local file'});return
        files[rel]=file_digest(p)
        try:tree=ast.parse(p.read_text('utf-8'),filename=rel)
        except (SyntaxError,UnicodeDecodeError):unresolved.append({'file':rel,'reason':'unparseable Python'});return
        for node in ast.walk(tree):
            if isinstance(node,(ast.Assign,ast.AnnAssign)):
                targets=node.targets if isinstance(node,ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target,ast.Name) and target.id in {'_base_','custom_imports'}:
                        try:value=ast.literal_eval(node.value)
                        except (ValueError,TypeError):unresolved.append({'file':rel,'reason':'dynamic '+target.id});continue
                        if target.id=='_base_':
                            values=[value] if isinstance(value,str) else value
                            if not isinstance(values,(list,tuple)):unresolved.append({'file':rel,'reason':'nonliteral bases'});continue
                            for base in values:
                                if not isinstance(base,str) or '::' in base:unresolved.append({'file':rel,'reason':'package/dynamic base','reference':str(base)});continue
                                dest=(p.parent/base).resolve()
                                if not dest.is_relative_to(root):unresolved.append({'file':rel,'reason':'external base','reference':base});continue
                                edges.append({'from':rel,'to':dest.relative_to(root).as_posix(),'type':'base'});visit(dest)
                        elif isinstance(value,dict):
                            for name in value.get('imports',[]):
                                dest=local_module(name,p.parent)
                                if dest:edges.append({'from':rel,'to':dest.relative_to(root).as_posix(),'type':'custom_import'});visit(dest)
                                else:imports.add(name)
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                names=[x.name for x in node.names] if isinstance(node,ast.Import) else [node.module or '']
                for name in names:
                    if not name:unresolved.append({'file':rel,'reason':'relative imported members need explicit closure'});continue
                    dest=local_module(name,p.parent)
                    if dest:edges.append({'from':rel,'to':dest.relative_to(root).as_posix(),'type':'python_import'});visit(dest)
                    else:imports.add(name)
            if isinstance(node,ast.Call):
                fn=ast.unparse(node.func)
                if fn in {'os.getenv','os.environ.get','environ.get'}:
                    if node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str):env_access.add(node.args[0].value)
                    else:unresolved.append({'file':rel,'reason':'dynamic environment lookup'})
                if fn in {'__import__','importlib.import_module','eval','exec'}:unresolved.append({'file':rel,'reason':'dynamic execution/import','line':node.lineno})
            if isinstance(node,ast.Subscript) and ast.unparse(node.value) in {'os.environ','environ'}:
                if isinstance(node.slice,ast.Constant) and isinstance(node.slice.value,str):env_access.add(node.slice.value)
                else:unresolved.append({'file':rel,'reason':'dynamic environment key'})
    visit(start)
    allowed=set(environment_names);provided=environment_values or {};env={}
    for name in sorted(env_access|allowed):
        # Store salted-independent content identity, not secrets; low-entropy hashes
        # are still sensitive. Caller must explicitly authorize each name.
        if name not in allowed:env[name]={'status':'UNDECLARED'}
        elif name in provided:env[name]={'status':'DECLARED','value_digest':digest({'name':name,'value':provided[name]})}
        else:env[name]={'status':'MISSING'}
    git={'commit':None,'dirty':None}
    try:
        git['commit']=subprocess.run(['git','-C',str(root),'rev-parse','HEAD'],capture_output=True,text=True,check=True,timeout=5).stdout.strip()
        git['dirty']=bool(subprocess.run(['git','-C',str(root),'status','--porcelain'],capture_output=True,text=True,check=True,timeout=5).stdout.strip())
    except (OSError,subprocess.SubprocessError):pass
    body={'format':'cvrs-config-closure/1.0','root_config':start.relative_to(root).as_posix(),'files':dict(sorted(files.items())),
          'edges':sorted(edges,key=digest),'external_modules':sorted(imports),'environment':env,'unresolved':unresolved,'git':git}
    return {**body,'closure_digest':digest(body),'status':'PARTIAL' if unresolved or any(x['status']!='DECLARED' for x in env.values()) else 'STATIC_CLOSURE',
            'dynamic_resolution_executed':False}

def preserve_closure(config,root,output,**kwargs):
    out=Path(output)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','closure is a new artifact')
    report=config_closure(config,root,**kwargs);out.mkdir(parents=True)
    for rel,sha in report['files'].items():
        src=safe_join(Path(root),rel);dest=safe_join(out/'files',rel);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(src.read_bytes())
        if file_digest(dest)!=sha:raise CVRSError('CONFIG_CHANGED','config changed during preservation')
    write_json(out/'closure.json',report);seal_directory(out);return report
