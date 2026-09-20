"""Curated preparation recipes and a review-first contribution workflow."""
from __future__ import annotations
from pathlib import Path
from urllib.parse import urlsplit
import datetime
import re
from cvsubstrate.adoption.recipes import recipe_list
from cvsubstrate.adoption.contracts import PaperRecipe
from cvsubstrate.adoption.common import output_tree,write_text
from cvsubstrate.provenance.io import write_json,read_json,digest


def _source_url(value):
    u=urlsplit(value)
    if u.scheme!='https' or not u.hostname or u.username or u.password or u.query:
        raise ValueError('recipe sources must use HTTPS without credentials or query secrets')
    return value


def check_recipe(value: dict, *, contributor: bool = False) -> dict:
    recipe=PaperRecipe.model_validate(value)
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,99}',recipe.id):raise ValueError('recipe ID must be a portable lowercase slug')
    datetime.date.fromisoformat(recipe.inspected_date)
    if not recipe.source_urls:raise ValueError('source attribution is required')
    for u in recipe.source_urls:_source_url(u)
    missing=[]
    if not recipe.repositories:missing.append('implementation repository not identified by source')
    for r in recipe.repositories:
        _source_url(r['url'])
        revision=r.get('revision')
        if not revision:missing.append('repository revision: '+r['url'])
        elif not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}',revision):raise ValueError('resolved recipe revisions must be immutable commit digests')
    if recipe.status=='EXECUTED' and contributor:
        raise ValueError('a contributed recipe cannot self-certify execution; submit separate evidence for maintainer review')
    for key,argv in recipe.commands.items():
        if not isinstance(argv,list) or not argv or any(not isinstance(a,str) or '\x00' in a or '\n' in a for a in argv):
            raise ValueError('candidate commands are argv lists, not shell strings')
        if argv[0] in {'curl','wget'}:raise ValueError('downloads belong in declared assets, not an implicit execution command')
    ids=[a.get('id') for a in recipe.assets]
    if any(not i for i in ids) or len(ids)!=len(set(ids)):raise ValueError('asset IDs must be unique')
    for a in recipe.assets:
        if not a.get('license_status'):raise ValueError('each asset requires separate explicit license status')
        if a.get('sha256') and not re.fullmatch(r'[0-9a-f]{64}',a['sha256']):raise ValueError('invalid asset digest')
        if not a.get('sha256'):missing.append('asset content identity: '+a['id'])
    if not recipe.limitations:raise ValueError('state unresolved integration boundaries explicitly')
    return {'status':'VALID_PREPARATION_RECIPE','id':recipe.id,'recipe_digest':digest(recipe),
            'readiness':'UNRESOLVED_INPUTS' if missing else 'PINNED_INPUT_DECLARATIONS',
            'missing':missing,'native_execution':'NOT_INFERRED','source_urls_contacted':False}


def search_recipes(query='',*,framework=None,task=None):
    query=query.casefold()
    result=[]
    for r in recipe_list():
        if query and query not in (' '.join([r['id'],r['title'],*r['frameworks'],*r['tasks']])).casefold():continue
        if framework and framework not in r['frameworks']:continue
        if task and task not in r['tasks']:continue
        result.append({**r,'readiness':check_recipe(r)})
    return {'matches':result,'count':len(result),'scope':'Attributed preparation recipes; not remotely executed paper reproductions.'}


def contribute_recipe(path: Path,destination: Path):
    r=read_json(path);report=check_recipe(r,contributor=True)
    with output_tree(destination,seal=False) as out:
        write_json(out/(r['id']+'.json'),r)
        write_json(out/'review.json',report)
        write_text(out/'PULL_REQUEST.md',f"# Recipe contribution: {r['id']}\n\n"
            "This is source-attributed preparation, not a compatibility certificate.\n\n"
            "Maintainer review: confirm attribution; resolve exact source commits; inspect native commands; check model/data licenses; bind required outputs; attach any real execution evidence separately.\n\n"
            "No model/data bytes or executable helper scripts are bundled automatically.\n")
    return {'status':'PREPARED_FOR_REVIEW','output':str(destination),'report':report}


def recipe_index(destination: Path):
    values=recipe_list();checks=[check_recipe(r) for r in values]
    with output_tree(destination,seal=False) as out:
        write_json(out/'recipes.json',values);write_json(out/'checks.json',checks)
        lines=['# Paper preparation recipe index','',
               'These entries identify public sources and required native assets. They are not claims of reproduced paper results.','',
               '| Recipe | Frameworks | Tasks | Readiness |','|---|---|---|---|']
        for r,c in zip(values,checks):
            lines.append(f"| {r['id']} | {', '.join(r['frameworks'])} | {', '.join(r['tasks'])} | {c['readiness']} |")
            write_json(out/'recipes'/(r['id']+'.json'),r)
        write_text(out/'README.md','\n'.join(lines)+'\n')
    return {'status':'BUILT','recipes':len(values),'output':str(destination)}
