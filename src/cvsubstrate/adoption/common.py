"""Bounded, non-executable configuration and immutable output utilities."""
from pathlib import Path
import contextlib, os, shutil, tempfile, json
from cvsubstrate.provenance.io import read_json, write_json, safe_join
from cvsubstrate.provenance.artifact_set import assert_not_inside_sealed, seal_directory
from cvsubstrate.errors import CVRSError

def load_config(path):
    p=Path(path)
    if p.stat().st_size > 8*1024*1024:raise CVRSError('CONFIG_SIZE','configuration exceeds 8 MiB')
    if p.suffix.lower() in {'.yaml','.yml'}:
        try:import yaml
        except ImportError:raise CVRSError('DEPENDENCY_UNAVAILABLE','install PyYAML in the controller, or use JSON')
        class UniqueLoader(yaml.SafeLoader):pass
        def mapping(loader,node,deep=False):
            result={}
            for k,v in node.value:
                key=loader.construct_object(k,deep=deep)
                if key in result:raise ValueError('duplicate YAML key')
                result[key]=loader.construct_object(v,deep=deep)
            return result
        UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,mapping)
        value=yaml.load(p.read_text('utf-8'),Loader=UniqueLoader)
        # Bounded depth catches aliases and recursive containers without code execution.
        budget=[100000]
        def walk(x,depth=0):
            budget[0]-=1
            if budget[0]<0:raise ValueError("configuration alias expansion exceeds node budget")
            if depth>40:raise ValueError('configuration nesting/aliases exceed limit')
            if isinstance(x,dict):
                for k,v in x.items():
                    if not isinstance(k,str):raise ValueError('configuration keys must be strings')
                    walk(v,depth+1)
            elif isinstance(x,list):
                for v in x:walk(v,depth+1)
        walk(value)
        json.dumps(value,allow_nan=False)
        return value
    return read_json(p)

@contextlib.contextmanager
def output_tree(destination,seal=True):
    out=Path(destination).resolve();assert_not_inside_sealed(out)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','use a new destination; source artifacts are never overwritten')
    out.parent.mkdir(parents=True,exist_ok=True)
    temp=Path(tempfile.mkdtemp(prefix='.'+out.name+'-',dir=out.parent))
    try:
        yield temp
        if seal:seal_directory(temp)
        os.rename(temp,out)
    except BaseException:
        shutil.rmtree(temp,ignore_errors=True)
        raise

def write_text(path,value):
    from cvsubstrate.provenance.io import atomic_bytes
    atomic_bytes(Path(path),value.encode('utf-8'))

def safe_files(root, *, max_files=10000,max_bytes=32*1024*1024, include=None):
    """Do not follow symlinks; deterministic and bounded. Caller sees truncation."""
    root=Path(root).resolve();entries: list[tuple[Path, str]]=[];total=0;truncated=False
    skip={'.git','.venv','venv','node_modules','__pycache__','.mypy_cache','.pytest_cache','dist','build','.cache'}
    for parent,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=sorted(d for d in dirs if d not in skip and not (Path(parent)/d).is_symlink())
        for name in sorted(files):
            p=Path(parent)/name
            if p.is_symlink():continue
            rel=p.relative_to(root).as_posix()
            if include and not include(p,rel):continue
            size=p.stat().st_size
            if len(entries)>=max_files or total+size>max_bytes:
                truncated=True;continue
            entries.append((p,rel));total+=size
    return entries,truncated


@contextlib.contextmanager
def execution_tree(destination):
    """Unlike pure-data output_tree, native SDKs keep stable absolute work paths."""
    out=Path(destination).resolve();assert_not_inside_sealed(out)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','use a new native execution directory')
    out.mkdir(parents=True)
    try:
        yield out
        seal_directory(out)
    except BaseException as exc:
        from cvsubstrate.errors import public_error
        from cvsubstrate.security import sanitize
        write_json(out/'FAILURE.json',{'status':'FAILED','error':sanitize(public_error(exc))})
        if not (out/'integrity.json').exists():seal_directory(out)
        raise
