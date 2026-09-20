"""Release/product checks use local artifacts, never mutate external accounts."""
from pathlib import Path
import json
import os
import zipfile
import tarfile
import io
import pytest
from cvsubstrate.provenance.io import read_json,write_json,digest,file_digest,read_jsonl
from cvsubstrate.product.launch import (preflight,workflow_documents,action_lock,security_plan,apply_security_plan,
                                      verify_artifacts,contribution_check,generate_workflows)
from cvsubstrate.product.compatibility import make_receipt,render_badge,freeze_api,compare_api
ROOT=Path(__file__).resolve().parents[1]


def test_owner_preflight_accepts_explicit_release_identity():
    r=preflight(ROOT)
    assert r['status']=='READY_FOR_OWNER_RELEASE_REVIEW'
    assert r['remote_state']=='NOT_CONTACTED'
    required={'identity approval','source license approval','authors','copyright holder','security contact','repository identity'}
    assert required<=set(x['name'] for x in r['checks'] if x['status']=='PASS')


def test_workflow_permissions_and_immutable_pins():
    docs=workflow_documents()
    release=docs['release.yml']
    assert 'pull_request_target' not in repr(docs)
    assert release['permissions']=={'contents':'read'}
    assert 'id-token' not in release['jobs']['build'].get('permissions',{})
    assert release['jobs']['publish']['permissions']['id-token']=='write'
    assert 'environment' in release['jobs']['publish']
    assert not any('run' in s for s in release['jobs']['publish']['steps'])
    assert not any('checkout' in s.get('uses','') for s in release['jobs']['publish']['steps'])
    assert 'CVRS_PUBLISH_ENABLED' in release['jobs']['build']['if']
    for doc in docs.values():
        for job in doc['jobs'].values():
            for step in job.get('steps',[]):
                if 'uses' in step:assert len(step['uses'].split('@')[-1])==40
    assert action_lock()['checked_on']=='2026-09-19'


def test_workflow_generator_and_contributions(tmp_path):
    pytest.importorskip('yaml')
    result=generate_workflows(ROOT,tmp_path/'workflows')
    assert result['remote_operations']==0
    assert contribution_check(ROOT)['status']=='PASSED'
    content=(tmp_path/'workflows/.github/workflows/release.yml').read_text()
    assert 'password:' not in content and 'skip-existing: false' in content


def test_security_plan_network_approval_and_endpoint_scope(tmp_path):
    p=security_plan('example-org/example-repo',required_checks=['Core (3.13)'])
    assert not p['executed'] and p['approving_reviews']==0
    from cvsubstrate.errors import CVRSError
    with pytest.raises(CVRSError):apply_security_plan(p,approve_digest=p['plan_digest'],allow_network=False,destination=tmp_path/'no')
    assert not (tmp_path/'no').exists()
    with pytest.raises(ValueError):security_plan('https://attacker.example/a/b')
    q=json.loads(json.dumps(p));q['operations'][0]['path']='/user';q.pop('plan_digest');q['plan_digest']=digest(q)
    with pytest.raises(ValueError,match='generated'):apply_security_plan(q,approve_digest=q['plan_digest'],allow_network=True,destination=tmp_path/'no')
    assert not (tmp_path/'no').exists()


def test_receipt_never_self_certifies(tmp_path):
    d={'subject_id':'owned-fixture','task':'hbb_detection','operation':'predict','implementation':'AVAILABLE'}
    r=make_receipt(d)
    assert r['execution']=='NOT_RUN' and r['reference_evaluation']=='NOT_RUN'
    render_badge(r,tmp_path/'badge.svg')
    assert 'adapter available' in (tmp_path/'badge.svg').read_text()
    with pytest.raises(ValueError):make_receipt({**d,'execution':'SUCCEEDED'})
    r['execution']='SUCCEEDED'
    with pytest.raises(ValueError):render_badge(r,tmp_path/'forged.svg')


def test_scoped_receipt_binds_real_files_not_just_manifest(tmp_path):
    from cvsubstrate.provenance.artifact_set import seal_directory
    d={'subject_id':'owned-fixture','task':'hbb_detection','operation':'predict','implementation':'AVAILABLE'}
    out=tmp_path/'execution';out.mkdir()
    write_json(out/'output.json',{'boxes':[]})
    write_json(out/'compatibility-execution.json',{**d,'status':'SUCCEEDED','worker_sha256':'a'*64,
        'result_artifacts':[{'path':'output.json','sha256':file_digest(out/'output.json')}]})
    seal_directory(out)
    r=make_receipt(d,out)
    assert r['execution']=='SUCCEEDED' and r['reproduction']=='NOT_RUN'
    with pytest.raises(Exception):make_receipt({**d,'task':'masks'},out)
    (out/'output.json').write_text('{}')
    with pytest.raises(Exception):make_receipt(d,out)


