"""Artifact attribution inventory, not legal interpretation or inferred permissions."""
from pathlib import Path
from cvsubstrate.provenance.io import write_json,digest
from cvsubstrate.provenance.artifact_set import seal_directory
from cvsubstrate.errors import CVRSError
KINDS={'code','weights','dataset','annotations','config','paper','asset'}

def license_report(artifacts,output:Path):
    rows=[];ids=set()
    for item in artifacts:
        r=dict(item)
        if r.get('kind') not in KINDS:raise ValueError('artifact kind must be explicit')
        if not r.get('id') or r['id'] in ids:raise ValueError('unique artifact identity required')
        ids.add(r['id']);r.setdefault('license','unknown');r.setdefault('redistribution','unknown')
        if r['redistribution'] not in {'allowed','prohibited','unknown'}:raise ValueError('invalid redistribution status')
        if r['redistribution']=='allowed' and not r.get('permission_evidence'):raise ValueError('allowed redistribution requires source evidence')
        rows.append(r)
    out=Path(output)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','licensing reports are immutable derivations')
    out.mkdir(parents=True);report={'schema_version':'1.0','artifacts':rows,'unknown_license':[r['id'] for r in rows if r['license']=='unknown'],
        'do_not_bundle':[r['id'] for r in rows if r['redistribution']!='allowed'],
        'limits':'Repository license does not establish checkpoint/dataset permission. This report preserves supplied evidence, not legal advice.'}
    write_json(out/'licenses.json',report);write_json(out/'artifact-license-report.json',report)
    text=['# Third-party notices','','Original-code licensing remains the repository owner\'s decision.','']
    for r in rows:
        text += ['## '+r['id'],f"Kind: {r['kind']}",f"License: {r['license']}",f"Redistribution: {r['redistribution']}",
            f"Source: {r.get('source','unknown')}",f"Attribution: {r.get('attribution','not supplied')}",f"Evidence: {r.get('permission_evidence','not supplied')}",'']
    (out/'THIRD_PARTY_NOTICES.md').write_text('\n'.join(text),'utf-8');seal_directory(out);return report
