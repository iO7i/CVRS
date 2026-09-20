"""Manage H0 metadata and generate reproducibility documentation; never auto-certify."""
from pathlib import Path
from cvsubstrate.heritage.catalogue import load_catalogue,CatalogueEntry
from cvsubstrate.provenance.io import read_json,write_json,atomic_bytes,digest
from cvsubstrate.errors import CVRSError

def search_catalogue(path:Path,query=''):
    entries=load_catalogue(path);q=query.casefold()
    return [e.model_dump(mode='json') for e in entries if q in (e.id+' '+e.family+' '+(e.notes or '')).casefold()]

def add_entry(path:Path,value,output:Path):
    entry=CatalogueEntry.model_validate(value);entries=load_catalogue(path)
    if any(e.id==entry.id for e in entries):raise CVRSError('CATALOGUE_DUPLICATE',entry.id)
    if Path(output).exists():raise CVRSError('OUTPUT_EXISTS','catalogue changes create a new version')
    entries.append(entry);write_json(output,{'schema_version':'1.0','entries':[e.model_dump(mode='json') for e in entries]})
    return {'entries':len(entries),'digest':digest(entries),'execution_claims_added':False}

def generate_docs(path:Path,output:Path):
    out=Path(output)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','new docs directory required')
    out.mkdir(parents=True);entries=load_catalogue(path)
    for e in entries:
        text=f'# {e.id}\n\n**H0 — metadata only; no execution certified.**\n\n'
        for label,value in [('Family',e.family),('Source',e.source_url),('Revision',e.source_ref),('Config',e.config_path),('Weights',e.checkpoint_url),('Weights SHA-256',e.checkpoint_sha256),('Published AP percentage points',e.reported_ap_percent),('Data protocol',e.dataset),('Notes',e.notes)]:
            text+=f'**{label}:** {value if value is not None else "UNKNOWN / NOT SUPPLIED"}\n\n'
        text+='## Reproduction\nCreate a heritage import using the exact source/config/checkpoint and dataset. Supply a trusted worker environment and exact taxonomy map. Published metric metadata alone cannot certify a run.\n'
        atomic_bytes(out/(e.id+'.md'),text.encode())
    return {'documents':len(entries),'status':'GENERATED'}