def test_public_surface_frozen_and_structural_change_review(tmp_path):
    freeze_api(ROOT,tmp_path/'before.json');old=read_json(tmp_path/'before.json')
    assert 'content_id' in old['symbols'] and len(old['schemas'])>=129
    assert compare_api(old,old)['status']=='STRUCTURALLY_COMPATIBLE'
    new=json.loads(json.dumps(old));new['symbols'].pop('content_id');new.pop('surface_digest');new['surface_digest']=digest(new)
    assert compare_api(old,new)['status']=='BREAKING'
    new=json.loads(json.dumps(old));new['schemas']['RichFrame']['description']='changed';new.pop('surface_digest');new['surface_digest']=digest(new)
    assert compare_api(old,new)['status']=='REVIEW_REQUIRED'


def release_fixture(root):
    packages=root/'packages';packages.mkdir()
    metadata=b'Metadata-Version: 2.4\nName: test-release\nVersion: 0.0.1\n'
    with zipfile.ZipFile(packages/'test_release-0.0.1-py3-none-any.whl','w') as z:z.writestr('test_release-0.0.1.dist-info/METADATA',metadata)
    with tarfile.open(packages/'test_release-0.0.1.tar.gz','w:gz') as t:
        x=tarfile.TarInfo('test_release-0.0.1/PKG-INFO');x.size=len(metadata);t.addfile(x,io.BytesIO(metadata))
    value={'distribution':'test-release','version':'0.0.1','tag':'v0.0.1','artifacts':{
        p.relative_to(root).as_posix():{'sha256':file_digest(p),'bytes':p.stat().st_size} for p in packages.iterdir()}}
    value['manifest_digest']=digest(value);write_json(root/'release-artifacts.json',value)
    return root/'release-artifacts.json'


def test_release_verification_and_unlisted_package_rejection(tmp_path):
    path=release_fixture(tmp_path)
    assert verify_artifacts(path)['status']=='VERIFIED'
    (tmp_path/'packages/injected.whl').write_text('not a package')
    with pytest.raises(ValueError,match='unlisted'):verify_artifacts(path)


def test_native_array_decoders_preserve_semantic_artifacts(tmp_path):
    np=pytest.importorskip('numpy')
    from cvsubstrate.product.bridges import decode_arrays
    from cvsubstrate.adoption.contracts import SemanticLabelMap
    p=tmp_path/'native.npz';np.savez(p,maps=np.array([[[0,1],[255,0]]],dtype=np.uint8))
    spec={'sha256':file_digest(p),'task':'semantic_segmentation','array':'maps','layout':'NHW',
          'category_mapping':{'0':3,'1':7},'ignore_index':255,'samples':[{'id':'image','width':2,'height':2}]}
    result=decode_arrays(p,spec,tmp_path/'decoded')
    row=SemanticLabelMap.model_validate(read_jsonl(tmp_path/'decoded/predictions.jsonl')[0])
    assert file_digest(tmp_path/'decoded'/row.labels)==row.sha256
    assert np.load(tmp_path/'decoded'/row.labels).tolist()==[[3,7],[255,3]]
    assert result['samples']==1


def test_array_decoder_rejects_noninteger_counts_and_nonfinite_logits(tmp_path):
    np=pytest.importorskip('numpy');from cvsubstrate.product.bridges import decode_arrays
    p=tmp_path/'native.npz';np.savez(p,boxes=np.array([[[0,0,1,1]]]),scores=np.array([[.9]]),labels=np.array([[1]]),counts=np.array([.5]))
    spec={'sha256':file_digest(p),'task':'hbb_detection','counts':'counts','category_mapping':{'1':1},'samples':[{'id':'i','width':2,'height':2}]}
    with pytest.raises(ValueError):decode_arrays(p,spec,tmp_path/'bad')
    p2=tmp_path/'logits.npz';np.savez(p2,v=np.full((1,2,2,2),float('nan')))
    with pytest.raises(ValueError):decode_arrays(p2,{**spec,'sha256':file_digest(p2),'task':'semantic_segmentation','layout':'NCHW','array':'v'},tmp_path/'bad2')


