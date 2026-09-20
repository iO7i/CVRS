import json
from pathlib import Path
import sys
import pytest
from cvsubstrate.cli import main
from cvsubstrate.contracts.models import WorkerRequest,WorkerResponse,ExperimentSpec,GenerationMetadata
from cvsubstrate.contracts.research import CampaignSpec,BackendTemplate,AccessApproval
from cvsubstrate.protocols.planner import plan
from cvsubstrate.campaigns.engine import plan_campaign,execute_campaign,load_campaign
from cvsubstrate.campaigns.report import campaign_report
from cvsubstrate.governance.ledger import Ledger
from cvsubstrate.governance.policy import preregister,approve_final_test,final_test_report
from cvsubstrate.provenance.io import write_json,read_json,digest,experiment_identity,file_digest
from cvsubstrate.provenance.bundle import RunBundle,verify_bundle
from cvsubstrate.execution.plugins import WorkerPlugin,invoke_external
from cvsubstrate.reporting.research import publish_report
from cvsubstrate.analysis.statistics import summarize_seeds,paired_seed_difference
from cvsubstrate.errors import CVRSError


def campaign(spec,**kwargs):
    return CampaignSpec(name='test-campaign',backends=[BackendTemplate(name='test-backend',experiment=spec)],
        seeds=[101],updates=1,pretrain_updates=1,rationale='test execution accounting',**kwargs)


def test_six_arm_graph_and_real_stream_preservation(dataset,real_spec):
    m,root=dataset;c=campaign(real_spec);p=plan_campaign(c,root)
    assert len(p['cases'])==6 and len(p['execution_graph'])==8
    arms={v['arm']:v['protocol_plan'] for v in p['cases']}
    assert arms['R']['stages'][0]['steps'][0]['real']==arms['R+S']['stages'][0]['steps'][0]['real']
    assert arms['R']['stages'][0]['steps'][0]['real']==arms['R-replay']['stages'][0]['steps'][0]['real_primary']
    assert arms['R+S']['planned_counts']['synthetic_exposures']==1
    assert arms['R-replay']['planned_counts']['synthetic_exposures']==0
    assert arms['R-replay']['planned_counts']['real_exposures']==2
    assert arms['S->R']['planned_counts']['optimizer_updates']==2
    assert arms['R->R']['planned_counts']['real_exposures']==2


def test_seed_governance_study_requires_three_new_seeds(dataset,real_spec,tmp_path):
    with pytest.raises(ValueError):CampaignSpec.model_validate({**campaign(real_spec).model_dump(),'phase':'confirmatory'})
    initial=campaign(real_spec);ledger=Ledger(tmp_path/'ledger')
    preregister(ledger,initial,'a'*64)
    confirm=CampaignSpec.model_validate({**initial.model_dump(),'phase':'confirmatory','seeds':[101,102,103],'selection_record_digest':'f'*64})
    with pytest.raises(CVRSError,match='seed'):preregister(ledger,confirm,'b'*64)
    confirm=CampaignSpec.model_validate({**initial.model_dump(),'phase':'confirmatory','seeds':[104,105,106],'selection_record_digest':'f'*64})
    preregister(ledger,confirm,'b'*64)
    assert ledger.verify()['entries']==2


def test_campaign_different_data_protocol_refused(dataset,real_spec):
    _,root=dataset;c=campaign(real_spec)
    second=real_spec.model_copy(deep=True);second.evaluation.iou_thresholds=[.75]
    c.backends.append(BackendTemplate(name='other',experiment=second))
    with pytest.raises(CVRSError):plan_campaign(c,root)


def test_campaign_failure_resume_keeps_missing_cases(dataset,real_spec,tmp_path,monkeypatch):
    import cvsubstrate.campaigns.engine as engine
    _,root=dataset;c=campaign(real_spec);write_json(root/'campaign.json',c)
    calls=[]
    def failure(*a,**kw):calls.append(a);raise CVRSError('ADAPTER_NOT_INSTALLED','expected fixture blocker')
    monkeypatch.setattr(engine,'run_experiment',failure)
    out=tmp_path/'runs'
    r=execute_campaign(root/'campaign.json',out);assert r['counts']['BLOCKED']==6
    assert len(calls)==6
    r=execute_campaign(root/'campaign.json',out,resume=True);assert len(calls)==6
    report=campaign_report(out);assert len(report['results'])==6 and all(x['metric'] is None for x in report['results'])
    execute_campaign(root/'campaign.json',out,resume=True,retry_failed=True);assert len(calls)==12
    changed=c.model_copy(deep=True);changed.seeds=[999];write_json(root/'campaign.json',changed)
    with pytest.raises(CVRSError):execute_campaign(root/'campaign.json',out,resume=True)


