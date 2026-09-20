"""Owner-reviewed citation/archive preparation. No archiving API is invoked."""
from __future__ import annotations
import re
from pathlib import Path
from cvsubstrate.publication.metadata import validate_settings
from cvsubstrate.adoption.common import output_tree,write_text
from cvsubstrate.provenance.io import read_json,write_json,file_digest,digest
from cvsubstrate.release import source_version


def citation_pack(root: Path,destination: Path,*,doi: str | None=None,archive_receipt: dict | None=None):
    root=Path(root);s=validate_settings(read_json(root/'PUBLICATION.json'))
    if not s.identity_approved or not s.license_approved:
        raise ValueError('citation/archive metadata requires approved authors, identity and exact source license')
    if doi:
        if not re.fullmatch(r'10\.\d{4,9}/[^\s]+',doi):raise ValueError('invalid DOI syntax')
        if not archive_receipt or archive_receipt.get('doi')!=doi or archive_receipt.get('repository')!=s.repository_url or archive_receipt.get('version')!=source_version(root):
            raise ValueError('bind DOI to a matching owner-supplied archive receipt; never generate placeholder DOIs')
    authors=[]
    for person in s.authors:
        if person.get('family-names'):
            author={k:v for k,v in person.items() if k in {'family-names','given-names','orcid','affiliation','email'}}
        elif person.get('name'):author={k:v for k,v in person.items() if k in {'name','orcid','affiliation','email'}}
        else:raise ValueError('author requires an explicit name or family-names; no name splitting is inferred')
        authors.append(author)
    cff={'cff-version':'1.2.0','message':'Cite the exact version and its archived source when available.','type':'software',
         'title':s.display_name,'version':source_version(root),'repository-code':s.repository_url,'license':s.license_id,'authors':authors}
    if doi:cff['doi']=doi
    with output_tree(destination,seal=False) as out:
        write_json(out/'CITATION.cff',cff)
        write_json(out/'codemeta.json',{'@context':'https://doi.org/10.5063/schema/codemeta-2.0','@type':'SoftwareSourceCode',
            'name':s.display_name,'version':source_version(root),'codeRepository':s.repository_url,'author':s.authors,'license':s.license_id,
            **({'identifier':doi} if doi else {})})
        write_json(out/'archive-preparation.json',{'repository':s.repository_url,'version':source_version(root),
            'citation_sha256':file_digest(out/'CITATION.cff'),'license_sha256':file_digest(root/'LICENSE'),
            'doi':doi,'archive_receipt':archive_receipt,'status':'OWNER_ATTESTED_ARCHIVE' if doi else 'NOT_ARCHIVED',
            'remote_verification':'NOT_PERFORMED','metadata_policy':'CITATION.cff is authoritative; no .zenodo.json override generated'})
        write_text(out/'ARCHIVE.md','# Archive this release\n\nConnect the owner-controlled GitHub repository in Zenodo and enable release archiving.\n'
            'Review the exact tag, source license, authors and CITATION.cff before publishing the release.\n'
            'After the archive exists, preserve its returned DOI, repository and version in an archive receipt.\n'
            'Supplying that receipt records owner testimony; this tool does not assert that it contacted Zenodo.\n')
    return {'status':'PREPARED','output':str(destination),'doi':doi,'remote_operations':0,'citation_digest':digest(cff)}