def test_browser_escapes_and_preserves_source_readonly(tmp_path):
    from cvsubstrate.product.browser import collect_catalog,render_browser
    run=tmp_path/'source'/'run';run.mkdir(parents=True)
    write_json(run/'run.json',{'run_id':'<script>alert(1)</script>','status':'SUCCEEDED'})
    write_json(run/'experiment.json',{'task':'hbb_detection','purpose':'software_fixture','model':{'backend':'native'},'evaluation':{'score_threshold':.5}})
    write_json(run/'metrics.json',{'diagnostic_ap':.3})
    write_json(run/'dataset_manifest.json',{'name':'fixture','purpose':'software_fixture','samples':[],'splits':{},'categories':[]})
    before={p.name:file_digest(p) for p in run.iterdir()}
    data=collect_catalog(tmp_path/'source')
    assert data['runs'][0]['integrity']=='NOT_CHECKED'
    render_browser(data,tmp_path/'site')
    html=(tmp_path/'site/index.html').read_text()
    assert '<script>alert(1)</script>' not in html and '\\u003cscript' in html
    assert all(file_digest(run/name)==sha for name,sha in before.items())
    assert (tmp_path/'site/app.js').is_file()


def test_cli_release_gate_exit_code():
    import subprocess,sys
    r=subprocess.run([sys.executable,'-m','cvsubstrate','release','preflight',str(ROOT)],capture_output=True,text=True)
    assert r.returncode==0 and json.loads(r.stdout)['status']=='READY_FOR_OWNER_RELEASE_REVIEW'


def test_security_readback_requires_requested_fields():
    from cvsubstrate.product.launch import security_readback_matches
    plan=security_plan('example-org/example-repo',required_checks=['Core'])
    op=plan['operations'][-1]
    assert not security_readback_matches(op,{'http_status':200,'body':{}})
    body={'required_status_checks':{'strict':True,'contexts':['Core']},'enforce_admins':{'enabled':True},
          'required_pull_request_reviews':op['payload']['required_pull_request_reviews'],
          'allow_force_pushes':{'enabled':False},'allow_deletions':{'enabled':False},
          'required_conversation_resolution':{'enabled':True},'restrictions':None}
    assert security_readback_matches(op,{'http_status':200,'body':body})
    body['required_status_checks']['contexts']=[]
    assert not security_readback_matches(op,{'http_status':200,'body':body})


def test_versioned_docs_preserve_existing_versions(tmp_path):
    from cvsubstrate.product.browser import versioned_portal
    roots=[]
    for version in ('0.6.0a1','0.7.0a1'):
        p=tmp_path/version;p.mkdir();(p/'index.html').write_text('<html><body>'+version+'</body></html>')
        write_json(p/'versions.json',{'current':version,'available':[version]});roots.append(p)
    result=versioned_portal(roots,tmp_path/'site')
    assert result['versions']==['0.7.0a1','0.6.0a1']
    assert (tmp_path/'site/versions/0.6.0a1/index.html').read_text()==(roots[0]/'index.html').read_text()
    with pytest.raises(ValueError,match='duplicate'):versioned_portal([roots[0],roots[0]],tmp_path/'bad')


def test_citation_requires_owner_and_never_invents_doi(tmp_path):
    from cvsubstrate.product.academic import citation_pack
    approved=citation_pack(ROOT,tmp_path/'approved')
    assert approved['doi'] is None and approved['remote_operations']==0
    assert 'doi' not in read_json(tmp_path/'approved/CITATION.cff')
    source=tmp_path/'owned';source.mkdir();(source/'src/cvsubstrate').mkdir(parents=True)
    (source/'src/cvsubstrate/_version.py').write_text('__version__ = "0.0.1"\n')
    (source/'pyproject.toml').write_text('[project]\nname = "owned-fixture"\nversion = "0.0.1"\n')
    (source/'LICENSE').write_text('Owned software test fixture license text; not the project grant.\n')
    settings=read_json(ROOT/'PUBLICATION.json')
    settings.update(identity_approved=True,license_approved=True,license_id='MIT',
        display_name='Owned fixture',repository_url='https://github.com/example-org/owned-fixture',
        copyright_holder='Fixture author',authors=[{'name':'Owned fixture author'}])
    write_json(source/'PUBLICATION.json',settings)
    result=citation_pack(source,tmp_path/'citation')
    assert result['doi'] is None and result['remote_operations']==0
    assert 'doi' not in read_json(tmp_path/'citation/CITATION.cff')
    with pytest.raises(ValueError):citation_pack(source,tmp_path/'bad-doi',doi='10.1234/test')


def test_owner_metadata_updates_explicit_authors_without_remote_changes(tmp_path):
    from cvsubstrate.publication.metadata import configure
    root=tmp_path/'metadata';root.mkdir()
    write_json(root/'PUBLICATION.json',read_json(ROOT/'PUBLICATION.json'))
    (root/'pyproject.toml').write_text('[project]\nname = "cv-research-substrate"\nlicense = "LicenseRef-Owner-Decision-Pending"\n[project.urls]\nRepository = "https://github.com/example-org/old"\n')
    s=read_json(ROOT/'PUBLICATION.json');s.update(authors=[{'name':'Explicit Author','email':'fixture@example.invalid'}],repository_url='https://github.com/example-org/new')
    configure(root,s,license_text=(ROOT/'LICENSE').read_text())
    import tomllib
    value=tomllib.loads((root/'pyproject.toml').read_text())
    assert value['project']['authors']==s['authors'] and value['project']['urls']['Repository']==s['repository_url']
    assert read_json(root/'PUBLICATION.json')['identity_approved'] is True