def test_seeds_missing_not_silently_dropped():
    value=summarize_seeds({1:1.,2:None,3:3.});assert value['mean']==2. and value['missing_seeds']==[2]
    assert summarize_seeds({1:1.})['sample_std'] is None
    r=paired_seed_difference({1:1.,2:2.,3:3.},{1:2.,2:3.,3:4.},bootstrap_samples=100)
    assert r['mean']==1.
    assert paired_seed_difference({1:1.},{1:2.})['bootstrap_interval_95'] is None


def test_legacy_authorization_does_not_bypass_ledger(dataset,real_spec,tmp_path):
    from cvsubstrate.execution.runner import run_experiment
    m,root=dataset;m.splits['dev'].role='locked_test';write_json(root/'dataset.json',m)
    real_spec.training=None;real_spec.dataset_sha256=digest(m);write_json(root/'final.json',real_spec)
    with pytest.raises(CVRSError,match='ledger'):
        run_experiment(root/'final.json',tmp_path/'run',authorization={'fake':'authorization'})


def test_governed_final_attempt_failure_still_charged(dataset,real_spec,tmp_path):
    from cvsubstrate.governance.execution import run_final_test
    m,root=dataset;m.splits['dev'].role='locked_test';write_json(root/'dataset.json',m)
    real_spec.training=None;real_spec.dataset_sha256=digest(m);write_json(root/'final.json',real_spec)
    ledger=Ledger(tmp_path/'ledger')
    a=AccessApproval(dataset_digest=digest(m),experiment_digest=experiment_identity(real_spec),split='dev',approved_by='test-operator',reason='test accounting on fixture')
    approval=approve_final_test(ledger,a)['payload']['approval_digest']
    with pytest.raises(CVRSError):run_final_test(root/'final.json',tmp_path/'out',ledger,approval,worker_python='/missing/python')
    assert final_test_report(ledger)['access_attempts']==1
    with pytest.raises(CVRSError,match='remaining'):run_final_test(root/'final.json',tmp_path/'out',ledger,approval)
    assert final_test_report(ledger)['access_attempts']==1


def test_plugin_explicit_trust_hash_and_subprocess(tmp_path):
    script=tmp_path/'plugin.py'
    script.write_text("import json,argparse\np=argparse.ArgumentParser();p.add_argument('--request');p.add_argument('--response');a=p.parse_args()\njson.dump({'schema_version':'1.0','protocol_version':'1.0','status':'SUCCEEDED','result':{'installed':False,'fixture':True}},open(a.response,'w'))\n")
    plugin=WorkerPlugin(id='test',script=str(script),script_sha256=file_digest(script))
    with pytest.raises(CVRSError):invoke_external(plugin,WorkerRequest(operation='capabilities'))
    plugin.trust_executable_code=True
    value=invoke_external(plugin,WorkerRequest(operation='capabilities'))
    assert value.result['fixture'] is True
    script.write_text('raise SystemExit(42)')
    with pytest.raises(CVRSError,match='changed'):invoke_external(plugin,WorkerRequest(operation='capabilities'))


def test_ledger_symlink_refused(tmp_path, symlink_or_skip):
    target=tmp_path/'real';Ledger(target).append('EVENT',{})
    link=tmp_path/'symlink';symlink_or_skip(link, target)
    with pytest.raises(CVRSError):Ledger(link).rows()


def test_cli_new_commands_roundtrip(tmp_path,capsys):
    d=tmp_path/'demo'
    assert main(['research-fixtures',str(d)])==0
    assert main(['campaign','plan',str(d/'campaign.json')])==0
    assert main(['synthetic','validate',str(d/'sidecars/generic.canonical.json')])==0
    assert main(['synthetic','map',str(d/'sidecars/unreal-shaped.source.json'),'--mapping',str(d/'sidecars/unreal-shaped.mapping.json'),'--out',str(d/'new.json')])==0
    assert main(['domain','describe',str(d/'images/dataset.json'),'--out',str(d/'domain-report')])==0
    assert main(['artifact-verify',str(d/'domain-report')])==0
    assert main(['dota','import','--images',str(d/'dota-images'),'--labels',str(d/'dota-labels'),'--categories',str(d/'dota-categories.json'),'--name','fixture','--dataset-version','fixture1','--out',str(d/'dota-images/dataset.json')])==0
    assert main(['dota','validate',str(d/'dota-images/dataset.json')])==0
    assert main(['schemas',str(d/'schemas')])==0
    assert len(list((d/'schemas').glob('*.json')))>=43
    assert main(['capsule','--packages','pydantic','not-installed-fixture','--out',str(d/'capsule')])==0
    assert read_json(d/'capsule/capsule.json')['missing_packages']==['not-installed-fixture']


def test_missing_pair_is_not_declared_all_present():
    report=paired_seed_difference({1:1.,2:2.},{1:2.,2:None})
    assert report['all_declared_seeds_present'] is False
    assert report['missing_seeds']==[2]
    assert report['per_seed']['2'] is None
