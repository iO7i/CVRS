"""Offline model-index ingestion. Metadata becomes candidates, never certification."""
from __future__ import annotations
from pathlib import Path
from cvsubstrate.provenance.io import file_digest,digest,safe_join,write_json
from cvsubstrate.errors import DependencyUnavailable

def ingest_model_index(path:Path,root:Path|None=None):
    try:import yaml
    except ImportError as exc:raise DependencyUnavailable('PyYAML is required for model-index import') from exc
    start=Path(path).resolve();root=Path(root or start.parent).resolve();seen=set();models=[];collections=[];sources={}
    def visit(p):
        p=Path(p).resolve()
        if not p.is_relative_to(root):raise ValueError('model-index import escapes root')
        rel=p.relative_to(root).as_posix()
        if rel in seen:return
        seen.add(rel)
        if p.stat().st_size>16*1024*1024:raise ValueError('model index exceeds bound')
        data=yaml.safe_load(p.read_text('utf-8'))
        if not isinstance(data,dict):raise ValueError('model index root must be a mapping')
        sources[rel]=file_digest(p)
        for child in data.get('Import',[]):visit(safe_join(p.parent,child))
        for c in data.get('Collections',[]):collections.append(c)
        for m in data.get('Models',[]):
            if not isinstance(m,dict) or not m.get('Name'):raise ValueError('model entry needs Name')
            config=m.get('Config');candidate={'name':m['Name'],'collection':m.get('In Collection'),'config':config,
                'weights_reference':m.get('Weights'),'metadata':m.get('Metadata',{}),'reported_results':m.get('Results',[]),
                'license_status':'UNKNOWN','compatibility':'H0_CATALOGUED','execution':'NOT_RUN',
                'source_file':rel,'source_sha256':sources[rel]}
            if config and isinstance(config,str) and '://' not in config:
                q=safe_join(root,config)
                candidate['config_sha256']=file_digest(q) if q.is_file() else None
            candidate['id']=digest(candidate);models.append(candidate)
    visit(start)
    return {'format':'cvrs-model-index-candidates/1.0','sources':sources,'models':sorted(models,key=lambda m:m['id']),
        'collections':collections,'status':'IMPORTED_UNVERIFIED','model_count':len(models),'assets_downloaded':False}