@pytest.mark.parametrize('registry_name',['registry.sqlite','registry-v2.sqlite'])
def test_browser_reads_both_registry_generations_without_mutation(tmp_path,registry_name):
    import sqlite3
    from cvsubstrate.product.browser import collect_catalog
    root=tmp_path/'records';root.mkdir();db=root/registry_name
    c=sqlite3.connect(db)
    c.execute('CREATE TABLE records(id TEXT,kind TEXT,payload TEXT)')
    if registry_name=='registry.sqlite':c.execute('CREATE TABLE edges(source TEXT,target TEXT,reason TEXT)')
    else:c.execute('CREATE TABLE edges(id TEXT,payload TEXT)')
    claim={'title':'Owned browser fixture','purpose':'software_fixture'};claim_id=digest({'kind':'claim','payload':claim})
    c.execute('INSERT INTO records VALUES(?,?,?)',(claim_id,'claim',json.dumps(claim)))
    attempt={'claim_id':claim_id,'status':'BLOCKED','purpose':'software_fixture'};attempt_id=digest({'kind':'attempt','payload':attempt})
    c.execute('INSERT INTO records VALUES(?,?,?)',(attempt_id,'attempt',json.dumps(attempt)));c.commit();c.close()
    before=file_digest(db);result=collect_catalog(root)
    assert len(result['claims'])==1 and len(result['attempts'])==1 and result['issues']==[]
    assert file_digest(db)==before


def test_browser_preserves_adapter_checkpoint_and_run_state(tmp_path):
    from cvsubstrate.product.browser import collect_catalog
    p=tmp_path/'run';p.mkdir()
    write_json(p/'run.json',{'run_id':'test','state':'SUCCEEDED'})
    write_json(p/'experiment.json',{'adapter':{'name':'native_torch','config':{}},'evaluation':{'task':'hbb_detection'}})
    write_json(p/'worker_result.json',{'checkpoint_sha256':'c'*64})
    result=collect_catalog(tmp_path)
    assert result['runs'][0]['status']=='SUCCEEDED'
    assert result['runs'][0]['task']=='hbb_detection'
    assert len(result['models'])==1 and result['models'][0]['title']=='native_torch'
    assert result['models'][0]['definition']['result_checkpoint_sha256']=='c'*64


def test_source_and_other_tree_schema_identities_match(tmp_path):
    import shutil
    other = tmp_path/'other-source'
    shutil.copytree(ROOT/'src', other/'src', ignore=shutil.ignore_patterns('__pycache__', '*.egg-info'))
    shutil.copytree(ROOT/'schemas', other/'schemas')
    freeze_api(ROOT, tmp_path/'local.json')
    freeze_api(other, tmp_path/'foreign.json')
    local, foreign = read_json(tmp_path/'local.json'), read_json(tmp_path/'foreign.json')
    assert 'RichFrame' in foreign['schemas']
    assert not any(name.endswith('.schema') for name in foreign['schemas'])
    assert local['schemas'] == foreign['schemas']
    assert compare_api(local, foreign)['status'] == 'STRUCTURALLY_COMPATIBLE'
    shutil.copyfile(other/'schemas/RichFrame.schema.json', other/'schemas/RichFrame.json')
    with pytest.raises(ValueError, match='duplicate canonical schema identity'):
        freeze_api(other, tmp_path/'duplicate.json')


def test_release_manifest_covers_nested_historical_manifests(tmp_path):
    from cvsubstrate.release import package_release, verify_release
    source=tmp_path/'source';source.mkdir()
    (source/'pyproject.toml').write_text('[project]\nname = "release-fixture"\nversion = "0.1.0"\n')
    write_json(source/'docs/history/old/RELEASE_MANIFEST.json', {'historical':'kept'})
    result=package_release(source,tmp_path/'release.zip')
    assert result['manifest_files'] > 1
    manifest=read_json(source/'RELEASE_MANIFEST.json')
    assert 'docs/history/old/RELEASE_MANIFEST.json' in manifest['files']
    assert verify_release(source)['status']=='VERIFIED'
    write_json(source/'docs/history/old/RELEASE_MANIFEST.json', {'historical':'tampered'})
    assert verify_release(source)['status']=='FAILED'
