"""Portable, offline research browser. Source artifacts remain read-only."""
from __future__ import annotations
import html
import importlib.resources as resources
import json
import math
import sqlite3
from pathlib import Path
from typing import Any
from cvsubstrate.adoption.common import output_tree,write_text
from cvsubstrate.provenance.io import read_json,write_json,digest,file_digest
from cvsubstrate.security import sanitize


def _json(path,limit=2*1024*1024):
    if not path.is_file() or path.is_symlink():return None
    if path.stat().st_size>limit:raise ValueError('metadata exceeds browser byte limit')
    return read_json(path)


def _metrics(value,prefix=''):
    result={}
    if isinstance(value,dict):
        for k,v in value.items():result.update(_metrics(v,prefix+'.'+k if prefix else k))
    elif isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value):result[prefix]=value
    return result


def collect_catalog(source: Path, *, verify=False,max_records=5000):
    root=Path(source).resolve()
    if not root.is_dir():raise ValueError('site source must be an existing local directory')
    runs: list[dict[str, Any]]=[];models: dict[str, dict[str, Any]]={};datasets: dict[str, dict[str, Any]]={};claims: list[dict[str, Any]]=[];attempts: list[dict[str, Any]]=[];edges: list[dict[str, Any]]=[];issues: list[dict[str, Any]]=[]
    candidates: list[Path]=[]
    # Explicit metadata files only: never enumerate or include media/checkpoints.
    for filename in ('artifacts.json','run.json','run_manifest.json'):
        for p in root.rglob(filename):
            if p.is_symlink() or any(x in {'history','recovery','node_modules','.git'} for x in p.relative_to(root).parts):continue
            candidates.append(p.parent)
    for p in sorted(set(candidates))[:max_records]:
        try:
            run=_json(p/'run.json') or _json(p/'run_manifest.json') or {}
            experiment=_json(p/'experiment.json') or {}
            if not experiment and not run:continue
            evaluation=_json(p/'evaluation.json') or experiment.get('evaluation') or {}
            env=_json(p/'environment.json') or {}
            ms=_json(p/'metrics.json') or {}
            data=_json(p/'dataset_manifest.json') or {}
            model=experiment.get('model') or _json(p/'model.json') or {}
            if not model and experiment.get('adapter'):
                worker=_json(p/'worker_result.json') or {}
                model={'adapter':experiment['adapter'], 'input_checkpoint':experiment.get('checkpoint'),
                       'result_checkpoint_sha256':worker.get('checkpoint_sha256'),
                       'identity_scope':'declared adapter/config and recorded checkpoint bytes'}
            model_id='model:'+digest(model) if model else None
            data_id='dataset:'+digest(data) if data else None
            ident='run:'+digest({'source':p.relative_to(root).as_posix(),'run':run,'experiment':experiment})
            integrity='NOT_CHECKED'
            if verify and (p/'artifacts.json').is_file():
                from cvsubstrate.provenance.bundle import verify_bundle
                integrity=verify_bundle(p)['status']
            task=experiment.get('task') or evaluation.get('task') or (model.get('task') if isinstance(model,dict) else None) or 'unknown'
            record={'id':ident,'title':run.get('run_id',run.get('id',p.name)),'kind':'run',
                    'task':task,'status':run.get('status',run.get('state','RECORDED')),'integrity':integrity,
                    'purpose':data.get('purpose',experiment.get('purpose','unknown')),
                    'model_id':model_id,'dataset_id':data_id,
                    'protocol_id':'evaluation:'+digest(evaluation) if evaluation else None,
                    'metrics':_metrics(ms),'metric_details':ms,'experiment':experiment,'environment':env,
                    'source_label':p.relative_to(root).as_posix(),
                    'research_reproduction':'NOT_INFERRED_FROM_RUN_INTEGRITY'}
            runs.append(sanitize(record))
            if model_id:models[model_id]=sanitize({'id':model_id,'kind':'model','title':str(model.get('name',(model.get('adapter',{}).get('name') if isinstance(model.get('adapter'),dict) else model.get('adapter')) or model.get('backend','Model'))),
                 'task':task,'definition':model,'status':'DECLARED','native_compatibility':'NOT_INFERRED'})
            if data_id:datasets[data_id]=sanitize({'id':data_id,'kind':'dataset','title':data.get('name','Dataset'),'task':task,
                 'purpose':data.get('purpose','unknown'),'sample_count':len(data.get('samples',[])),
                 'categories':data.get('categories',[]),'split_roles':{k:{'role':v.get('role'),'samples':len(v.get('sample_ids',[]))} for k,v in data.get('splits',{}).items()},
                 'licenses':data.get('licenses',{}),'status':'MANIFEST_RECORDED'})
        except Exception as e:issues.append({'path':p.relative_to(root).as_posix(),'reason':sanitize(str(e))})
    registry_files=set(root.rglob('registry-v2.sqlite')) | set(root.rglob('registry.sqlite'))
    for db in sorted(registry_files):
        if db.is_symlink() or len(claims)+len(attempts)>=max_records:continue
        try:
            conn=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
            try:
                conn.execute('PRAGMA query_only=ON');conn.execute('PRAGMA trusted_schema=OFF');conn.execute('BEGIN')
                for ident,kind,payload in conn.execute('SELECT id,kind,payload FROM records ORDER BY id LIMIT ?',(max_records,)):
                    if len(payload)>2*1024*1024:raise ValueError('registry record too large for site export')
                    value=json.loads(payload)
                    if digest({'kind':kind,'payload':value})!=ident:raise ValueError('registry content digest mismatch')
                    rec=sanitize({'id':ident,'kind':kind,'title':value.get('title',value.get('attempt_kind',value.get('claim_id',ident[:12]))),
                          'status':value.get('status',value.get('outcome','RECORDED')),'attempt_kind':value.get('attempt_kind'),'purpose':value.get('purpose','unknown'),
                          'integrity':'RECORD_DIGEST_CHECKED','payload':value})
                    if kind=='claim':claims.append(rec)
                    elif kind=='attempt':attempts.append(rec)
                columns={row[1] for row in conn.execute('PRAGMA table_info(edges)')}
                if {'id','payload'}<=columns:
                    for ident,payload in conn.execute('SELECT id,payload FROM edges ORDER BY id LIMIT ?',(max_records*4,)):
                        value=json.loads(payload)
                        if digest(value)!=ident:raise ValueError('registry edge digest mismatch')
                        edges.append(sanitize({'id':ident,**value}))
                elif {'source','target','reason'}<=columns:
                    for source_id,target_id,reason in conn.execute('SELECT source,target,reason FROM edges ORDER BY source,target LIMIT ?',(max_records*4,)):
                        value={'source':source_id,'target':target_id,'relation':'superseded_by','reason':reason}
                        edges.append(sanitize({'id':digest(value),**value,'integrity':'LEGACY_EDGE_READ_ONLY'}))
                else:raise ValueError('unsupported registry edge schema')
            finally:conn.close()
        except Exception as e:issues.append({'path':db.relative_to(root).as_posix(),'reason':sanitize(str(e))})
    claims=list({r['id']:r for r in claims}.values())
    attempts=list({r['id']:r for r in attempts}.values())
    edges=list({r['id']:r for r in edges}.values())
    from cvsubstrate._version import __version__
    result={'format':'cvrs-static-browser/1','version':__version__,'title':'CV Research Substrate',
        'runs':runs,'models':list(models.values()),'datasets':list(datasets.values()),'claims':claims,'attempts':attempts,'edges':edges,
        'issues':issues,'truncated':len(set(candidates))>max_records,
        'notice':'Artifact integrity is not model compatibility, benchmark reproduction or independent verification. No media, checkpoint bytes or credentials are intentionally exported. Review metadata before public sharing.'}
    result['catalog_digest']=digest(result)
    return result


