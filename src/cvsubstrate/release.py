"""Local release inventory/SBOM/wheel/archive automation. Never publishes remotely."""
from __future__ import annotations
from pathlib import Path
import ast,hashlib,importlib.metadata,io,json,subprocess,sys,tokenize,zipfile,tomllib
from cvsubstrate.provenance.io import write_json,read_json,file_digest,digest
from cvsubstrate.errors import CVRSError
EXCLUDED={'.git','.venv','venv','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','build'}

def source_files(root):
    root=Path(root)
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root)
        if any(x in EXCLUDED or x.endswith('.egg-info') for x in rel.parts):continue
        if p.is_symlink():raise CVRSError('SYMLINK','release refuses symlinks')
        if p.is_file():yield p

def line_counts(root):
    root=Path(root);groups={'source':{'files':0,'physical_lines':0,'nonblank_lines':0,'code_lines_excluding_comments_docstrings':0},
        'tests':{'files':0,'physical_lines':0,'nonblank_lines':0,'code_lines_excluding_comments_docstrings':0},
        'tools_examples':{'files':0,'physical_lines':0,'nonblank_lines':0,'code_lines_excluding_comments_docstrings':0}}
    for p in source_files(root):
        if p.suffix!='.py':continue
        rel=p.relative_to(root);kind='source' if rel.parts[0]=='src' else 'tests' if rel.parts[0]=='tests' else 'tools_examples'
        text=p.read_text('utf-8');lines=text.splitlines();tree=ast.parse(text);excluded=set()
        for node in ast.walk(tree):
            if isinstance(node,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and node.body:
                first=node.body[0]
                if isinstance(first,ast.Expr) and isinstance(first.value,ast.Constant) and isinstance(first.value.value,str):excluded.update(range(first.lineno,first.end_lineno+1))
        code=set()
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type not in {tokenize.COMMENT,tokenize.NL,tokenize.NEWLINE,tokenize.ENCODING,tokenize.ENDMARKER,tokenize.INDENT,tokenize.DEDENT}:
                code.update(range(tok.start[0],tok.end[0]+1))
        g=groups[kind];g['files']+=1;g['physical_lines']+=len(lines);g['nonblank_lines']+=sum(bool(x.strip()) for x in lines);g['code_lines_excluding_comments_docstrings']+=len(code-excluded)
    return {'method':'physical UTF-8 Python source lines; token-based comment/docstring-excluded lines reported separately; generated JSON/Markdown/checkpoints not counted','groups':groups,
        'total_python_physical_lines':sum(x['physical_lines'] for x in groups.values())}

def sbom(root):
    root=Path(root);metadata=tomllib.loads((root/'pyproject.toml').read_text());project=metadata['project'];components=[]
    for d in sorted(importlib.metadata.distributions(),key=lambda x:(x.metadata.get('Name','').lower(),x.version)):
        name=d.metadata.get('Name')
        if not name:continue
        c={'type':'library','name':name,'version':d.version,'purl':f'pkg:pypi/{name.lower().replace("_","-")}@{d.version}',
            'properties':[{'name':'cvrs:inventory-scope','value':'installed build environment; not necessarily a runtime dependency'},
                {'name':'cvrs:reported-license-metadata','value':d.metadata.get('License-Expression') or d.metadata.get('License') or 'unknown'}]}
        components.append(c)
    return {'bomFormat':'CycloneDX','specVersion':'1.6','version':1,'metadata':{'component':{'type':'application','name':project['name'],'version':project.get('version') or source_version(root)},
        'properties':[{'name':'cvrs:declared-core-requirements','value':json.dumps(project.get('dependencies',[]))},
            {'name':'cvrs:declared-optional-requirements','value':json.dumps(project.get('optional-dependencies',{}))}]},'components':components}

def package_release(root:Path,output:Path,*,build_wheel=False):
    root=Path(root).resolve();out=Path(output).resolve()
    if out.is_relative_to(root):raise ValueError('release ZIP must be outside repository')
    if out.exists():raise CVRSError('OUTPUT_EXISTS','release path already exists')
    metadata=tomllib.loads((root/'pyproject.toml').read_text())['project']
    if build_wheel:
        from cvsubstrate.execution.process import run_command
        run_command([sys.executable,'-m','pip','wheel',str(root),'--no-deps','--no-build-isolation','--wheel-dir',str(root/'dist')],180,cwd=root)
    write_json(root/'SBOM.cdx.json',sbom(root));write_json(root/'LINE_COUNTS.json',line_counts(root))
    manifest={p.relative_to(root).as_posix():{'sha256':file_digest(p),'bytes':p.stat().st_size} for p in source_files(root) if p.relative_to(root).as_posix()!='RELEASE_MANIFEST.json'}
    write_json(root/'RELEASE_MANIFEST.json',{'format':'cvrs-release-manifest','version':'1.0','package_version':metadata.get('version') or source_version(root),'files':manifest})
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in source_files(root):z.write(p,Path(root.name)/p.relative_to(root))
    checksum=file_digest(out);out.with_name(out.name+'.sha256').write_text(checksum+'  '+out.name+'\n','utf-8')
    return {'archive':str(out),'sha256':checksum,'bytes':out.stat().st_size,'manifest_files':len(manifest),'version':metadata.get('version') or source_version(root)}

def verify_release(root):
    root=Path(root);m=read_json(root/'RELEASE_MANIFEST.json');actual={p.relative_to(root).as_posix() for p in source_files(root)}-{'RELEASE_MANIFEST.json'}
    expected=set(m['files']);fail=[]
    for rel,r in m['files'].items():
        from cvsubstrate.provenance.io import safe_join
        p=safe_join(root,rel)
        if not p.is_file() or file_digest(p)!=r['sha256'] or p.stat().st_size!=r['bytes']:fail.append(rel)
    return {'status':'VERIFIED' if not fail and actual==expected else 'FAILED','files':len(expected),'mismatches':fail,'extra':sorted(actual-expected),'missing':sorted(expected-actual)}


def prepare_release(root:Path,output:Path,version:str,notes:list[str]):
    """Create a new versioned source copy and changelog without editing the source."""
    import re,shutil
    root=Path(root).resolve();output=Path(output).resolve()
    if output.exists() or output.is_relative_to(root):raise CVRSError('OUTPUT_EXISTS','new release preparation must be outside original root')
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:(?:a|b|rc)[0-9]+)?',version):raise ValueError('explicit normalized release or prerelease version required')
    if not notes or any(not x.strip() or '\n' in x for x in notes):raise ValueError('nonempty single-line changelog notes required')
    output.mkdir(parents=True)
    for p in source_files(root):
        rel=p.relative_to(root)
        if rel.parts[0]=='dist' or rel.as_posix() in {'RELEASE_MANIFEST.json','SBOM.cdx.json','LINE_COUNTS.json'}:continue
        target=output/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    project=output/'pyproject.toml';text=project.read_text();old=source_version(output)
    text=text.replace('version = "'+old+'"','version = "'+version+'"',1);project.write_text(text)
    m=tomllib.loads((output/'pyproject.toml').read_text())
    attr=m.get('tool',{}).get('setuptools',{}).get('dynamic',{}).get('version',{}).get('attr','cvsubstrate.__version__')
    module,_,symbol=attr.rpartition('.')
    init=output/'src'/Path(*module.split('.')).with_suffix('.py')
    if not init.exists():init=output/'src'/Path(*module.split('.'))/'__init__.py'
    value=init.read_text();value=re.sub(r'(?m)^__version__\s*=\s*[\"\'][^\"\']+[\"\']', '__version__ = '+repr(version),value,count=1);init.write_text(value)
    if source_version(output)!=version:raise ValueError('prepared source version did not update')
    log=output/'CHANGELOG.md';previous=log.read_text() if log.exists() else '# Changelog\n'
    entry='\n## '+version+' — prepared, not verified\n\n'+'\n'.join('- '+x for x in notes)+'\n'
    log.write_text(previous.replace('# Changelog','# Changelog\n'+entry,1))
    report={'status':'PREPARED','source_version':old,'version':version,'notes':notes,'validation':'NOT_RUN','limits':'Source copied and version/changelog updated; historical reports and scientific evidence retain their original meaning. Review current build report before release.'}
    write_json(output/'RELEASE_PREPARATION.json',report);return report


def source_version(root):
    """Read a static literal version without importing source or installed packages."""
    import ast,tomllib
    root=Path(root);metadata=tomllib.loads((root/'pyproject.toml').read_text());project=metadata['project']
    if project.get('version'):return project['version']
    attr=metadata.get('tool',{}).get('setuptools',{}).get('dynamic',{}).get('version',{}).get('attr','cvsubstrate._version.__version__')
    module,_,symbol=attr.rpartition('.')
    if not module or symbol!='__version__' or not all(x.isidentifier() for x in module.split('.')):raise ValueError('version source must be an explicit __version__ module attribute')
    for path in (root/'src'/Path(*module.split('.')).with_suffix('.py'),):
        if not path.exists():continue
        for node in ast.parse(path.read_text()).body:
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='__version__' for t in node.targets):return ast.literal_eval(node.value)
    raise ValueError('canonical version unavailable')
