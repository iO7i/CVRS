"""Product workflows layered over the existing public CLI.

This dispatches only newly implemented subcommands; historical commands retain
exactly their former parsers. Machine-readable JSON stays the default.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from cvsubstrate.adoption.common import load_config
from cvsubstrate.provenance.io import read_json, write_json

ACTIONS = {
    'env': {'plan','create','apply','repair','upgrade','doctor','diff','managed','activate','observe','freeze'},
    'stack': {'inspect','configure','doctor','execute'},
    'paper': {'prepare','readiness','approve','execute'},
    'recipe': {'search','check','contribute','index'},
    'research': {'lint'},
    'exchange': {'export','import','audit','native','fiftyone-import','decode','tracking'},
    'site': {'build'},
    'docs': {'portal','version-site'},
    'release': {'preflight','workflows','launch-plan','security-plan','security-apply','freeze-api','api-diff','verify-artifacts','contribution-check','citation-pack'},
    'adapter': {'receipt','badge'},
}


def handles(argv):
    return len(argv)>1 and argv[0] in ACTIONS and argv[1] in ACTIONS[argv[0]]


def parser():
    p=argparse.ArgumentParser(prog='cvrs',description='Managed environments, guided adoption and owner-controlled release preparation')
    groups=p.add_subparsers(dest='group',required=True)
    for group,actions in ACTIONS.items():
        g=groups.add_parser(group);sub=g.add_subparsers(dest='action',required=True)
        for action in sorted(actions):
            c=sub.add_parser(action)
            c.add_argument('target',nargs='?')
            c.add_argument('other',nargs='?')
            for flag in ('out','store','spec','plan','python','environment','pack','operation','actor','approval','approve','replacement',
                         'worker-python','format','field','repository','version','previous','status','task','subject','evidence','reason'):
                c.add_argument('--'+flag)
            c.add_argument('--files',nargs='*',default=[])
            c.add_argument('--trust',action='store_true')
            c.add_argument('--verify',action='store_true')
            c.add_argument('--apply',action='store_true')
            c.add_argument('--preview',action='store_true')
            c.add_argument('--force',action='store_true')
    return p


def _need(v,name):
    if not v:raise ValueError(name+' is required')
    return v


def dispatch(a):
    target=Path(a.target) if a.target else None
    destination=Path(a.out) if a.out else None
    if a.group=='env':
        from cvsubstrate.product.environments import EnvironmentManager, probe
        from cvsubstrate.product.contracts import ManagedEnvironmentSpec, EnvironmentPlan
        if a.action=='observe':return probe(_need(a.python,'--python'),a.files)
        manager=EnvironmentManager(_need(a.store,'--store'))
        if a.action=='managed':return manager.list()
        if a.action=='doctor':return manager.doctor(_need(a.target,'NAME'))
        if a.action=='diff':return manager.diff(_need(a.target,'NAME'),_need(a.other,'OTHER_NAME'))
        if a.action=='activate':
            if a.approve != _need(a.other,'REVISION'):raise ValueError('approve the exact revision with --approve REVISION')
            return manager.activate(_need(a.target,'NAME'),a.other,confirm=True)
        if a.action=='freeze':
            report=manager.doctor(_need(a.target,'NAME'))
            return {'schema_version':'1.0','kind':'OBSERVED_PACKAGE_LOCK','name':a.target,
                    'observation':report,'limits':'Package observations do not identify compiled binaries or recreate a CUDA image.'}
        if a.action=='apply':return manager.apply(read_json(_need(target,'PLAN_FILE')),approve_digest=_need(a.approve,'--approve PLAN_DIGEST'))
        if a.action in {'repair','upgrade'}:
            plan=manager.repair_plan(_need(a.target,'NAME'),replacement_spec=load_config(Path(a.spec)) if a.spec else None)
            if a.action=='upgrade' and not a.spec:raise ValueError('upgrade requires --spec with reviewed replacement pins')
        else:plan=manager.plan(load_config(_need(target,'SPEC_FILE')))
        if destination:write_json(destination,plan)
        if a.approve:return manager.apply(plan,approve_digest=a.approve)
        return {'status':'PLAN_ONLY','plan':plan.model_dump(mode='json'),'next':'Apply the exact plan digest using --approve; nothing has been installed.'}
    if a.group=='stack':
        from cvsubstrate.product.stacks import inspect_pack,configure_pack,workspace_doctor,run_workspace
        if a.action=='inspect':return inspect_pack(_need(a.target,'PACK'))
        if a.action=='doctor':return workspace_doctor(_need(target,'WORKSPACE'))
        if a.action=='configure':return configure_pack(_need(a.target,'PACK'),_need(destination,'--out'),python=a.python,
                store=Path(a.store) if a.store else None,environment=a.environment,payload=load_config(Path(a.spec)) if a.spec else None)
        return run_workspace(_need(target,'WORKSPACE'),_need(a.other or a.operation,'OPERATION'),_need(destination,'--out'),trust=a.trust)
    if a.group=='paper':
        from cvsubstrate.product.onboarding import prepare_paper,readiness,approve_paper,execute_approved
        if a.action=='prepare':return prepare_paper(_need(target,'REPO'),_need(destination,'--out'),python=a.python,
            store=Path(a.store) if a.store else None,environment=a.environment,decisions=load_config(Path(a.spec)) if a.spec else None)
        if a.action=='readiness':return readiness(_need(target,'PAPER_SPEC'))
        if a.action=='approve':return approve_paper(_need(target,'PAPER_SPEC'),_need(a.actor,'--actor'),_need(destination,'--out'))
        return execute_approved(_need(target,'PAPER_SPEC'),Path(_need(a.approval,'--approval')),
                                _need(a.operation,'--operation'),_need(destination,'--out'),trust=a.trust)
    if a.group=='research':
        from cvsubstrate.product.methodology import review_methodology,review_report
        value=load_config(_need(target,'METHODOLOGY_FILE'));result=review_methodology(value)
        if destination:
            destination.mkdir(parents=True,exist_ok=False);write_json(destination/'review.json',result)
            (destination/'review.md').write_text(review_report(value),encoding='utf-8')
        return result
    if a.group=='recipe':
        from cvsubstrate.product.recipes import search_recipes,check_recipe,contribute_recipe,recipe_index
        if a.action=='search':return search_recipes(a.target or '',framework=a.pack,task=a.task)
        if a.action=='check':return check_recipe(load_config(_need(target,'RECIPE_FILE')))
        if a.action=='contribute':return contribute_recipe(_need(target,'RECIPE_FILE'),_need(destination,'--out'))
        return recipe_index(_need(destination,'--out'))
    if a.group=='exchange':
        from cvsubstrate.product.interchange import exchange,audit_roundtrip
        from cvsubstrate.product.bridges import native_exchange,import_fiftyone_dataset,decode_arrays,tracking_handoff
        if a.action=='audit':return audit_roundtrip(load_config(_need(target,'ORIGINAL')),load_config(Path(_need(a.other,'RESTORED'))))
        if a.action=='native':return native_exchange(load_config(_need(target,'CANONICAL')), _need(a.format,'--format'),_need(destination,'--out'),worker_python=a.worker_python,trust=a.trust)
        if a.action=='fiftyone-import':return import_fiftyone_dataset(_need(a.target,'DATASET_NAME'),_need(destination,'--out'),worker_python=a.worker_python,trust=a.trust)
        if a.action=='decode':return decode_arrays(_need(target,'NPZ_FILE'),load_config(Path(_need(a.spec,'--spec'))),_need(destination,'--out'))
        if a.action=='tracking':return tracking_handoff(_need(target,'RUN'),_need(destination,'--out'),approved_files=a.files)
        result=exchange(load_config(_need(target,'INPUT')), _need(a.format,'--format'),a.action)
        write_json(_need(destination,'--out'),result);return {'status':'CONVERTED','output':str(destination),'native_sdk_execution':'NOT_INFERRED'}
    if a.group in {'site','docs'}:
        from cvsubstrate.product.browser import build_browser,build_portal,versioned_portal
        if a.group=='docs' and a.action=='version-site':return versioned_portal([Path(x) for x in a.files],_need(destination,'--out'))
        return (build_portal if a.group=='docs' else build_browser)(_need(target,'SOURCE'),_need(destination,'--out'),**({'verify':a.verify} if a.group=='site' else {}))
    if a.group=='adapter':
        from cvsubstrate.product.compatibility import make_receipt,render_badge
        if a.action=='receipt':
            result=make_receipt(load_config(_need(target,'DESCRIPTOR')),Path(a.evidence) if a.evidence else None)
            write_json(_need(destination,'--out'),result);return result
        return render_badge(load_config(_need(target,'RECEIPT')),_need(destination,'--out'))
    if a.group=='release':
        from cvsubstrate.product.launch import preflight,generate_workflows,launch_plan,security_plan,apply_security_plan,verify_artifacts,contribution_check
        from cvsubstrate.product.compatibility import freeze_api,compare_api
        if a.action=='preflight':return preflight(_need(target,'REPO'),require_clean=a.verify)
        if a.action=='workflows':return generate_workflows(_need(target,'REPO'),_need(destination,'--out'))
        if a.action=='launch-plan':
            result=launch_plan(_need(target,'REPO'))
            if destination:write_json(destination,result)
            return result
        if a.action=='security-plan':
            result=security_plan(_need(a.repository or a.target,'owner/repo'),required_checks=a.files)
            if destination:write_json(destination,result)
            return result
        if a.action=='security-apply':return apply_security_plan(load_config(_need(target,'PLAN')),approve_digest=_need(a.approve,'--approve'),allow_network=a.apply,destination=_need(destination,'--out'))
        if a.action=='freeze-api':return freeze_api(_need(target,'REPO'),_need(destination,'--out'))
        if a.action=='api-diff':return compare_api(load_config(_need(target,'PREVIOUS')),load_config(Path(_need(a.other,'CURRENT'))))
        if a.action=='verify-artifacts':return verify_artifacts(_need(target,'RELEASE_MANIFEST'))
        if a.action=='contribution-check':return contribution_check(_need(target,'REPO'))
        if a.action=='citation-pack':
            from cvsubstrate.product.academic import citation_pack
            receipt=load_config(Path(a.spec)) if a.spec else None
            return citation_pack(_need(target,'REPO'),_need(destination,'--out'),doi=receipt.get('doi') if receipt else None,archive_receipt=receipt)
    raise ValueError('unsupported command')


def main(argv=None):
    args=parser().parse_args(argv)
    try:
        result=dispatch(args)
        print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False,default=str))
        if isinstance(result,dict) and a_gate(args,result):return 2
        return 0
    except Exception as exc:
        from cvsubstrate.errors import public_error
        error=public_error(exc)
        print(json.dumps({'status':'FAILED','error':error,'hint':'No implicit installs, model downloads or remote publishing were attempted. Inspect the named operation receipt for partial local work.'},default=str),file=sys.stderr)
        return 2


def a_gate(args, result):
    gated = (args.group == 'release' and args.action in {'preflight','contribution-check','verify-artifacts','api-diff'}) or (args.group=='research' and args.verify)
    return gated and result.get('status') in {'BLOCKED','FAILED','BREAKING'}
