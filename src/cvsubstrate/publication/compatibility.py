"""Read-only API/schema compatibility inventory; never imports an old wheel."""
from pathlib import Path
from typing import Any
import ast,zipfile,json
from cvsubstrate.provenance.io import digest

def _surface(files):
    api: dict[str, dict[str, Any]] = {}; schemas: dict[str, Any] = {}; cli: dict[str, Any] = {}; versions: dict[str, Any] = {}
    for name,text in files:
        if name.endswith('.py'):
            try:tree=ast.parse(text)
            except SyntaxError:continue
            for node in tree.body:
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and not node.name.startswith('_'):
                    key=name+':'+node.name
                    if isinstance(node,ast.ClassDef):api[key]={'kind':'class'}
                    else:api[key]={'kind':'function','args':[x.arg for x in node.args.posonlyargs+node.args.args],
                         'kwonly':[x.arg for x in node.args.kwonlyargs],'defaults':len(node.args.defaults)}
        elif name.endswith('api-surface.json'):
            try:
                surface=json.loads(text);cli.update(surface.get('cli',{}));versions.update(surface.get('versions',{}))
                schemas.update({'schemas/'+k+'.schema.json':v for k,v in surface.get('schemas',{}).items()})
            except ValueError:pass
        elif name.endswith('.schema.json'):
            try:schemas[name]=json.loads(text)
            except ValueError:pass
    return {'api':api,'schemas':schemas,'cli':cli,'versions':versions}

def inventory(path):
    p=Path(path)
    if p.suffix=='.whl':
        with zipfile.ZipFile(p) as z:
            if len(z.infolist())>20000 or sum(i.file_size for i in z.infolist())>64*1024**2:raise ValueError('wheel inspection exceeds limits')
            files=[(n,z.read(n).decode('utf-8')) for n in z.namelist() if n.endswith(('.py','.schema.json','api-surface.json'))]
    else:
        root=p/'src' if (p/'src').is_dir() else p
        files=[(f.relative_to(root).as_posix(),f.read_text('utf-8')) for f in root.rglob('*') if f.is_file() and not f.is_symlink() and (f.suffix=='.py' or f.name=='api-surface.json')]
        sr=p/'schemas'
        if sr.exists():files += [('schemas/'+f.name,f.read_text()) for f in sr.glob('*.schema.json')]
    return _surface(files)

def compare_compatibility(old,new):
    a=inventory(old);b=inventory(new);removed=sorted(set(a['api'])-set(b['api']))
    changed=[k for k in a['api'].keys()&b['api'].keys() if a['api'][k]!=b['api'][k]]
    schema_changes=[]
    for key,value in a['schemas'].items():
        other=b['schemas'].get(key)
        if other is None:schema_changes.append({'schema':key,'kind':'removed'})
        elif digest(value)!=digest(other):schema_changes.append({'schema':key,'kind':'changed_needs_semantic_review'})
    cli_removed=sorted(set(a['cli'])-set(b['cli']))
    cli_changed=[k for k in a['cli'].keys() & b['cli'].keys() if a['cli'][k]!=b['cli'][k]]
    version_changes={k:{'old':v,'new':b['versions'].get(k)} for k,v in a['versions'].items() if b['versions'].get(k)!=v}
    return {'status':'REVIEW_REQUIRED' if removed or changed or schema_changes or cli_removed or cli_changed or version_changes else 'NO_SURFACE_BREAK_DETECTED',
            'cli_removed':cli_removed,'cli_changed':cli_changed,'protocol_changes':version_changes,
            'old_cli_inventory_available':bool(a['cli']),
            'removed_api':removed,'changed_signatures':changed,'schema_changes':schema_changes,
            'limits':'Static public-looking surface comparison, not a proof of behavioral compatibility or stable-API membership.'}
