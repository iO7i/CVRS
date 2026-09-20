from pathlib import Path
import sys
import pytest
from cvsubstrate.contracts.models import ExperimentSpec,CheckpointRef
from cvsubstrate.contracts.research import TilingPolicy,AccessApproval
from cvsubstrate.data.research_fixtures import generate_research_fixtures
from cvsubstrate.campaigns.engine import execute_campaign
from cvsubstrate.campaigns.report import campaign_report
from cvsubstrate.execution.runner import run_experiment
from cvsubstrate.execution.tiled import run_tiled
from cvsubstrate.provenance.io import read_json,read_jsonl,write_json,digest,experiment_identity,file_digest
from cvsubstrate.provenance.bundle import verify_bundle
from cvsubstrate.governance.ledger import Ledger
from cvsubstrate.governance.policy import approve_final_test,final_test_report
from cvsubstrate.governance.execution import run_final_test

pytestmark=pytest.mark.native


def test_six_arm_real_model_campaign_resume_and_tiled_checkpoint(tmp_path):
    pytest.importorskip('torch');pytest.importorskip('torchvision')
    d=tmp_path/'input';generate_research_fixtures(d)
    campaign=execute_campaign(d/'campaign.json',tmp_path/'campaign',worker_python=sys.executable)
    assert campaign['status']=='SUCCEEDED' and campaign['counts']['SUCCEEDED']==6
    before=Ledger(tmp_path/'campaign/events.jsonl').verify()
    assert execute_campaign(d/'campaign.json',tmp_path/'campaign',resume=True)['status']=='SUCCEEDED'
    assert Ledger(tmp_path/'campaign/events.jsonl').verify()==before
    report=campaign_report(tmp_path/'campaign')
    assert report['scope']=='SOFTWARE_FIXTURE_EVIDENCE'
    assert all(r['status']=='SUCCEEDED' and r['metric'] is not None for r in report['results'])
    rows={r['arm']:r for r in report['results']}
    assert rows['R+S']['measured_counts']['real_exposures']==rows['R']['measured_counts']['real_exposures']==1
    assert rows['R-replay']['measured_counts']['real_exposures']==2
    assert rows['R-replay']['measured_counts']['synthetic_exposures']==0
    assert rows['R->R']['measured_counts']['optimizer_updates']==2
    for row in report['results']:
        run=tmp_path/'campaign'/row['run'];result=read_json(run/'worker_result.json')
        assert result['parameters_changed'] and result['checkpoint_roundtrip_predictions_exact']
    realrun=tmp_path/'campaign'/rows['R']['run'];ck=realrun/'worker/checkpoint.pt'
    spec=ExperimentSpec.model_validate(read_json(d/'inference.json'))
    spec.checkpoint=CheckpointRef(path=str(ck),sha256=file_digest(ck))
    write_json(d/'trained-tiled.json',spec)
    out=run_tiled(d/'trained-tiled.json',TilingPolicy.model_validate(read_json(d/'tiling.json')),tmp_path/'tiles',worker_python=sys.executable)
    assert verify_bundle(out)['status']=='VERIFIED'
    predictions=read_jsonl(out/'predictions.jsonl');assert len(predictions)==4
    audit=read_json(out/'merge_audit.json')
    assert audit['reconciled'] is True
    assert read_json(out/'tiling_plan.json')['source_images']==4
    assert read_json(out/'worker_result.json')['parameters_changed'] is False


def test_locked_test_real_native_inference_records_single_use(dataset,real_spec,tmp_path):
    pytest.importorskip('torch');pytest.importorskip('torchvision')
    m,root=dataset;m.splits['dev'].role='locked_test';write_json(root/'dataset.json',m)
    real_spec.training=None;real_spec.dataset_sha256=digest(m);write_json(root/'final.json',real_spec)
    ledger=Ledger(tmp_path/'ledger.jsonl')
    approval=AccessApproval(dataset_digest=digest(m),experiment_digest=experiment_identity(real_spec),split='dev',approved_by='fixture-test',reason='test exact local policy')
    ad=approve_final_test(ledger,approval)['payload']['approval_digest']
    result=run_final_test(root/'final.json',tmp_path/'runs',ledger,ad,worker_python=sys.executable)
    assert result['verification']['status']=='VERIFIED'
    assert final_test_report(ledger)['access_attempts']==1
    assert (Path(result['run'])/'final_test_access_receipt.json').exists()
