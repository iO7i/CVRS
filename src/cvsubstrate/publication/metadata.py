"""Owner-supplied project identity. No fabricated attribution or automatic license grant."""
from pathlib import Path
import re,json,shutil
from cvsubstrate.adoption.contracts import PublicationSettings
from cvsubstrate.adoption.common import write_text,output_tree
from cvsubstrate.provenance.io import read_json,write_json,digest

def validate_settings(settings):
    s=PublicationSettings.model_validate(settings)
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]*',s.distribution_name):raise ValueError('invalid distribution name')
    if not s.import_name.isidentifier() or not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_-]*',s.cli_name):raise ValueError('invalid import/CLI identifier')
    if s.identity_approved and (not s.authors or not s.repository_url or not s.copyright_holder):raise ValueError('approved identity requires actual authors, repository URL and copyright holder')
    if s.license_approved and s.license_id=='LicenseRef-Owner-Decision-Pending':raise ValueError('approved license cannot remain pending')
    return s

def configure(root,settings,*,license_text=None):
    root=Path(root);s=validate_settings(settings)
    from cvsubstrate.provenance.artifact_set import assert_not_inside_sealed
    assert_not_inside_sealed(root/'PUBLICATION.json')
    if s.license_approved and not license_text:raise ValueError('supply the exact approved license grant text')
    old=PublicationSettings.model_validate(read_json(root/'PUBLICATION.json')) if (root/'PUBLICATION.json').exists() else PublicationSettings()
    # Renaming a package is a source migration, not a blind replacement in historical data.
    if s.import_name!=old.import_name:raise ValueError('import namespace is an API contract; use identity derive for an explicit reviewed source migration')
    write_json(root/'PUBLICATION.json',s)
    text=(root/'pyproject.toml').read_text()
    text=re.sub(r'(?m)^name = "[^"]+"', 'name = '+json.dumps(s.distribution_name),text,count=1)
    text=re.sub(r'(?m)^license = "[^"]+"','license = '+json.dumps(s.license_id),text,count=1)
    text=re.sub(r'(?m)^'+re.escape(old.cli_name)+r' = "'+re.escape(old.import_name)+r'\.cli:main"',s.cli_name+' = "'+s.import_name+'.cli:main"',text)
    if s.repository_url:
        section='\n[project.urls]\nRepository = '+json.dumps(s.repository_url)+'\n'
        if '[project.urls]' not in text:text+=section
        else:text=re.sub(r'(?m)^Repository = "[^"]*"', 'Repository = '+json.dumps(s.repository_url),text)
    author_entries=[]
    for a in s.authors:
        if a.get('name'):author_entries.append('{name = '+json.dumps(a['name'])+(', email = '+json.dumps(a['email']) if a.get('email') else '')+'}')
    if author_entries:
        authors='authors = ['+', '.join(author_entries)+']'
        if re.search(r'(?m)^authors = ',text):text=re.sub(r'(?m)^authors = .*$',authors,text)
        else:text=text.replace('[project]','[project]\n'+authors,1)
    write_text(root/'pyproject.toml',text)
    if license_text:write_text(root/'LICENSE',license_text)
    citation={'cff-version':'1.2.0','message':'Cite this software using its release identity and archived source when available.',
              'title':s.display_name,'type':'software','authors':[{'name':a['name']} for a in s.authors if a.get('name')]}
    if s.repository_url:citation['repository-code']=s.repository_url
    if s.license_approved:citation['license']=s.license_id
    # JSON is valid YAML, including for CFF; pending author metadata is labeled in the status record.
    write_json(root/'CITATION.cff',citation)
    write_json(root/'.codemeta.json',{'@context':'https://doi.org/10.5063/schema/codemeta-2.0','@type':'SoftwareSourceCode',
        'name':s.display_name,'codeRepository':s.repository_url,'author':s.authors,'license':s.license_id,
        'description':'Computer-vision experiment interoperability and reproducible evidence'})
    return {'status':'OWNER_CONFIGURED' if s.identity_approved and s.license_approved else 'PENDING_OWNER_APPROVAL','identity_digest':digest(s)}

def derive_identity(source,destination,settings,*,license_text=None):
    from cvsubstrate.publication.audit import public_tree
    source=Path(source);s=validate_settings(settings);old=PublicationSettings.model_validate(read_json(source/'PUBLICATION.json'))
    public_tree(source,destination,preview=True);root=Path(destination)
    old_import=old.import_name
    if s.import_name!=old_import:
        import tokenize,io
        # Limited source rewrite; never rewrites evidence/checkpoint bytes or registry IDs.
        for p in (root/'src').rglob('*.py'):
            text=p.read_text();tokens=[]
            for t in tokenize.generate_tokens(io.StringIO(text).readline):
                if t.type==tokenize.NAME and t.string==old_import:t=t._replace(string=s.import_name)
                elif t.type==tokenize.STRING:
                    import ast
                    try:value=ast.literal_eval(t.string)
                    except (ValueError,SyntaxError):value=None
                    if value==old_import:t=t._replace(string=repr(s.import_name))
                    else:t=t._replace(string=t.string.replace(old_import+'.',s.import_name+'.').replace('/'+old_import+'/', '/'+s.import_name+'/'))
                tokens.append(t)
            p.write_text(tokenize.untokenize(tokens))
        (root/'src'/old_import).rename(root/'src'/s.import_name)
        for folder in ('tests','tools','examples','docs'):
            for p in (root/folder).rglob('*') if (root/folder).exists() else []:
                if p.is_file() and p.suffix in {'.py','.md','.json','.toml','.yml','.yaml'}:
                    p.write_text(p.read_text().replace(old_import,s.import_name).replace(old.cli_name+' ',s.cli_name+' '))
        p=root/'pyproject.toml';p.write_text(p.read_text().replace(old_import,s.import_name))
        value=old.model_dump(mode='json');value['import_name']=s.import_name;write_json(root/'PUBLICATION.json',value)
    result=configure(root,s.model_dump(mode='json'),license_text=license_text)
    write_json(root/'IDENTITY_MIGRATION.json',{'from':old.model_dump(mode='json'),'to':s.model_dump(mode='json'),
        'status':'SOURCE_REWRITE_REQUIRES_OWNER_REVIEW','compatibility':'An import/CLI rename is a breaking surface change, not a schema rewrite'})
    return result