def render_browser(catalog: dict,destination: Path):
    required={'runs','models','datasets','claims','attempts','edges','issues'}
    if not required<=catalog.keys():raise ValueError('incomplete research browser catalogue')
    with output_tree(destination,seal=False) as out:
        assets=resources.files('cvsubstrate').joinpath('resources','product_ui')
        for name in ('app.js','app.css'):
            write_text(out/name,assets.joinpath(name).read_text('utf-8'))
        data=json.dumps(catalog,ensure_ascii=False,allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
        template=assets.joinpath('index.html').read_text('utf-8')
        write_text(out/'index.html',template.replace('__CATALOG__',data).replace('__VERSION__',html.escape(catalog.get('version','unknown'))))
        write_json(out/'catalog.json',catalog)
        write_text(out/'README.md','# Static research browser\n\nOpen `index.html` directly, or serve this directory on a static host. No accounts, CDN or backend are required. Metadata should be reviewed before publication. The JSON catalogue is the same data rendered in the browser.\n')
    return {'status':'BUILT','output':str(destination),'runs':len(catalog['runs']),'claims':len(catalog['claims']),
            'external_network_required':False,'source_modified':False,'issues':catalog['issues']}


def build_browser(source: Path,destination: Path,*,verify=False):
    if destination.resolve().is_relative_to(source.resolve()):raise ValueError('static export must be outside source artifacts')
    return render_browser(collect_catalog(source,verify=verify),destination)


def build_portal(source: Path,destination: Path):
    """Versioned, offline searchable documentation over the existing renderer."""
    from cvsubstrate.publication.site import build_docs,link_check
    from cvsubstrate.release import source_version
    __version__=source_version(Path(source))
    result=build_docs(source,destination)
    pages=[]
    for p in sorted((Path(source)/'docs/public').rglob('*.md')):
        text=p.read_text('utf-8')
        pages.append({'title':next((x.lstrip('# ').strip() for x in text.splitlines() if x.startswith('# ')),p.stem),
                      'path':p.relative_to(Path(source)/'docs/public').with_suffix('.html').as_posix(),'text':text[:120000]})
    js='''"use strict";
const field=document.querySelector('#docs-search');const results=document.querySelector('#docs-results');
const data=JSON.parse(document.querySelector('#docs-data').textContent);
field.addEventListener('input',()=>{results.replaceChildren();const q=field.value.trim().toLocaleLowerCase();
if(!q)return;for(const p of data.filter(x=>(x.title+' '+x.text).toLocaleLowerCase().includes(q)).slice(0,30)){
const li=document.createElement('li');const a=document.createElement('a');a.href=p.path;a.textContent=p.title;li.append(a);results.append(li);}});
'''
    write_text(destination/'search.js',js)
    safe=json.dumps(pages,ensure_ascii=False).replace('<','\\u003c').replace('&','\\u0026')
    from cvsubstrate.publication.site import page
    body='<h1>Search documentation</h1><p>Release '+html.escape(__version__)+' · offline search</p><label for="docs-search">Search concepts, commands and examples</label><br><input id="docs-search" type="search" autofocus><ul id="docs-results" aria-live="polite"></ul><script id="docs-data" type="application/json">'+safe+'</script><script src="search.js"></script>'
    write_text(destination/'search.html',page('Search',body,'<a href="index.html">Documentation</a>'))
    for p in destination.rglob('*.html'):
        if p.name=='search.html':continue
        depth=len(p.relative_to(destination).parts)-1
        text=p.read_text('utf-8').replace('<nav>','<nav><a href="'+('../'*depth)+'search.html">Search</a> ')
        text=text.replace('<footer>','<footer><span>Release '+html.escape(__version__)+'</span> · ')
        p.write_text(text,encoding='utf-8')
    write_json(destination/'versions.json',{'current':__version__,'available':[__version__],
               'archive_policy':'Publish older generated directories alongside this one; never relabel old docs as current.'})
    return {**result,'searchable_pages':len(pages),'version':__version__,'links':link_check(destination)}


def versioned_portal(portals: list[Path], destination: Path):
    """Assemble already-generated versions without rebuilding or relabeling them.

    Each input must declare its own current version in versions.json. Only static
    site files are copied, with per-file hashes in the output catalogue. This
    does not download past releases or claim those releases were reproduced.
    """
    import shutil
    import re
    from packaging.version import Version
    from cvsubstrate.publication.site import page,link_check
    if not portals:raise ValueError('provide one or more completed docs portals')
    source_versions={}
    for source in portals:
        source=Path(source).resolve();manifest=read_json(source/'versions.json');version=manifest['current']
        if not re.fullmatch(r'[0-9][A-Za-z0-9.+-]*',version):raise ValueError('unsafe documentation version')
        Version(version)
        if version in source_versions:raise ValueError('duplicate documentation version; never overwrite an archive')
        if not (source/'index.html').is_file():raise ValueError('documentation index is missing')
        source_versions[version]=source
    versions=sorted(source_versions,key=Version,reverse=True)
    inventory=[]
    with output_tree(destination,seal=False) as out:
        for version,source in source_versions.items():
            for p in sorted(source.rglob('*')):
                if p.is_symlink():raise ValueError('documentation archive contains a symlink')
                if not p.is_file():continue
                if p.suffix.lower() not in {'.html','.css','.js','.json','.svg','.png','.jpg','.webp','.txt','.xml'} and p.name!='.nojekyll':
                    raise ValueError('non-static artifact in documentation archive: '+p.name)
                if p.stat().st_size>16*1024*1024:raise ValueError('oversized documentation asset')
                dest=out/'versions'/version/p.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
                inventory.append({'path':dest.relative_to(out).as_posix(),'sha256':file_digest(dest),'bytes':dest.stat().st_size})
        body='<h1>CVRS documentation versions</h1><p>These are preserved documentation builds, not compatibility certifications.</p><ul>'+''.join(
            '<li><a href="versions/'+html.escape(v)+'/index.html">'+html.escape(v)+('</a> · newest supplied' if v==versions[0] else '</a>')+'</li>' for v in versions)+'</ul>'
        write_text(out/'index.html',page('Documentation versions',body));write_text(out/'.nojekyll','')
        write_json(out/'versions.json',{'current':versions[0],'available':versions,'files':inventory})
    return {'status':'ASSEMBLED','versions':versions,'files':len(inventory),'output':str(destination),'links':link_check(destination)}
