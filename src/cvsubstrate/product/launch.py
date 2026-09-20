"""Owner-gated launch plans, pinned workflow generation and release verification.

This module does not publish anything by default. Only security-apply makes a
remote change, after approval of the exact plan, with explicit network consent.
PyPI, Pages and archiving activation remain actions by the actual account owner.
"""
from __future__ import annotations
import email
import importlib.resources as resources
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import tomllib
import zipfile
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit, quote
from cvsubstrate.adoption.common import output_tree, write_text
from cvsubstrate.provenance.io import read_json, write_json, file_digest, digest, safe_join
from cvsubstrate.errors import CVRSError


def _source_version(root):
    from cvsubstrate.release import source_version
    return source_version(Path(root))


def _repository(url):
    p=urlsplit(url or '')
    if p.scheme!='https' or p.netloc!='github.com' or p.query or p.fragment or p.username or p.password:
        raise ValueError('configure an exact HTTPS github.com owner/repository URL')
    value=p.path.strip('/').removesuffix('.git')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',value):raise ValueError('invalid repository identity')
    return value


def preflight(root: Path, *, require_clean=False) -> dict:
    from cvsubstrate.publication.metadata import validate_settings
    from cvsubstrate.publication.audit import public_tree
    root=Path(root).resolve();checks=[]
    def add(name,state,detail):checks.append({'name':name,'status':state,'detail':detail})
    settings=validate_settings(read_json(root/'PUBLICATION.json'))
    for name,value in [('identity approval',settings.identity_approved),('source license approval',settings.license_approved),
                       ('authors',bool(settings.authors)),('copyright holder',bool(settings.copyright_holder)),('security contact',bool(settings.security_contact))]:
        add(name,'PASS' if value else 'BLOCK','Owner configured' if value else 'Requires an explicit owner decision; no value is inferred')
    try:repo=_repository(settings.repository_url);add('repository identity','PASS',repo)
    except ValueError as e:repo=None;add('repository identity','BLOCK',str(e))
    toml=tomllib.loads((root/'pyproject.toml').read_text())['project']
    for key,expected in [('name',settings.distribution_name),('license',settings.license_id)]:
        add('package '+key,'PASS' if toml.get(key)==expected else 'BLOCK','Package metadata must agree with PUBLICATION.json')
    text=(root/'LICENSE').read_text() if (root/'LICENSE').is_file() else ''
    pending=not text.strip() or 'Owner-Decision-Pending' in text or 'license grant has not' in text.lower()
    add('license text','BLOCK' if pending else 'PASS','Exact source grant must be supplied; this check is not a legal opinion')
    try:
        with tempfile.TemporaryDirectory() as td:
            result=public_tree(root,Path(td)/'public',preview=True)
            sensitive=[x for x in result['audit']['findings'] if x['severity']=='BLOCK' and x['code'] not in {'IDENTITY_PENDING','LICENSE_PENDING'}]
            add('public-source scan','BLOCK' if sensitive else 'PASS',{'sensitive_findings':sensitive,'warnings':sum(x['severity']=='WARN' for x in result['audit']['findings'])})
    except Exception as e:add('public-source scan','BLOCK',str(e))
    for path in ('README.md','docs/public/index.md','CONTRIBUTING.md','SECURITY.md','CITATION.cff','src/cvsubstrate/resources/product/action-lock.json'):
        add('required '+path,'PASS' if (root/path).is_file() else 'BLOCK','Required public metadata/source')
    version=_source_version(root)
    ref=os.environ.get('CVRS_RELEASE_TAG')
    add('release tag','PASS' if ref=='v'+version else 'BLOCK' if ref else 'NOT_REQUESTED',{'expected':'v'+version,'observed':ref})
    identity=os.environ.get('CVRS_RELEASE_REPOSITORY')
    if identity:add('release repository','PASS' if identity==repo else 'BLOCK',{'expected':repo,'observed':identity})
    if require_clean:
        r=subprocess.run(['git','status','--porcelain','--untracked-files=normal'],cwd=root,capture_output=True,text=True,timeout=20)
        add('clean source','PASS' if r.returncode==0 and not r.stdout.strip() else 'BLOCK','Git checkout must have no pending changes; this does not approve private history')
    return {'status':'BLOCKED' if any(x['status']=='BLOCK' for x in checks) else 'READY_FOR_OWNER_RELEASE_REVIEW',
            'version':version,'repository':repo,'distribution':settings.distribution_name,'checks':checks,
            'native_model_certification':'NOT_INFERRED','remote_state':'NOT_CONTACTED'}


