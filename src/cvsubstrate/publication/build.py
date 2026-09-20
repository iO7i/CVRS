"""Local-only public packaging. Owner-preview and publishable release are distinct."""
from pathlib import Path
from typing import Any
import os,sys,shutil,subprocess,zipfile,hashlib,json
from cvsubstrate.adoption.common import write_text
from cvsubstrate.provenance.io import read_json,write_json,file_digest,digest

def deterministic_zip(source,archive,*,prefix=None):
    source=Path(source);archive=Path(archive)
    if archive.exists():raise ValueError('archive already exists')
    archive.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(source.rglob('*')):
            if not p.is_file() or p.is_symlink() or '__pycache__' in p.parts or '.pytest_cache' in p.parts:continue
            rel=p.relative_to(source).as_posix();name=(prefix.rstrip('/')+'/' if prefix else '')+rel
            zi=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));zi.external_attr=((0o100755 if p.stat().st_mode & 0o111 else 0o100644)<<16);zi.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(zi,p.read_bytes())
    write_text(archive.with_name(archive.name+'.sha256'),file_digest(archive)+'  '+archive.name+'\n')
    return {'archive':str(archive),'sha256':file_digest(archive),'bytes':archive.stat().st_size}

def publish_bundle(source,destination,*,preview=False,build_packages=True):
    from cvsubstrate.publication.audit import public_tree,audit_public
    from cvsubstrate.product.browser import build_portal
    from cvsubstrate.schemas.registry import export_schemas
    from cvsubstrate.release import sbom,source_version
    root=Path(destination).resolve();source=Path(source).resolve()
    if root.exists():raise ValueError('use a new publication destination')
    if root.is_relative_to(source):raise ValueError('publication output must be outside source')
    root.mkdir();state={'status':'STARTED','preview':preview}
    try:
        public=public_tree(source,root/'source',preview=preview)
        docs=build_portal(root/'source',root/'docs');export_schemas(root/'schemas')
        (root/'dist').mkdir();write_json(root/'sbom'/'build-environment.cdx.json',sbom(root/'source'))
        if build_packages:
            env={**os.environ,'SOURCE_DATE_EPOCH':'0','PYTHONHASHSEED':'0','SETUPTOOLS_SCM_PRETEND_VERSION':source_version(source)}
            # Explicit local build backend only. This does not fetch packages or run third-party model code.
            cmd=[sys.executable,'-c','import setuptools.build_meta as b; b.build_wheel('+repr(str(root/'dist'))+'); b.build_sdist('+repr(str(root/'dist'))+')']
            r=subprocess.run(cmd,cwd=root/'source',env=env,capture_output=True,text=True,timeout=180)
            write_text(root/'build.log',r.stdout+r.stderr)
            if r.returncode:raise RuntimeError('wheel/sdist build failed; see build.log')
            for p in (root/'source').glob('src/*.egg-info'):shutil.rmtree(p)
            shutil.rmtree(root/'source'/'build',ignore_errors=True)
        version=source_version(root/'source')
        archive=deterministic_zip(root/'source',root/'dist'/('source-'+version+'.zip'),prefix='cv-research-substrate-'+version)
        deterministic_zip(root/'docs',root/'dist'/('docs-'+version+'.zip'))
        deterministic_zip(root/'schemas',root/'dist'/('schemas-'+version+'.zip'))
        records: dict[str, dict[str, Any]]={p.relative_to(root).as_posix():{'sha256':file_digest(p),'bytes':p.stat().st_size}
                 for p in sorted(root.rglob('*')) if p.is_file() and not p.is_symlink() and p.name!='release-manifest.json'}
        write_text(root/'checksums'/'SHA256SUMS',''.join(v['sha256']+'  '+k+'\n' for k,v in records.items()))
        state={'status':'OWNER_PREVIEW' if preview and public['audit']['status']=='BLOCK' else 'LOCAL_RELEASE_PREPARED',
            'version':version,'published':False,'source_archive':archive,'records':records,'docs':docs,
            'identity_status':public['audit']['status'],'limits':'Source/archive deterministic; wheels/sdist are build artifacts with recorded hashes, not a bit-reproducible binary-build claim.'}
        write_json(root/'release-manifest.json',state);return state
    except BaseException as exc:
        write_json(root/'PUBLICATION_FAILURE.json',{'status':'FAILED','message':str(exc),'published':False});raise
