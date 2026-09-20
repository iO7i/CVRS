"""Public adoption CLI. Argument lists, explicit trust, no invisible network actions."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from cvsubstrate.adoption.common import load_config
from cvsubstrate.provenance.io import write_json

TOP={'inspect-repo','wrap-repo','wrap-paper','paper','recipe','env','stack','bridge','assets','hf','composition','methodology','review','diff','support','site','source-git','identity','profile','init','new','adapter','demo-all','quickstart','doctor'}
RELEASE={'audit-public','public-tree','publish-bundle','compatibility'}
def handles(argv):
    return bool(argv and (argv[0] in TOP or argv[0]=='release' and len(argv)>1 and argv[1] in RELEASE or argv[0]=='docs' and len(argv)>1 and argv[1] in {'build','serve','link-check'} or argv[0]=='research' and len(argv)>1 and argv[1]=='lint' or argv[0]=='licenses' and len(argv)>1 and argv[1]=='audit'))

def parser():
    p=argparse.ArgumentParser(prog='cvrs',description='Native research repositories, ecosystem bridges and local public-release tooling.')
    sub=p.add_subparsers(dest='command',required=True)
    def cmd(name,help=None):return sub.add_parser(name,help=help)
    def out(c):c.add_argument('--out',required=True)
    def native(c):c.add_argument('--python',dest='worker_python');c.add_argument('--trust',action='store_true');c.add_argument('--timeout',type=float,default=600)
    c=cmd('inspect-repo');c.add_argument('repo');c.add_argument('--out')
    for name in ('wrap-repo','wrap-paper'):
        c=cmd(name);c.add_argument('repo');out(c);c.add_argument('--python');c.add_argument('--commands',help='reviewed operation→argv/output mapping JSON');c.add_argument('--purpose',choices=['research','software_fixture'],default='research')
    c=cmd('paper');ss=c.add_subparsers(dest='action',required=True)
    a=ss.add_parser('validate');a.add_argument('spec')
    a=ss.add_parser('run');a.add_argument('spec');a.add_argument('--operation',default='predict');out(a);a.add_argument('--trust',action='store_true')
    a=ss.add_parser('import');a.add_argument('repo');out(a);a.add_argument('--python')
    c=cmd('recipe');ss=c.add_subparsers(dest='action',required=True)
    ss.add_parser('list')
    for action in ('inspect','materialize'):
        a=ss.add_parser(action);a.add_argument('name')
        if action=='materialize':out(a)
    a=ss.add_parser('assets');a.add_argument('recipe');a.add_argument('bindings')
    c=cmd('env');ss=c.add_subparsers(dest='action',required=True);ss.add_parser('list')
    a=ss.add_parser('scaffold');a.add_argument('pack');a.add_argument('destination');a.add_argument('--pins');a.add_argument('--python-version');a.add_argument('--base-image')
    a=ss.add_parser('explain');a.add_argument('repos',nargs='+');a.add_argument('--marker-environment')
    a=ss.add_parser('hpc');a.add_argument('spec');out(a);a.add_argument('--scheduler',choices=['slurm','pbs','lsf'],default='slurm');a.add_argument('--cpus',type=int,default=4);a.add_argument('--memory-gb',type=int,default=16);a.add_argument('--gpus',type=int,default=0);a.add_argument('--walltime',default='01:00:00');a.add_argument('--container');a.add_argument('--python',default='python')
    c=cmd('stack');ss=c.add_subparsers(dest='action',required=True);ss.add_parser('list')
    a=ss.add_parser('run');a.add_argument('family');a.add_argument('operation');a.add_argument('payload');out(a);native(a)
    c=cmd('bridge');ss=c.add_subparsers(dest='action',required=True);ss.add_parser('list')
    a=ss.add_parser('run');a.add_argument('job');a.add_argument('--trust',action='store_true');a.add_argument('--allow-network',action='store_true')
    a=ss.add_parser('bundle-detections');a.add_argument('dataset');a.add_argument('predictions');a.add_argument('--image-root',required=True);out(a)
    a=ss.add_parser('codeocean');a.add_argument('capsule');a.add_argument('--argv',required=True,help='JSON list, not a shell command');a.add_argument('--environment');out(a)
    a=ss.add_parser('benchmark');a.add_argument('spec');out(a)
    a=ss.add_parser('reproduce');a.add_argument('run');out(a)
    a=ss.add_parser('simulator');a.add_argument('kind');a.add_argument('source');a.add_argument('--mapping');out(a)
    a=ss.add_parser('semantic-evaluate');a.add_argument('pairs');a.add_argument('--classes',required=True,type=int);a.add_argument('--ignore-index',type=int,default=255);a.add_argument('--reduce-zero-label',action='store_true');out(a)
    a=ss.add_parser('tracking');a.add_argument('run');a.add_argument('--target',choices=['wandb','mlflow'],default='wandb');a.add_argument('--project',default='cvrs');out(a)
    c=cmd('assets');ss=c.add_subparsers(dest='action',required=True)
    for action in ('status','acknowledge','fetch','prune'):
        a=ss.add_parser(action);a.add_argument('--cache',required=True)
        if action!='prune':a.add_argument('descriptor')
        if action=='acknowledge':a.add_argument('--actor',required=True);a.add_argument('--purpose',required=True)
        if action=='fetch':a.add_argument('--allow-network',action='store_true');a.add_argument('--max-bytes',type=int,default=1024**3)
        if action=='prune':a.add_argument('--keep',nargs='*',default=[]);a.add_argument('--apply',action='store_true')
    c=cmd('hf');ss=c.add_subparsers(dest='action',required=True)
    a=ss.add_parser('inspect');a.add_argument('repo');a.add_argument('--revision',default='main');a.add_argument('--repo-type',default='model');a.add_argument('--allow-network',action='store_true');a.add_argument('--out')
    a=ss.add_parser('local-lock');a.add_argument('directory');a.add_argument('--repo-id');a.add_argument('--revision');out(a)
    c=cmd('composition');ss=c.add_subparsers(dest='action',required=True)
    for act in ('plan','run'):
        a=ss.add_parser(act);a.add_argument('spec')
        if act=='run':out(a);a.add_argument('--trust',action='store_true')
    for name in ('methodology','research'):
        c=cmd(name);ss=c.add_subparsers(dest='action',required=True);a=ss.add_parser('lint');a.add_argument('spec');a.add_argument('--out')
    c=cmd('review');c.add_argument('capsule');c.add_argument('--out')
    c=cmd('diff');c.add_argument('left');c.add_argument('right');c.add_argument('--out')
    c=cmd('licenses');ss=c.add_subparsers(dest='action',required=True);a=ss.add_parser('audit');a.add_argument('spec');a.add_argument('--out')
    c=cmd('support');ss=c.add_subparsers(dest='action',required=True);a=ss.add_parser('bundle');a.add_argument('run');out(a)
    c=cmd('site');ss=c.add_subparsers(dest='action',required=True)
    a=ss.add_parser('results');a.add_argument('runs',nargs='+');out(a)
    a=ss.add_parser('graph');a.add_argument('spec');out(a)
    a=ss.add_parser('visual-diff');a.add_argument('image');a.add_argument('left');a.add_argument('right');out(a);a.add_argument('--allow-image-copy',action='store_true')
    c=cmd('source-git');ss=c.add_subparsers(dest='action',required=True)
    a=ss.add_parser('capture');a.add_argument('repo');out(a);a.add_argument('--include-untracked',action='store_true')
    a=ss.add_parser('materialize');a.add_argument('capsule');out(a);a.add_argument('--trust',action='store_true')
    c=cmd('identity');ss=c.add_subparsers(dest='action',required=True)
    for act in ('configure','derive'):
        a=ss.add_parser(act);a.add_argument('root');a.add_argument('settings');a.add_argument('--license-text')
        if act=='derive':out(a)
    c=cmd('profile');c.add_argument('--argv',required=True);out(c);c.add_argument('--trust',action='store_true');c.add_argument('--timeout',type=float,default=600);c.add_argument('--gpu-metrics',action='store_true');c.add_argument('--phase-events')
    c=cmd('init');c.add_argument('destination');c.add_argument('--profile',default='detection');c.add_argument('--name')
    c=cmd('new');ss=c.add_subparsers(dest='action',required=True);a=ss.add_parser('project');a.add_argument('destination');a.add_argument('--profile',default='detection');a.add_argument('--name')
    c=cmd('adapter');ss=c.add_subparsers(dest='action',required=True)
    a=ss.add_parser('new');a.add_argument('name');out(a);a.add_argument('--native-vision',action='store_true')
    a=ss.add_parser('check');a.add_argument('descriptor')
    for name in ('demo-all','quickstart'):
        c=cmd(name);c.add_argument('destination');c.add_argument('--python');c.add_argument('--timeout',type=float,default=240)
    c=cmd('doctor');c.add_argument('--python')
    c=cmd('release');ss=c.add_subparsers(dest='action',required=True)
    a=ss.add_parser('audit-public');a.add_argument('root');a.add_argument('--out')
    for act in ('public-tree','publish-bundle'):
        a=ss.add_parser(act);a.add_argument('root');out(a);a.add_argument('--preview',action='store_true')
        if act=='publish-bundle':a.add_argument('--no-packages',action='store_true')
    a=ss.add_parser('compatibility');a.add_argument('old');a.add_argument('new');a.add_argument('--out')
    c=cmd('docs');ss=c.add_subparsers(dest='action',required=True)
    a=ss.add_parser('build');a.add_argument('root');out(a)
    a=ss.add_parser('link-check');a.add_argument('site')
    a=ss.add_parser('serve');a.add_argument('site');a.add_argument('--port',default=8000,type=int)
    return p

def execute(a):
    C=a.command;A=getattr(a,'action',None)
    if C=='inspect-repo':
        from cvsubstrate.adoption.inspect import inspect_repository
        return inspect_repository(a.repo).model_dump(mode='json')
    if C in {'wrap-repo','wrap-paper'} or C=='paper' and A=='import':
        from cvsubstrate.adoption.wrapping import wrap_repository
        return wrap_repository(a.repo,a.out,python=a.python,commands=load_config(a.commands) if getattr(a,'commands',None) else None,purpose=getattr(a,'purpose','research'))
    if C=='paper':
        from cvsubstrate.adoption.wrapping import validate_paper,run_paper
        return validate_paper(a.spec) if A=='validate' else run_paper(a.spec,a.operation,a.out,trust=a.trust)
    if C=='recipe':
        from cvsubstrate.adoption.recipes import recipe_list,recipe_inspect,materialize_recipe,asset_status
        if A=='list':return recipe_list()
        if A=='inspect':return recipe_inspect(a.name)
        if A=='materialize':return materialize_recipe(a.name,a.out)
        return asset_status(a.recipe,a.bindings)
    if C=='env':
        from cvsubstrate.adoption.environments import list_packs,scaffold_environment,hpc_script
        if A=='list':return list_packs()
        if A=='scaffold':return scaffold_environment(a.pack,a.destination,pins=load_config(a.pins) if a.pins else None,python_version=a.python_version,base_image=a.base_image)
        if A=='explain':
            from cvsubstrate.adoption.conflicts import explain_repositories
            return explain_repositories(a.repos,load_config(a.marker_environment) if a.marker_environment else None)
        return hpc_script(a.spec,a.out,scheduler=a.scheduler,cpus=a.cpus,memory_gb=a.memory_gb,gpus=a.gpus,walltime=a.walltime,python=a.python,container=a.container)
    if C=='stack':
        from cvsubstrate.adoption.environments import list_packs
        from cvsubstrate.adoption.stacks import execute_stack
        return list_packs() if A=='list' else execute_stack(a.family,a.operation,load_config(a.payload),a.out,worker_python=a.worker_python,trust=a.trust,timeout=a.timeout)
    if C=='bridge':
        from cvsubstrate.bridges.service import bridge_catalogue,run_bridge
        if A=='list':return bridge_catalogue()
        if A=='run':
            v=load_config(a.job);v['trust_code']=a.trust;v['allow_network']=a.allow_network
            return run_bridge(v)
        if A=='bundle-detections':
            from cvsubstrate.bridges.interchange import detection_bundle
            from cvsubstrate.provenance.io import read_jsonl
            return detection_bundle(load_config(a.dataset),read_jsonl(Path(a.predictions)),a.image_root)
        if A=='codeocean':
            from cvsubstrate.bridges.exports import export_codeocean
            return export_codeocean(a.capsule,a.out,argv=json.loads(a.argv),environment=load_config(a.environment) if a.environment else None)
        if A=='benchmark':
            from cvsubstrate.bridges.exports import export_benchmark
            return export_benchmark(load_config(a.spec),a.out)
        if A=='reproduce':
            from cvsubstrate.bridges.exports import export_reproduction
            return export_reproduction(a.run,a.out)
        if A=='simulator':
            from cvsubstrate.bridges.simulators import import_simulator
            return import_simulator(a.kind,a.source,a.out,mapping=load_config(a.mapping) if a.mapping else None)
        if A=='tracking':
            from cvsubstrate.bridges.tracking import prepare_tracking
            return prepare_tracking(a.run,a.out,bridge=a.target,project=a.project)
        if A=='semantic-evaluate':
            from cvsubstrate.bridges.semantic import semantic_metrics
            import numpy as np
            pairs=[(np.load(x['truth'],allow_pickle=False),np.load(x['prediction'],allow_pickle=False)) for x in load_config(a.pairs)]
            return semantic_metrics(pairs,num_classes=a.classes,ignore_index=a.ignore_index,reduce_zero_label=a.reduce_zero_label)
    if C=='assets':
        from cvsubstrate.adoption.assets import AssetManager
        manager=AssetManager(a.cache)
        if A=='prune':return manager.prune(a.keep,apply=a.apply)
        value=load_config(a.descriptor)
        if A=='status':return manager.status(value if isinstance(value,list) else [value])
        if A=='acknowledge':return manager.acknowledge(value,a.actor,a.purpose)
        return manager.fetch(value,allow_network=a.allow_network,max_bytes=a.max_bytes)
    if C=='hf':
        from cvsubstrate.adoption.assets import hf_inspect,lock_local_assets
        return hf_inspect(a.repo,a.revision,allow_network=a.allow_network,repo_type=a.repo_type) if A=='inspect' else lock_local_assets(a.directory,provider='huggingface_local',repo_id=a.repo_id,revision=a.revision)
    if C=='composition':
        from cvsubstrate.adoption.composition import compile_composition,run_composition
        spec=load_config(a.spec)
        for n in spec.get('nodes',[]):
            if not Path(n['paper_spec']).is_absolute():n['paper_spec']=str((Path(a.spec).resolve().parent/n['paper_spec']).resolve())
        return compile_composition(spec) if A=='plan' else run_composition(spec,a.out,trust=a.trust)
    if C in {'methodology','research'}:
        from cvsubstrate.adoption.methodology import lint_methodology
        return lint_methodology(load_config(a.spec))
    if C=='review':
        from cvsubstrate.adoption.methodology import reviewer_report
        return reviewer_report(a.capsule)
    if C=='diff':
        from cvsubstrate.adoption.methodology import experiment_diff
        return experiment_diff(load_config(a.left),load_config(a.right))
    if C=='licenses':
        from cvsubstrate.publication.licenses import audit_licenses
        return audit_licenses(load_config(a.spec))
    if C=='support':
        from cvsubstrate.publication.support import support_bundle
        return support_bundle(a.run,a.out)
    if C=='site':
        from cvsubstrate.publication.site import results_site,graph_site,visual_diff
        if A=='results':return results_site(a.runs,a.out)
        if A=='graph':return graph_site(load_config(a.spec),a.out)
        return visual_diff(a.image,load_config(a.left),load_config(a.right),a.out,allow_image_copy=a.allow_image_copy)
    if C=='source-git':
        from cvsubstrate.adoption.git import capture_source,materialize_source
        return capture_source(a.repo,a.out,include_untracked=a.include_untracked) if A=='capture' else materialize_source(a.capsule,a.out,trust=a.trust)
    if C=='identity':
        from cvsubstrate.publication.metadata import configure,derive_identity
        v=load_config(a.settings);text=Path(a.license_text).read_text() if a.license_text else None
        return configure(a.root,v,license_text=text) if A=='configure' else derive_identity(a.root,a.out,v,license_text=text)
    if C=='profile':
        from cvsubstrate.publication.profiling import profile_command
        return profile_command(json.loads(a.argv),a.out,trust=a.trust,timeout=a.timeout,gpu_metrics=a.gpu_metrics,phase_events=a.phase_events)
    if C in {'init','new'}:
        from cvsubstrate.adoption.projects import init_project
        return init_project(a.destination,profile=a.profile,name=a.name)
    if C=='adapter':
        if A=='new':
            if a.native_vision:
                from cvsubstrate.adapters.recipes import scaffold_vision_adapter
                return scaffold_vision_adapter(Path(a.out))
            from cvsubstrate.adoption.projects import adapter_project
            return adapter_project(a.name,a.out)
        from cvsubstrate.contracts.groundwork import PluginDescriptor
        d=PluginDescriptor.model_validate(load_config(a.descriptor))
        return {'status':'MANIFEST_VALID','id':d.id,'operations':d.operations,'native_execution':'NOT_RUN','next':'Use plugin conformance with the explicitly trusted adapter interpreter.'}
    if C in {'demo-all','quickstart'}:
        from cvsubstrate.adoption.demo import demo
        return demo(a.destination,worker_python=a.python,timeout=a.timeout)
    if C=='doctor':
        from cvsubstrate.adoption.environments import doctor
        return doctor(a.python)
    if C=='release':
        from cvsubstrate.publication.audit import audit_public,public_tree
        if A=='audit-public':return audit_public(a.root)
        if A=='public-tree':return public_tree(a.root,a.out,preview=a.preview)
        if A=='publish-bundle':
            from cvsubstrate.publication.build import publish_bundle
            return publish_bundle(a.root,a.out,preview=a.preview,build_packages=not a.no_packages)
        from cvsubstrate.publication.compatibility import compare_compatibility
        return compare_compatibility(a.old,a.new)
    if C=='docs':
        from cvsubstrate.publication.site import build_docs,link_check
        if A=='build':return build_docs(a.root,a.out)
        if A=='link-check':return link_check(a.site)
        import http.server,functools
        handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(Path(a.site).resolve()))
        server=http.server.ThreadingHTTPServer(('127.0.0.1',a.port),handler)
        print('Serving locally on 127.0.0.1:'+str(a.port),file=sys.stderr)
        try:server.serve_forever()
        finally:server.server_close()
        return {'status':'STOPPED'}
    raise ValueError('unsupported command')

def main(argv=None):
    p=parser();a=p.parse_args(argv)
    try:
        result=execute(a)
        # Single-file output commands write data; directory-producing commands already wrote their tree.
        single=(a.command in {'inspect-repo','methodology','research','review','diff','hf','licenses'} or a.command=='release' and a.action in {'audit-public','compatibility'} or a.command=='bridge' and a.action in {'bundle-detections','semantic-evaluate'})
        if single and getattr(a,'out',None):
            target=Path(a.out)
            if target.exists():raise ValueError('refusing to overwrite an existing report')
            write_json(target,result)
        print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False,default=str))
        status=result.get('status') if isinstance(result,dict) else None
        return 2 if status in {'FAILED','FAIL','BLOCK','NOT_READY'} else 0
    except Exception as exc:
        from cvsubstrate.errors import public_error
        from cvsubstrate.security import sanitize
        error=sanitize(public_error(exc))
        hints={'DEPENDENCY_UNAVAILABLE':'Install the matching optional dependency in its dedicated worker environment, or configure --python. Core installation does not require every framework.',
               'TRUST_REQUIRED':'Review native code/configs and explicitly opt in. An isolated interpreter is not a security sandbox.',
               'LICENSE_ACK_REQUIRED':'Inspect license metadata and record acknowledgement for this exact asset with assets acknowledge.',
               'NETWORK_OPT_IN':'This operation requires network permission; it is disabled by default.',
               'TRANSFER_ACK_REQUIRED':'Set payload.acknowledge_external_transfer and opt into network access only after reviewing what will leave this machine.',
               'OUTPUT_EXISTS':'Choose a new output directory. Existing sealed evidence is never overwritten.',
               'PAPER_NOT_READY':'Resolve the reported paths/commands and review the native output contract, then run paper validate again.',
               'WORKER_EXIT':'Inspect the bounded worker log and configured environment. Failed output is not reported as successful.'}
        print(json.dumps({'status':'FAILED','error':error,'hint':hints.get(error.get('code'),'Inspect the documented command and its explicit requirements; no automatic installation or publication occurred.')},ensure_ascii=False),file=sys.stderr)
        return 2