def action_lock():
    value=json.loads(resources.files('cvsubstrate').joinpath('resources/product/action-lock.json').read_text())
    for name,item in value['actions'].items():
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',name) or not re.fullmatch('[0-9a-f]{40}',item['sha']):
            raise ValueError('action pins must be immutable full commit identities')
    return value


def workflow_documents():
    """Build jobs have no signing/publishing tokens. Privileged jobs consume files."""
    pins=action_lock()['actions']
    def action(name,step=None,**kw):
        v={'uses':name+('/'+step if step else '')+'@'+pins[name]['sha']};v.update(kw);return v
    checkout=action('actions/checkout',**{'with':{'persist-credentials':False}})
    python=action('actions/setup-python',**{'with':{'python-version':'3.13'}})
    base_env={'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    core_steps=[checkout,action('actions/setup-python',**{'with':{'python-version':'${{ matrix.python }}'}}),
        {'run':'python -m pip install -e ".[adoption]" pytest jsonschema'},
        {'run':'python -m pytest -m "not native" --junitxml=core-tests.xml'},
        {'run':'python -m compileall -q src'},
        {'run':'python -m cvsubstrate release contribution-check . --verify'}]
    core={'name':'CVRS core','on':{'pull_request':{},'push':{'branches':['main']},'workflow_dispatch':{}},
        'permissions':{'contents':'read'},'concurrency':{'group':'core-${{ github.ref }}','cancel-in-progress':True},'jobs':{
        'core':{'name':'Core Linux (${{ matrix.python }})','runs-on':'ubuntu-latest','timeout-minutes':20,
        'strategy':{'fail-fast':False,'matrix':{'python':['3.11','3.12','3.13']}},'env':base_env,
        'steps':[ *core_steps,
            action('actions/upload-artifact',**{'if':'always()','with':{'name':'core-linux-${{ matrix.python }}','path':'core-tests.xml','if-no-files-found':'error'}})]},
        'platform':{'name':'Core ${{ matrix.slug }}','runs-on':'${{ matrix.os }}','timeout-minutes':25,
        'strategy':{'fail-fast':False,'matrix':{'include':[
            {'os':'windows-latest','python':'3.12','slug':'windows-3.12'},
            {'os':'macos-latest','python':'3.12','slug':'macos-3.12'}]}},'env':base_env,
        'steps':[ *core_steps,
            action('actions/upload-artifact',**{'if':'always()','with':{'name':'core-${{ matrix.slug }}','path':'core-tests.xml','if-no-files-found':'error'}})]}}}
    quality={'name':'CVRS quality','on':{'pull_request':{},'push':{'branches':['main']},'workflow_dispatch':{}},'permissions':{'contents':'read'},'jobs':{
        'quality':{'runs-on':'ubuntu-latest','timeout-minutes':20,'steps':[checkout,python,
            {'run':'python -m pip install -e ".[adoption,dev,docs]"'},
            {'run':'python tools/dev.py lint'}, {'run':'python tools/dev.py typecheck'},
            {'run':'python -m mkdocs build --strict --site-dir ../mkdocs-check'},
            {'run':'python -m cvsubstrate docs portal . --out ../docs-check'},
            {'run':'python -m cvsubstrate docs link-check ../docs-check'}]},
        'coco':{'name':'Official COCO parity','runs-on':'ubuntu-latest','timeout-minutes':20,'env':base_env,
            'steps':[checkout,action('actions/setup-python',**{'with':{'python-version':'3.12'}}),
                {'run':'python -m pip install -e ".[adoption,coco]" pytest jsonschema'},
                {'run':'python -m pytest -q -m coco tests/test_evaluation.py tests/test_slice02_heritage.py --junitxml=coco-tests.xml'},
                action('actions/upload-artifact',**{'if':'always()','with':{'name':'official-coco-tests','path':'coco-tests.xml','if-no-files-found':'error'}})]}}}
    security={'name':'CVRS code scanning','on':{'push':{'branches':['main']},'schedule':[{'cron':'23 5 * * 1'}],'workflow_dispatch':{}},
        'permissions':{'contents':'read'},'jobs':{'analyze':{'runs-on':'ubuntu-latest','timeout-minutes':30,
        'permissions':{'contents':'read','security-events':'write'},'steps':[checkout,
        action('github/codeql-action','init',**{'with':{'languages':'python, actions','build-mode':'none'}}),
        action('github/codeql-action','analyze')]}}}
    build_steps=[checkout,python,{'run':'python -m pip install -e ".[adoption]" pytest jsonschema setuptools wheel'},
        {'run':'python -m pytest -m "not native"'},
        {'run':'python tools/release_ci.py artifacts release-assets','env':{'CVRS_RELEASE_TAG':'${{ github.ref_name }}','CVRS_RELEASE_REPOSITORY':'${{ github.repository }}'}},
        action('actions/upload-artifact',**{'with':{'name':'release-assets','path':'release-assets/','if-no-files-found':'error','retention-days':30}})]
    download=action('actions/download-artifact',**{'with':{'name':'release-assets','path':'release-assets'}})
    release={'name':'CVRS trusted release','on':{'workflow_dispatch':{'inputs':{'registry':{'type':'choice','options':['testpypi','pypi'],'default':'testpypi','required':True}}}},
        'permissions':{'contents':'read'},'concurrency':{'group':'release-${{ github.ref }}','cancel-in-progress':False},'jobs':{
        'build':{'if':"startsWith(github.ref, 'refs/tags/v') && vars.CVRS_PUBLISH_ENABLED == 'true'",'runs-on':'ubuntu-latest','timeout-minutes':30,'env':base_env,'steps':build_steps},
        'attest':{'needs':'build','runs-on':'ubuntu-latest','permissions':{'contents':'read','id-token':'write','attestations':'write'},'steps':[download,
            action('actions/attest',**{'with':{'subject-path':'release-assets/packages/*'}}),
            action('actions/attest',**{'with':{'subject-path':'release-assets/packages/*','sbom-path':'release-assets/build-environment.cdx.json'}})]},
        'publish':{'needs':['build','attest'],'runs-on':'ubuntu-latest','environment':{'name':'${{ inputs.registry }}'},
            'permissions':{'id-token':'write','contents':'read'},'steps':[download,
            action('pypa/gh-action-pypi-publish',**{'with':{'packages-dir':'release-assets/packages/','repository-url':"${{ inputs.registry == 'testpypi' && 'https://test.pypi.org/legacy/' || 'https://upload.pypi.org/legacy/' }}",'attestations':True,'skip-existing':False}})]},
        'github-draft':{'needs':['build','attest'],'if':"inputs.registry == 'pypi'",'runs-on':'ubuntu-latest',
            'environment':{'name':'github-release'},'permissions':{'contents':'write'},'steps':[download,
            {'name':'Create reviewed draft release','env':{'GH_TOKEN':'${{ github.token }}','GH_REPO':'${{ github.repository }}','RELEASE_TAG':'${{ github.ref_name }}'},
             'run':'gh release create "$RELEASE_TAG" --verify-tag --draft --title "$RELEASE_TAG" --notes-file release-assets/RELEASE_NOTES.md release-assets/packages/* release-assets/release-artifacts.json release-assets/SHA256SUMS release-assets/build-environment.cdx.json'}]}}}
    pages={'name':'CVRS documentation','on':{'push':{'branches':['main']},'workflow_dispatch':{}},'permissions':{'contents':'read'},
        'concurrency':{'group':'pages','cancel-in-progress':False},'jobs':{
        'build':{'if':"vars.CVRS_PAGES_ENABLED == 'true'",'runs-on':'ubuntu-latest','steps':[checkout,python,
            {'run':'python -m pip install -e ".[adoption]"'},
            {'run':'python -m cvsubstrate docs portal . --out ../docs-site'},
            {'run':'python -m cvsubstrate docs link-check ../docs-site'},
            action('actions/configure-pages'),action('actions/upload-pages-artifact',**{'with':{'path':'../docs-site'}})]},
        'deploy':{'needs':'build','runs-on':'ubuntu-latest','permissions':{'pages':'write','id-token':'write'},
            'environment':{'name':'github-pages','url':'${{ steps.deployment.outputs.page_url }}'},
            'steps':[action('actions/deploy-pages',id='deployment')]}}}
    return {'core.yml':core,'quality.yml':quality,'security.yml':security,'release.yml':release,'pages.yml':pages}


