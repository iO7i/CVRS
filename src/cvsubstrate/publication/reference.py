"""Generated CLI/schema/API references; no external model imports."""
from pathlib import Path
import argparse,ast
from cvsubstrate.provenance.io import write_json
from cvsubstrate.adoption.common import write_text


def cli_surface():
    from cvsubstrate import cli,cli_adoption,cli_frontier,cli_groundwork,cli_closure,cli_product
    result={}
    def walk(parser,prefix):
        commands=[a for a in parser._actions if isinstance(a,argparse._SubParsersAction)]
        result[prefix]={'options':sorted({x for a in parser._actions for x in a.option_strings}),
            'positionals':[a.dest for a in parser._actions if not a.option_strings and not isinstance(a,argparse._SubParsersAction)],
            'help':parser.format_help()}
        for action in commands:
            for name,child in action.choices.items():walk(child,prefix+' '+name)
    # Later dispatch layers own their shared command prefixes. Retain subcommands.
    for module,prefix in [(cli,'cvrs'),(cli_groundwork,'cvrs'),(cli_frontier,'cvrs'),(cli_closure,'cvrs closure'),(cli_adoption,'cvrs'),(cli_product,'cvrs')]:
        walk(module.parser(),prefix)
    return result


def generate_public_reference(root):
    from cvsubstrate.schemas.registry import schema_registry
    root=Path(root);dest=root/'docs/public/reference';dest.mkdir(parents=True,exist_ok=True)
    surfaces=cli_surface()
    lines=['# Command reference','','Generated from parser declarations. Commands never execute during documentation generation.','']
    for name,value in sorted(surfaces.items()):lines+=['## '+name,'','```text',value['help'].rstrip(),'```','']
    write_text(dest/'cli.md','\n'.join(lines))
    classes=schema_registry();lines=['# Contract reference','','Generated JSON Schema definitions. Native SDK availability is not inferred.','']
    for name,cls in sorted(classes.items()):
        s=cls.model_json_schema();lines+=['## '+name,'','| Field | Required | Definition |','|---|---|---|']
        for k,v in s.get('properties',{}).items():
            kind=v.get('type',v.get('$ref','union / see schema'))
            lines.append('| '+k+' | '+str(k in s.get('required',[]))+' | `'+str(kind).replace('|','\\|')+'` |')
        lines+=['']
    write_text(dest/'schemas.md','\n'.join(lines))
    modules=['adoption.api','adoption.inspect','adoption.wrapping','adoption.composition','adoption.recipes','adoption.environments',
             'adoption.assets','adoption.methodology','adoption.gallery','bridges.service','bridges.interchange','bridges.exports','bridges.semantic',
             'publication.audit','publication.build','publication.site','publication.metadata','publication.compatibility',
             'product.environments','product.stacks','product.onboarding','product.methodology','product.interchange','product.bridges',
             'product.recipes','product.browser','product.compatibility','product.launch']
    lines=['# Python adoption API','','These are local alpha adoption APIs. The existing `cvsubstrate.v1` facade retains its separate compatibility promise.','']
    for module in modules:
        p=root/'src/cvsubstrate'/Path(*module.split('.')).with_suffix('.py');tree=ast.parse(p.read_text())
        lines+=['## cvsubstrate.'+module,'']
        for node in tree.body:
            if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and not node.name.startswith('_'):
                signature=node.name+('('+ast.unparse(node.args)+')' if isinstance(node,ast.FunctionDef) else '')
                lines+=['### `'+signature+'`','',ast.get_docstring(node) or 'See the typed implementation and matching command contract.','']
    write_text(dest/'python.md','\n'.join(lines))
    write_text(dest/'index.md','# Generated references\n\n[Commands](cli.md) · [Schemas](schemas.md) · [Python APIs](python.md)\n')
    payload={'schema_version':'1','cli':{k:{q:v for q,v in x.items() if q!='help'} for k,x in surfaces.items()},
             'schemas':{k:c.model_json_schema() for k,c in classes.items()},
             'versions':{'worker_request':'1.0','worker_session':'2','adoption_contract':'1.0'},
             'scope':'Declared surface, not behavioral compatibility or native integration certification'}
    write_json(root/'src/cvsubstrate/resources/public/api-surface.json',payload)
    return {'commands':len(surfaces),'schemas':len(classes),'python_modules':len(modules)}
