"""Registry fixtures explicitly do not represent a model or scientific finding."""
import copy
import pytest
from cvsubstrate.research.registry import ResearchRegistry,import_snapshot
from cvsubstrate.research.capsule import export_registry_capsule,import_registry_capsule
from cvsubstrate.provenance.io import digest,write_json,file_digest,read_json
from cvsubstrate.errors import CVRSError

def claim():
    return dict(title='Fixture <script>not executed</script>',question='Does the registry retain evidence?',dataset_sha256=digest({'dataset':'fixture'}),protocol_sha256=digest({'protocol':'fixture'}),experiment_sha256=digest({'experiment':'fixture'}),estimand='fixture metric',reported_metrics={'AP':.5},absolute_tolerances={'AP':.001},author_id='author',implementation_id='implementation-a',purpose='software_fixture')

def attempt(reg,cid,*,actor='author',machine='machine-a',implementation='implementation-a',score=.5,native=True):
    c=claim();pred=reg.add_json({'prediction_fixture':True})
    ev={'dataset':reg.add_json({'dataset':'fixture'}),'protocol':reg.add_json({'protocol':'fixture'}),'experiment':reg.add_json({'experiment':'fixture'}),'environment':reg.add_json({'env':'fixture'}),'predictions':pred}
    ev['execution']=reg.add_json({'status':'SUCCEEDED','operation':'predict','execution_kind':'native' if native else 'mock','purpose':'software_fixture','dataset_sha256':c['dataset_sha256'],'experiment_sha256':c['experiment_sha256'],'predictions_sha256':pred,'implementation_id':implementation})
    ev['evaluation']=reg.add_json({'status':'EVALUATED','dataset_sha256':c['dataset_sha256'],'protocol_sha256':c['protocol_sha256'],'predictions_sha256':pred,'metrics':{'AP':score},'evaluator_identity':{'name':'fixture_evaluator'}})
    return dict(claim_id=cid,actor_id=actor,machine_id=machine,implementation_id=implementation,dataset_sha256=c['dataset_sha256'],protocol_sha256=c['protocol_sha256'],experiment_sha256=c['experiment_sha256'],estimand=c['estimand'],outcome='completed',metrics={'AP':score},evidence=ev,purpose='software_fixture')

def test_registry_evidence_ladder_and_failed_attempts(tmp_path):
    with ResearchRegistry(tmp_path/'r') as reg:
        cid=reg.register_claim(claim());assert cid==reg.register_claim(claim())
        aid=reg.register_attempt(attempt(reg,cid));v=reg.assess_attempt(aid)
        assert v['level']=='R3_METRICS' and v['status'].startswith('FIXTURE_')
        failed=attempt(reg,cid,score=.2);fid=reg.register_attempt(failed)
        assert 'FAILED_TO_REPRODUCE' in reg.assess_attempt(fid)['status']
        blocked=attempt(reg,cid);blocked.update(outcome='blocked',failure_reason='Native library unavailable',metrics={})
        reg.register_attempt(blocked)
        status=reg.status(cid);assert status['failed_attempts']==1 and status['blocked_attempts']==1 and len(status['attempts'])==3
        assert reg.verify()['status']=='VERIFIED'

def test_no_native_claim_from_mock_no_independence_from_strings(tmp_path):
    with ResearchRegistry(tmp_path/'r') as reg:
        cid=reg.register_claim(claim())
        a=reg.register_attempt(attempt(reg,cid,native=False));assert reg.assess_attempt(a)['level']=='R1_ARTIFACTS'
        b=reg.register_attempt(attempt(reg,cid,actor='other',machine='other'));assert reg.assess_attempt(b)['level']=='R3_METRICS'
        with pytest.raises(ValueError):reg.register_review(dict(attempt_id=b,reviewer_id='other',independent_operator_attested=True,independent_machine_attested=True,rationale='self certification is not independent',evidence_sha256=reg.add_json({'x':1})))

def test_attestation_cross_impl_is_explicit_not_authentication(tmp_path):
    with ResearchRegistry(tmp_path/'r') as reg:
        cid=reg.register_claim(claim());reg.register_attempt(attempt(reg,cid))
        b=reg.register_attempt(attempt(reg,cid,actor='other',machine='machine-b',implementation='implementation-b'))
        reg.register_review(dict(attempt_id=b,reviewer_id='reviewer',independent_operator_attested=True,independent_machine_attested=True,independent_implementation_attested=True,rationale='Fixture attestation: no real independent scientist is claimed.',evidence_sha256=reg.add_json({'attestation':'test only'})))
        result=reg.assess_attempt(b);assert result['level'].startswith('R5_') and result['status']=='FIXTURE_INDEPENDENTLY_REPRODUCED_ATTESTED'
        assert reg.status(cid)['certification'].startswith('EVIDENCE_SCOPED')