def generate_workflows(root: Path, destination: Path) -> dict:
    import yaml
    docs=workflow_documents()
    with output_tree(destination,seal=False) as out:
        for filename,value in docs.items():
            write_text(out/'.github/workflows'/filename,'# Generated from reviewed action-lock.json; owner activation still required.\n'+yaml.safe_dump(json.loads(json.dumps(value)),sort_keys=False,width=110))
        write_json(out/'action-lock.json',action_lock())
        write_text(out/'.github/dependabot.yml',yaml.safe_dump({'version':2,'updates':[
            {'package-ecosystem':'github-actions','directory':'/','schedule':{'interval':'weekly'}},
            {'package-ecosystem':'pip','directory':'/','schedule':{'interval':'weekly'},'groups':{'development':{'dependency-type':'development'}}}]}))
        write_json(out/'launch-plan.json',launch_plan(root))
    return {'status':'GENERATED_NOT_ACTIVATED','files':list(docs),'output':str(destination),
            'remote_operations':0,'permissions':'PR jobs have no publication tokens; OIDC publish consumes only the build artifact.'}


def launch_plan(root: Path) -> dict:
    from cvsubstrate.product.contracts import LaunchPlan
    settings=read_json(Path(root)/'PUBLICATION.json');state=preflight(root)
    actions=[
        'Approve exact name, authors/copyright, source license text and security contact.',
        'Create/select the public repository and review the clean-source audit; configure protected main/check names.',
        'Configure environments pypi/testpypi/github-release/github-pages with authorized reviewers and tag restrictions.',
        'On (Test)PyPI configure an OIDC trusted publisher for the exact repository, release.yml and matching environment.',
        'Enable CVRS_PUBLISH_ENABLED only after settings and reviewed artifacts are ready; dispatch release from the exact v<version> tag.',
        'Set Pages source to GitHub Actions and enable CVRS_PAGES_ENABLED after reviewing public docs/data.',
        'Connect GitHub to Zenodo and enable this repository; release archive/DOI is created there, never invented locally.',
        'Record generated DOI in citation metadata only after the archive exists.'
    ]
    result=LaunchPlan(repository=settings.get('repository_url') or 'OWNER_UNSET',package=settings['distribution_name'],
        release_version=state['version'],readiness='OWNER_ACTIONS_REQUIRED' if state['status']=='BLOCKED' else 'READY_FOR_REVIEW',
        owner_actions=actions,operations=[{'system':'GitHub Actions','operation':'install generated read-only build and gated publication workflows','executed':False},
            {'system':'PyPI','operation':'owner configures OIDC publisher','executed':False},
            {'system':'Zenodo','operation':'owner enables release archiving; CITATION.cff is used unless explicitly overridden','executed':False}]).model_dump(mode='json')
    result['approval_digest']=digest({k:v for k,v in result.items() if k!='approval_digest'})
    return result


