"""Source-attributed paper/stack recipes; never claim an unexecuted reproduction."""
from pathlib import Path
import importlib.resources as resources
from cvsubstrate.adoption.contracts import PaperRecipe
from cvsubstrate.adoption.common import output_tree,write_text
from cvsubstrate.provenance.io import read_json,write_json,file_digest,digest

def recipe_list():
    root=resources.files('cvsubstrate').joinpath('resources','papers')
    return [PaperRecipe.model_validate_json(p.read_text('utf-8')).model_dump(mode='json') for p in sorted(root.iterdir(),key=lambda x:x.name) if p.name.endswith('.json')]

def recipe_inspect(name):
    matches=[x for x in recipe_list() if x['id']==name]
    if not matches:raise ValueError('unknown paper recipe')
    return matches[0]

def materialize_recipe(name,destination):
    recipe=recipe_inspect(name)
    with output_tree(destination,seal=False) as out:
        write_json(out/'recipe.json',recipe)
        write_json(out/'required-assets.json',{'assets':recipe['assets'],'state':'EXTERNAL_ASSETS_REQUIRED'})
        write_json(out/'bindings.json',{'repositories':{str(i):None for i,_ in enumerate(recipe['repositories'])},
                                      'assets':{a['id']:None for a in recipe['assets']}})
        write_text(out/'REPRODUCE.md','# '+recipe['title']+'\n\nSource-attributed preparation recipe, not a reproduced paper.\n'
            'Bind local repositories and assets in `bindings.json`, then inspect each actual checkout with `cvrs inspect-repo`.\n'
            'Pin a commit and asset digests. Review native arguments before using `cvrs wrap-repo`.\n\n'
            '**Composition boundary:** '+recipe['integration_boundary']+'\n\n'+
            '\n'.join('- '+x for x in recipe['limitations'])+'\n')
    return {'status':'MATERIALIZED_UNEXECUTED','path':str(destination),'recipe':name}

def asset_status(recipe_path,bindings_path):
    recipe=PaperRecipe.model_validate(read_json(Path(recipe_path)));bindings=read_json(Path(bindings_path));rows=[]
    for a in recipe.assets:
        value=bindings.get('assets',{}).get(a['id']);p=Path(value) if value else None
        row={'id':a['id'],'present':bool(p and p.exists()),'status':'MISSING'}
        if p and p.is_file():
            row.update(sha256=file_digest(p),status='LOCAL_UNVERIFIED' if not a.get('sha256') else 'VERIFIED' if file_digest(p)==a['sha256'] else 'MISMATCH')
        elif p and p.is_dir():row['status']='DIRECTORY_REQUIRES_MANIFEST'
        rows.append(row)
    return {'recipe':recipe.id,'assets':rows,'scientific_execution':'NOT_RUN'}