def test_dataset_incompatibility_and_tamper_block_promotion(tmp_path):
    with ResearchRegistry(tmp_path/'r') as reg:
        cid=reg.register_claim(claim());a=attempt(reg,cid);a['dataset_sha256']='f'*64
        aid=reg.register_attempt(a);assert reg.assess_attempt(aid)['status']=='INCOMPARABLE'
        b=attempt(reg,cid);b['evidence']['dataset']=reg.add_json({'different_dataset':True})
        assert reg.assess_attempt(reg.register_attempt(b))['status']=='EVIDENCE_MISMATCH'
        p=reg.object_path(b['evidence']['predictions']);p.write_text('tamper')
        assert reg.verify()['status']=='FAILED'
        with pytest.raises(CVRSError):reg.export(tmp_path/'bad')

def test_supersession_cycle_snapshot_and_html_escaping(tmp_path):
    with ResearchRegistry(tmp_path/'r') as reg:
        cid=reg.register_claim(claim());c=claim();c['title']='New claim';new=reg.register_claim(c)
        reg.supersede(cid,new,'Corrected fixture interpretation')
        with pytest.raises(ValueError):reg.supersede(new,cid,'An invalid cycle of claims')
        reg.register_attempt(attempt(reg,cid));reg.export(tmp_path/'snapshot');head=reg.verify()['head']
    assert '<script>' not in (tmp_path/'snapshot/index.html').read_text()
    import_snapshot(tmp_path/'snapshot',tmp_path/'imported')
    with ResearchRegistry(tmp_path/'imported') as reg:
        assert reg.verify()['head']==head and reg.status(cid)['superseded_by'][0]['target']==new
    export_registry_capsule(tmp_path/'r',tmp_path/'capsule',tmp_path/'capsule.zip')
    import_registry_capsule(tmp_path/'capsule.zip',tmp_path/'restored')
    with ResearchRegistry(tmp_path/'restored') as reg:assert reg.verify()['head']==head

def test_failed_outcome_requires_reason_and_unavailable_evidence(tmp_path):
    with ResearchRegistry(tmp_path/'r') as reg:
        cid=reg.register_claim(claim());a=attempt(reg,cid);a['outcome']='failed'
        with pytest.raises(ValueError):reg.register_attempt(a)
        a['failure_reason']='Some failure';a['evidence']['missing']='b'*64
        with pytest.raises(CVRSError):reg.register_attempt(a)

def test_reevaluation_does_not_touch_predictions(dataset,tmp_path):
    from cvsubstrate.data.groundwork_fixtures import generate
    from cvsubstrate.research.reevaluate import reevaluate
    generate(tmp_path/'g');p=tmp_path/'g';before=file_digest(p/'fixture-predictions.jsonl')
    protocol={'evaluator':'diagnostic_detection','evaluator_version':'1'};write_json(p/'protocol.json',protocol)
    result=reevaluate(p/'base/dataset.json','dev',p/'fixture-predictions.jsonl',p/'protocol.json',tmp_path/'analysis')
    assert result['model_executed'] is False and file_digest(p/'fixture-predictions.jsonl')==before
    assert read_json(tmp_path/'analysis/evaluation.json')['operation']=='reevaluate'


def test_registry_verification_detects_deleted_rows_and_edges(tmp_path):
    with ResearchRegistry(tmp_path/'deleted') as reg:
        cid=reg.register_claim(claim());a=reg.register_attempt(attempt(reg,cid))
        reg.db.execute('DELETE FROM records WHERE id=?',(a,));reg.db.commit()
        assert reg.verify()['status']=='FAILED'
    with ResearchRegistry(tmp_path/'edge') as reg:
        cid=reg.register_claim(claim());c=claim();c['title']='Corrected';new=reg.register_claim(c)
        reg.supersede(cid,new,'A documented correction')
        reg.db.execute('DELETE FROM edges');reg.db.commit()
        assert reg.verify()['status']=='FAILED'

def test_original_receipt_cannot_be_relabelled_as_reproduction(tmp_path):
    with ResearchRegistry(tmp_path/'r') as reg:
        cid=reg.register_claim(claim());a=attempt(reg,cid);a['attempt_kind']='original'
        reg.register_attempt(a);a['attempt_kind']='reproduction';a['actor_id']='renamed-author'
        value=reg.assess_attempt(reg.register_attempt(a))
        assert value['level']=='R2_EXECUTION' and value['status']=='DUPLICATE_ORIGINAL_ARTIFACTS'

