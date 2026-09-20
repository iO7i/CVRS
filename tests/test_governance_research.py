from pathlib import Path
import json
import pytest
from cvsubstrate.governance.ledger import Ledger
from cvsubstrate.governance.policy import approve_final_test,consume_final_test,final_test_report
from cvsubstrate.contracts.research import AccessApproval
from cvsubstrate.provenance.io import digest,write_json
from cvsubstrate.provenance.bundle import RunBundle,verify_bundle
from cvsubstrate.provenance.recovery import recover_interrupted_run
from cvsubstrate.provenance.artifact_set import seal_directory,verify_directory
from cvsubstrate.errors import CVRSError

def test_ledger_chain_tamper_and_retained_head(tmp_path):
    l=Ledger(tmp_path/'events.jsonl')
    l.append('A',{'value':1});head=l.append('B',{'value':2})['digest']
    assert l.verify(head)['status']=='VERIFIED'
    lines=l.path.read_text().splitlines()
    l.path.write_text(lines[0]+'\n')
    assert l.verify()['status']=='VERIFIED' # Local truncation alone is not detectable.
    assert l.verify(head)['status']=='FAILED'
    data=json.loads(lines[0]);data['payload']['value']=4
    l.path.write_text(json.dumps(data)+'\n')
    assert l.verify()['status']=='FAILED'

def test_partial_line_is_not_silently_recovered(tmp_path):
    l=Ledger(tmp_path/'events.jsonl');l.append('A',{})
    with l.path.open('ab') as f:f.write(b'{"partial":')
    assert l.verify()['status']=='FAILED'
    with pytest.raises(CVRSError):l.append('B',{})

def test_one_use_identity_bound_approval(tmp_path):
    l=Ledger(tmp_path/'events.jsonl')
    a=AccessApproval(dataset_digest='a'*64,experiment_digest='b'*64,split='test',approved_by='owner',reason='locked final pass')
    approve_final_test(l,a)
    with pytest.raises(CVRSError):
        consume_final_test(l,digest(a),dataset_digest='c'*64,experiment_digest='b'*64,split='test')
    match,event=consume_final_test(l,digest(a),dataset_digest='a'*64,experiment_digest='b'*64,split='test')
    assert event['event']=='FINAL_TEST_ACCESS'
    with pytest.raises(CVRSError):
        consume_final_test(l,digest(a),dataset_digest='a'*64,experiment_digest='b'*64,split='test')
    with pytest.raises(CVRSError):approve_final_test(l,a)
    assert final_test_report(l)['access_attempts']==1

def test_recover_only_interrupted_unsealed_run(tmp_path):
    b=RunBundle(tmp_path,'a'*64,'b'*64)
    write_json(b.path/'partial.json',{'done':False})
    with pytest.raises(CVRSError):recover_interrupted_run(b.path,reason='worker stopped',acknowledge_process_stopped=False)
    r=recover_interrupted_run(b.path,reason='worker manually confirmed stopped',acknowledge_process_stopped=True)
    assert r['status']=='VERIFIED' and r['run_state']=='INTERRUPTED'
    with pytest.raises(CVRSError):recover_interrupted_run(b.path,reason='again',acknowledge_process_stopped=True)

def test_artifact_set_covers_nested_manifests_and_new_files(tmp_path):
    p=tmp_path/'artifact';p.mkdir();write_json(p/'nested'/'artifacts.json',{'x':1})
    seal_directory(p);assert verify_directory(p)['status']=='VERIFIED'
    write_json(p/'new.json',{})
    assert verify_directory(p)['status']=='FAILED'

def test_run_manifest_covers_nested_manifest_files(tmp_path):
    b=RunBundle(tmp_path,'a'*64,'b'*64);write_json(b.path/'nested'/'artifacts.json',{'fake':False})
    b.finish('SUCCEEDED');assert verify_bundle(b.path)['status']=='VERIFIED'
    write_json(b.path/'nested'/'artifacts.json',{'fake':True})
    assert verify_bundle(b.path)['status']=='FAILED'