def security_plan(repository: str, *, required_checks=None, branch='main', approving_reviews=0, observed_state=None) -> dict:
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):raise ValueError('use owner/repository, no URL or wildcard')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+',branch):raise ValueError('branch must be a simple reviewed name')
    if approving_reviews not in range(0,7):raise ValueError('review count must be 0..6')
    checks=sorted(set(required_checks or []))
    if any(not isinstance(x,str) or not x or len(x)>150 or '\n' in x for x in checks):raise ValueError('invalid required check name')
    prefix='/repos/'+repository
    operations=[{'id':'repository_security','method':'PATCH','path':prefix,'read_path':prefix,
        'payload':{'security_and_analysis':{'secret_scanning':{'status':'enabled'},'secret_scanning_push_protection':{'status':'enabled'}}}},
        {'id':'vulnerability_alerts','method':'PUT','path':prefix+'/vulnerability-alerts','read_path':prefix+'/vulnerability-alerts','payload':None},
        {'id':'automated_security_fixes','method':'PUT','path':prefix+'/automated-security-fixes','read_path':prefix+'/automated-security-fixes','payload':None},
        {'id':'private_vulnerability_reporting','method':'PUT','path':prefix+'/private-vulnerability-reporting','read_path':prefix+'/private-vulnerability-reporting','payload':None}]
    if checks:operations.append({'id':'branch_protection','method':'PUT','path':prefix+'/branches/'+branch+'/protection','read_path':prefix+'/branches/'+branch+'/protection',
        'payload':{'required_status_checks':{'strict':True,'checks':[{'context':x} for x in checks]},'enforce_admins':True,
        'required_pull_request_reviews':{'dismiss_stale_reviews':True,'required_approving_review_count':approving_reviews,'require_code_owner_reviews':False},
        'restrictions':None,'allow_force_pushes':False,'allow_deletions':False,'required_conversation_resolution':True}})
    value={'schema_version':'1.0','repository':repository,'branch':branch,'required_checks':checks,'approving_reviews':approving_reviews,
        'operations':operations,'expected_state':observed_state or {},'executed':False,
        'limits':['Plan does not inspect or change remote settings.','Existing branch protection requires an exact readback hash before replacement.',
                  'Reviewer count defaults to zero for a solo maintainer; change deliberately when other reviewers exist.',
                  'Availability/permissions depend on repository and account policy; errors are retained, never treated as enabled.']}
    value['plan_digest']=digest(value)
    return value


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise CVRSError('REMOTE_REDIRECT','GitHub administration requests must not redirect credentials')



