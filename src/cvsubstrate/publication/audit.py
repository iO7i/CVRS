"""Deterministic public-source audit and allowlisted export. No auto-deletion."""
from __future__ import annotations
from pathlib import Path
import re,os,shutil,tomllib,json
from cvsubstrate.adoption.common import output_tree,write_text
from cvsubstrate.adoption.contracts import PublicationSettings
from cvsubstrate.provenance.io import read_json,write_json,file_digest,digest

PUBLIC_ROOTS={'src','tests','docs','examples','schemas','benchmarks','heritage','adapters','tools','scripts','.github','.devcontainer','rfcs','docker'}
PUBLIC_TOP={'pyproject.toml','MANIFEST.in','README.md','LICENSE','NOTICE','THIRD_PARTY_NOTICES.md','ARCHITECTURE.md','CHANGELOG.md','CONTRIBUTING.md','GOVERNANCE.md',
            'SECURITY.md','SUPPORT.md','ROADMAP.md','CODE_OF_CONDUCT.md','CITATION.cff','.codemeta.json','.gitignore','.gitattributes','.editorconfig','Makefile',
            'mkdocs.yml','PUBLICATION.json','PUBLIC_STATUS.json','PUBLIC_RELEASE_POLICY.json','RELEASE_NOTES.md'}
