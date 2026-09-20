"""Export/import portable, unsigned research capsules; never execute their contents.

A capsule transports supplied evidence and dependency REFERENCES. It does not
make unbundled models or licensed datasets available. Archive extraction is bounded
and rejects traversal, duplicates, symlinks, and overwrite of existing destinations.
"""
from __future__ import annotations
import os,stat,shutil,tempfile,zipfile
from pathlib import Path,PurePosixPath
from cvsubstrate.provenance.io import read_json,write_json,file_digest,digest,safe_join
from cvsubstrate.provenance.artifact_set import seal_directory,verify_directory,assert_not_inside_sealed
from cvsubstrate.errors import CVRSError
from cvsubstrate.security import sanitize

MAX_FILES=20000
MAX_TOTAL=8*1024**3
MAX_MEMBER=4*1024**3

def create_capsule(source:Path,output:Path,*,include=None,external_references=None,dependency_closure=None):
    source=Path(source).resolve();output=Path(output).resolve()
    assert_not_inside_sealed(output)
    if output.exists() or output==source or output.is_relative_to(source):raise CVRSError('CAPSULE_LOCATION','new output outside source required')
    if not source.is_dir():raise ValueError('source directory required')
    if (source/'artifacts.json').exists():
        from cvsubstrate.provenance.bundle import verify_bundle
        v=verify_bundle(source)
    elif (source/'integrity.json').exists():v=verify_directory(source)
    else:v={'status':'UNSEALED_SOURCE','limits':'No source integrity statement was supplied'}
    if v['status'] not in {'VERIFIED','UNSEALED_SOURCE'}:raise CVRSError('ARTIFACT_INTEGRITY','source evidence failed integrity')
    paths=include or [p.relative_to(source).as_posix() for p in sorted(source.rglob('*')) if p.is_file()]
    if len(paths)>MAX_FILES:raise ValueError('too many capsule members')
    entries=[];total=0
    for rel in paths:
        raw=source/rel
        if any(part.is_symlink() for part in [raw,*raw.parents] if part!=source.parent):raise ValueError('source symlinks refused')
        p=safe_join(source,rel)
        if p.is_symlink() or not p.is_file():raise ValueError('regular source files only')
        size=p.stat().st_size;total+=size
        if size>MAX_MEMBER or total>MAX_TOTAL:raise ValueError('capsule size limit')
        entries.append({'path':rel,'sha256':file_digest(p),'bytes':size})
    output.mkdir(parents=True)
    for item in entries:
        dst=safe_join(output/'evidence',item['path']);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(safe_join(source,item['path']),dst)
        if file_digest(dst)!=item['sha256']:raise CVRSError('SOURCE_CHANGED','source changed while building capsule')
    closure_status=None
    if dependency_closure is not None:
        from cvsubstrate.artifacts.dependencies import DependencyClosure,inspect_closure
        closure=DependencyClosure.model_validate(dependency_closure)
        closure_status=inspect_closure(closure,output/'evidence')
        if any(d['disposition']=='EMBEDDED' and d['status']!='VERIFIED' for d in closure_status['dependencies']):
            raise CVRSError('CAPSULE_DEPENDENCY','an embedded dependency is not included with its declared hash')
        write_json(output/'dependencies.json',closure)
    refs=sanitize(external_references or [])
    manifest={'format':'cvrs-research-capsule','version':'1.0','source_verification':v,
        'evidence_digest':digest(entries),'files':entries,'external_references':refs,
        'portable_metadata':True,'payload_redacted':False,'dependency_closure_sha256':file_digest(output/'dependencies.json') if closure_status else None,
        'limits':['Unsigned integrity, not publisher authentication','Source evidence bytes are preserved and may contain original paths: review before public sharing','External data/weights not acquired; their licenses remain separate','Materialization does not install packages or execute code']}
    write_json(output/'capsule.json',manifest);seal_directory(output)
    return {'status':'CREATED','capsule':str(output),'files':len(entries),'bytes':total,'external_dependencies':len(refs),'dependency_closure':closure_status}

def validate_capsule(path:Path):
    path=Path(path);v=verify_directory(path)
    if v['status']!='VERIFIED':return v
    m=read_json(path/'capsule.json')
    if m.get('format')!='cvrs-research-capsule' or m.get('version')!='1.0':raise CVRSError('SCHEMA_MISMATCH','unsupported capsule')
    if digest(m['files'])!=m['evidence_digest']:raise CVRSError('ARTIFACT_INTEGRITY','capsule evidence identity mismatch')
    for r in m['files']:
        p=safe_join(path/'evidence',r['path'])
        if not p.is_file() or p.stat().st_size!=r['bytes'] or file_digest(p)!=r['sha256']:raise CVRSError('ARTIFACT_INTEGRITY','evidence changed')
    closure=None
    if m.get('dependency_closure_sha256'):
        from cvsubstrate.artifacts.dependencies import DependencyClosure,inspect_closure
        if file_digest(path/'dependencies.json')!=m['dependency_closure_sha256']:raise CVRSError('CAPSULE_DEPENDENCY','dependency declaration changed')
        closure=inspect_closure(DependencyClosure.model_validate(read_json(path/'dependencies.json')),path/'evidence')
        if any(d['disposition']=='EMBEDDED' and d['status']!='VERIFIED' for d in closure['dependencies']):raise CVRSError('CAPSULE_DEPENDENCY','embedded asset changed')
    return {'status':'VERIFIED','files':len(m['files']),'external_references':m['external_references'],'execution_verified':False,'dependency_closure':closure}

def archive_capsule(source:Path,zip_path:Path):
    v=validate_capsule(source)
    if v['status']!='VERIFIED':raise CVRSError('ARTIFACT_INTEGRITY','invalid capsule')
    target=Path(zip_path)
    if target.exists():raise CVRSError('OUTPUT_EXISTS','archive exists')
    target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(Path(source).rglob('*')):
            if p.is_file():z.write(p,p.relative_to(source).as_posix())
    return {'path':str(target),'sha256':file_digest(target),'bytes':target.stat().st_size}

def materialize_capsule(archive:Path,destination:Path):
    dst=Path(destination).resolve();assert_not_inside_sealed(dst)
    if dst.exists():raise CVRSError('OUTPUT_EXISTS','destination must not exist')
    dst.parent.mkdir(parents=True,exist_ok=True)
    temp=Path(tempfile.mkdtemp(prefix='.capsule-',dir=dst.parent))
    try:
        with zipfile.ZipFile(archive) as z:
            infos=z.infolist();names=set();total=0
            if len(infos)>MAX_FILES:raise ValueError('archive member limit')
            for info in infos:
                rel=info.filename
                if rel in names:raise ValueError('duplicate archive member')
                names.add(rel)
                if info.is_dir():continue
                if stat.S_ISLNK(info.external_attr>>16):raise ValueError('archive symlink refused')
                target=safe_join(temp,rel);total+=info.file_size
                if info.file_size>MAX_MEMBER or total>MAX_TOTAL:raise ValueError('archive uncompressed-size limit')
                target.parent.mkdir(parents=True,exist_ok=True)
                with z.open(info) as src,target.open('xb') as out:shutil.copyfileobj(src,out)
        v=validate_capsule(temp)
        if v['status']!='VERIFIED':raise CVRSError('ARTIFACT_INTEGRITY','invalid extracted capsule')
        os.replace(temp,dst);return {'status':'MATERIALIZED','destination':str(dst),'verification':v}
    finally:
        if temp.exists():shutil.rmtree(temp)