def security_readback_matches(operation: dict, observation: dict) -> bool:
    """Check requested enablement fields, not merely an HTTP success status."""
    if observation.get('http_status') not in (200,204):return False
    body=observation.get('body') or {};kind=operation['id'];requested=operation.get('payload') or {}
    if kind=='repository_security':
        actual=body.get('security_and_analysis',{})
        return all(actual.get(k,{}).get('status')=='enabled' for k in requested['security_and_analysis'])
    if kind in {'automated_security_fixes','private_vulnerability_reporting'}:return body.get('enabled') is True
    if kind=='branch_protection':
        checks=body.get('required_status_checks') or {};expected=requested['required_status_checks']
        actual_contexts=set(checks.get('contexts',[]))|{x.get('context') for x in checks.get('checks',[])}
        expected_contexts={x['context'] for x in expected['checks']}
        reviews=body.get('required_pull_request_reviews') or {};wanted=requested['required_pull_request_reviews']
        return (checks.get('strict') is expected['strict'] and expected_contexts<=actual_contexts
            and body.get('enforce_admins',{}).get('enabled') is True
            and all(reviews.get(k)==v for k,v in wanted.items())
            and body.get('allow_force_pushes',{}).get('enabled') is False
            and body.get('allow_deletions',{}).get('enabled') is False
            and body.get('required_conversation_resolution',{}).get('enabled') is True
            and body.get('restrictions') is None)
    return kind=='vulnerability_alerts' and observation['http_status']==204