EXCLUDE_PARTS={'__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','.git','.venv','venv','node_modules','history','evidence','recovery','__artifacts__','native-smoke-final'}
ASSET_SUFFIXES={'.pt','.pth','.ckpt','.safetensors','.onnx','.engine','.plan','.bin','.zip','.tar','.gz','.db','.sqlite','.log','.whl'}
SECRETS=[('PRIVATE_KEY',re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ED25519 )?PRIVATE KEY-----')),
         ('GITHUB_TOKEN',re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b')),
         ('API_TOKEN',re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{35,}\b')),
         ('AWS_ACCESS',re.compile(r'\bAKIA[A-Z0-9]{16}\b'))]
MACHINE_PATH=re.compile(r'(?:/mnt/data/[A-Za-z0-9_.-]+|/home/[^/\s]+/[^\s"\']+|[A-Za-z]:\\Users\\[^\\\s]+\\[^\s"\']+)')

def settings(root):
    root=Path(root);p=root/'PUBLICATION.json'
    value=read_json(p) if p.exists() else {}
    return PublicationSettings.model_validate(value)

def audit_public(root,*,require_identity=True,max_file_bytes=2*1024*1024):
    root=Path(root).resolve();conf=settings(root);findings=[];checked=0
    def add(code,severity,path,message,line=None):
        findings.append({'code':code,'severity':severity,'path':path,'line':line,'message':message})
    if require_identity:
        if not conf.identity_approved:add('IDENTITY_PENDING','BLOCK','PUBLICATION.json','Owner must approve public project identity and maintainers')
        if not conf.license_approved or conf.license_id=='LicenseRef-Owner-Decision-Pending':
            add('LICENSE_PENDING','BLOCK','LICENSE','An approved license grant is required for an open-source release')
        if not conf.repository_url:add('REPOSITORY_UNSET','WARN','PUBLICATION.json','Final repository URL is not configured')
        if not conf.security_contact:add('SECURITY_CONTACT_UNSET','WARN','PUBLICATION.json','Configure a private vulnerability-reporting route')
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root).as_posix()
        if '.git' in p.relative_to(root).parts:continue
        if p.is_symlink():add('SYMLINK','BLOCK',rel,'Public export refuses symlinks');continue
        if not p.is_file():continue
        if any(x in {'__pycache__','.pytest_cache','.mypy_cache','.ruff_cache'} for x in p.relative_to(root).parts):continue
        checked+=1
        if p.stat().st_size>max_file_bytes:add('LARGE_FILE','WARN',rel,'Review large source-tree file before publication')
        if p.suffix.lower() in ASSET_SUFFIXES:add('BINARY_OR_SESSION_ARTIFACT','BLOCK',rel,'Model/data/session binaries are not allowed in clean public source')
        if p.stat().st_size>max_file_bytes:continue
        try:text=p.read_text('utf-8')
        except UnicodeError:continue
        for number,line in enumerate(text.splitlines(),1):
            for code,pattern in SECRETS:
                if pattern.search(line):add(code,'BLOCK',rel,'Possible credential or private key (value withheld)',number)
            if MACHINE_PATH.search(line):add('MACHINE_PATH','WARN',rel,'Machine-specific path; review whether intentional fixture or private material',number)
            for term in conf.private_terms:
                if term and term.lower() in line.lower():add('PRIVATE_TERM','BLOCK',rel,'Owner-defined private term detected (value withheld)',number)
            if re.search(r'\bTODO\b|\bFIXME\b',line):add('DEVELOPMENT_MARKER','WARN',rel,'Review unresolved development marker',number)
    return {'status':'BLOCK' if any(f['severity']=='BLOCK' for f in findings) else 'WARN' if findings else 'PASS',
            'files_scanned':checked,'findings':findings,'limits':'Pattern scan and allowlist, not proof that all secrets/private data are absent. Manual review remains required.'}

def _qualification_public_allowlist(source):
    source=Path(source)
    allowed={
        'qualification/FINAL_REPORT.md',
        'qualification/h2/H2_REVIEW.md',
        'qualification/h2/release-checks.json',
        'qualification/h2/cleanroom-report.json',
        'qualification/h2/pip-audit-release-final.json',
        'qualification/h2/qualification-matrix.json',
        'qualification/h2/browser/index.html',
        'qualification/h2/browser/app.css',
        'qualification/h2/browser/app.js',
        'qualification/h2/browser/browser-manifest.json',
        'qualification/h2/browser/qualification-matrix.json',
    }
    matrix=source/'qualification/h2/qualification-matrix.json'
    if matrix.is_file():
        for lane in read_json(matrix).get('lanes',[]):
            evidence=str(lane.get('evidence','')).replace('\\','/')
            if evidence.startswith('qualification/') and '..' not in Path(evidence).parts:
                allowed.add(evidence)
    return allowed

def public_tree(source,destination,*,preview=False):
    source=Path(source).resolve();destination=Path(destination).resolve()
    if destination.is_relative_to(source):raise ValueError('public output must be outside source tree')
    excluded=[];qualification_allowed=_qualification_public_allowlist(source)
    with output_tree(destination,seal=False) as out:
        for p in sorted(source.rglob('*')):
            if not p.is_file() and not p.is_symlink():continue
            rel=p.relative_to(source)
            if p.is_symlink():excluded.append({'path':rel.as_posix(),'reason':'symlink'});continue
            rel_posix=rel.as_posix()
            qualification_permitted=rel_posix in qualification_allowed
            permitted=(len(rel.parts)==1 and rel.name in PUBLIC_TOP) or (len(rel.parts)>1 and rel.parts[0] in PUBLIC_ROOTS) or qualification_permitted
            if any(x in EXCLUDE_PARTS or x.endswith('.egg-info') for x in rel.parts) and not qualification_permitted:permitted=False
            if p.suffix.lower() in ASSET_SUFFIXES:permitted=False
            if p.name in {'RELEASE_MANIFEST.json','integrity.json','BUILD_REPORT.md','IMPLEMENTATION_LEDGER.json','LINE_COUNTS.json'}:permitted=False
            if not permitted:excluded.append({'path':rel.as_posix(),'reason':'outside public source policy'});continue
            target=out/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target);shutil.copymode(p,target)
        audit=audit_public(out)
        # Always block credential findings, even for owner-preview mode.
        unsafe=[f for f in audit['findings'] if f['severity']=='BLOCK' and f['code'] not in {'IDENTITY_PENDING','LICENSE_PENDING'}]
        if unsafe:raise ValueError('public tree contains blocked sensitive content: '+str([(x['code'],x['path']) for x in unsafe[:8]]))
        if audit['status']=='BLOCK' and not preview:raise ValueError('Owner identity/license decisions pending; use preview for a local review artifact, not public release')
        write_json(out/'PUBLIC_EXPORT.json',{'mode':'OWNER_PREVIEW_NOT_PUBLISHABLE' if preview and audit['status']=='BLOCK' else 'REVIEWABLE_SOURCE',
            'excluded_count':len(excluded),'policy':'allowlisted source only; original delivery evidence remains outside public export'})
        write_json(out/'PUBLIC_AUDIT.json',audit)
        write_text(out/'PUBLIC_RELEASE_AUDIT.md','# Public source audit\n\nStatus: **'+audit['status']+'**\n\n'+
            '\n'.join('- '+f['severity']+' '+f['code']+' — `'+f['path']+'`'+(' line '+str(f['line']) if f.get('line') else '') for f in audit['findings'])+'\n')
    return {'status':'PREVIEW' if preview else 'EXPORTED','destination':str(destination),'audit':audit,'excluded_count':len(excluded)}