def apply_security_plan(plan: dict, *, approve_digest: str, allow_network: bool, destination: Path) -> dict:
    if not allow_network:raise CVRSError('NETWORK_NOT_AUTHORIZED','security changes require explicit --apply and the exact reviewed plan digest')
    payload=dict(plan);stored=payload.pop('plan_digest',None)
    if stored!=approve_digest or digest(payload)!=stored:raise ValueError('security plan approval mismatch')
    canonical=security_plan(plan['repository'],required_checks=plan['required_checks'],branch=plan['branch'],
        approving_reviews=plan['approving_reviews'],observed_state=plan.get('expected_state'))
    if canonical!=plan:raise ValueError('only generated enablement operations may be executed')
    token=os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token:raise CVRSError('AUTHENTICATION_REQUIRED','provide a suitably scoped GitHub token in GH_TOKEN; tokens are never written into receipts')
    from cvsubstrate.adoption.common import execution_tree
    opener=urllib.request.build_opener(_NoRedirect())
    def request(method,path,value=None):
        req=urllib.request.Request('https://api.github.com'+path,data=json.dumps(value).encode() if value is not None else None,method=method,
            headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2026-03-10','Content-Type':'application/json','User-Agent':'cvrs-reviewed-security-plan'})
        try:
            with opener.open(req,timeout=30) as r:
                raw=r.read(1024*1024+1)
                if len(raw)>1024*1024:raise ValueError('GitHub response exceeds limit')
                return {'http_status':r.status,'body':json.loads(raw) if raw else None}
        except urllib.error.HTTPError as e:
            if method=='GET' and e.code==404:return {'http_status':404,'body':None}
            raise CVRSError('GITHUB_OPERATION_FAILED',f'{method} {path}: HTTP {e.code}; stop and review permissions or account policy') from e
    results=[]
    with execution_tree(destination) as out:
        write_json(out/'approved-plan.json',plan)
        before={op['id']:request('GET',op['read_path']) for op in plan['operations']}
        write_json(out/'before.json',before)
        if before['repository_security']['http_status']!=200:raise ValueError('repository unavailable; no changes applied')
        for key,expected in plan.get('expected_state',{}).items():
            if key not in before or digest(before[key])!=expected:raise CVRSError('REMOTE_STATE_CHANGED',key+' differs from the reviewed snapshot; no changes applied')
        if 'branch_protection' in before and before['branch_protection']['http_status']==200 and 'branch_protection' not in plan.get('expected_state',{}):
            raise CVRSError('EXISTING_PROTECTION','existing branch rule will not be overwritten without its exact reviewed snapshot digest; no changes applied')
        for op in plan['operations']:
            response=request(op['method'],op['path'],op['payload'])
            after=request('GET',op['read_path'])
            ok=security_readback_matches(op,after)
            row={'operation':op['id'],'write_http_status':response['http_status'],'readback':after,'verified':ok}
            results.append(row);write_json(out/'operation-results.json',results)
            if not ok:raise CVRSError('READBACK_MISMATCH',op['id']+' did not report the requested state; prior operations may already have applied')
        write_json(out/'summary.json',{'status':'APPLIED_WITH_READBACK','operations':len(results),'remote_changes':True})
    return {'status':'APPLIED_WITH_READBACK','operations':results,'output':str(destination)}


def verify_artifacts(manifest_path: Path) -> dict:
    """Verify wheel/sdist identity and contents without importing or extracting code."""
    manifest_path=Path(manifest_path);value=read_json(manifest_path);base=manifest_path.parent
    payload=dict(value);expected=payload.pop('manifest_digest',None)
    if expected!=digest(payload):raise ValueError('release manifest digest mismatch')
    seen=set();kinds=set();rows=[]
    for rel,info in value['artifacts'].items():
        p=safe_join(base,rel)
        if rel in seen or p.is_symlink() or not p.is_file() or file_digest(p)!=info['sha256'] or p.stat().st_size!=info['bytes']:
            raise ValueError('changed/unsafe release artifact: '+rel)
        seen.add(rel)
        if p.suffix=='.whl':
            with zipfile.ZipFile(p) as z:
                metadata_names=[n for n in z.namelist() if n.endswith('.dist-info/METADATA')]
                if len(metadata_names)!=1 or z.getinfo(metadata_names[0]).file_size>2*1024*1024:raise ValueError('invalid wheel metadata')
                metadata=email.message_from_bytes(z.read(metadata_names[0]))
            kinds.add('wheel')
        elif p.name.endswith('.tar.gz'):
            with tarfile.open(p) as t:
                pkg_infos=[m for m in t.getmembers() if m.name.count('/')==1 and m.name.endswith('/PKG-INFO')]
                if len(pkg_infos)!=1 or not pkg_infos[0].isfile() or pkg_infos[0].size>2*1024*1024:raise ValueError('invalid source-distribution metadata')
                extracted=t.extractfile(pkg_infos[0])
                if extracted is None:raise ValueError('source-distribution metadata is unreadable')
                metadata=email.message_from_bytes(extracted.read())
            kinds.add('sdist')
        else:rows.append({'path':rel,'sha256':info['sha256']});continue
        if re.sub('[-_.]+','-',metadata['Name']).lower()!=re.sub('[-_.]+','-',value['distribution']).lower() or metadata['Version']!=value['version']:
            raise ValueError('package metadata differs from approved release identity')
        rows.append({'path':rel,'distribution':metadata['Name'],'version':metadata['Version'],'sha256':info['sha256']})
    if kinds!={'wheel','sdist'}:raise ValueError('release requires both wheel and source distribution')
    if value.get('tag')!='v'+value['version']:raise ValueError('release tag/version mismatch')
    actual={p.relative_to(base).as_posix() for p in (base/'packages').glob('*') if p.is_file()}
    if actual!={r for r in value['artifacts'] if r.startswith('packages/')}:raise ValueError('unlisted or missing publication package')
    return {'status':'VERIFIED','artifacts':rows,'manifest_digest':expected,'origin_authentication':'requires externally verified OIDC/Sigstore attestation'}


def contribution_check(root: Path) -> dict:
    root=Path(root);issues=[];checked=[]
    from cvsubstrate.product.recipes import check_recipe
    recipes=root/'src/cvsubstrate/resources/papers'
    for p in sorted(recipes.glob('*.json')):
        try:checked.append({'path':p.relative_to(root).as_posix(),'review':check_recipe(read_json(p))})
        except Exception as e:issues.append({'path':p.relative_to(root).as_posix(),'error':str(e)})
    for p in (root/'.github/workflows').glob('*.y*ml'):
        text=p.read_text()
        if 'pull_request_target' in text:issues.append({'path':str(p.relative_to(root)),'error':'privileged PR-target workflow is not allowed'})
        for use in re.findall(r'(?m)^\s*-?\s*uses:\s*[\'"]?([^\s\'"#]+)',text):
            if use.startswith('./'):continue
            if not re.fullmatch(r'[\w.-]+/[\w./-]+@[0-9a-f]{40}',use):issues.append({'path':str(p.relative_to(root)),'error':'action must use full commit SHA: '+use})
    return {'status':'FAILED' if issues else 'PASSED','recipe_count':len(checked),'recipes':checked,'issues':issues,
            'native_execution':'NOT_PERFORMED_BY_CONTRIBUTION_CHECK'}
