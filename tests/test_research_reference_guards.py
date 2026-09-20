from pathlib import Path
import pytest
from cvsubstrate.contracts.models import Category,LegacyExperimentRef,LicenseInfo
from cvsubstrate.data.research_fixtures import generate_research_fixtures
from cvsubstrate.contracts.research import OrientedPrediction
from cvsubstrate.data.dota import import_dota
from cvsubstrate.evaluation.reference_dota import DotaReference,run_reference
from cvsubstrate.execution.heritage import certify_run
from cvsubstrate.provenance.io import file_digest,read_json,write_json
from cvsubstrate.provenance.bundle import verify_bundle
from cvsubstrate.provenance.artifact_set import verify_directory
from cvsubstrate.errors import CVRSError


def test_dota_reference_boundary_never_silently_uses_diagnostic(tmp_path):
    generate_research_fixtures(tmp_path/'f');d=tmp_path/'f'
    m=import_dota(d/'dota-images',d/'dota-labels',categories=[Category(id=1,name='small-vehicle')],name='test',version='fixture',role='dev',purpose='software_fixture')
    s=m.samples[0];pred=[OrientedPrediction(sample_id=s.id,polygons=[s.annotations[0].polygon],scores=[.9],category_ids=[1])]
    fake=tmp_path/'reference-fixture.py'
    fake.write_text("# Protocol fixture, NOT the actual DOTA evaluator\ndef voc_eval(detpath,annopath,imagesetfile,classname,ovthresh=.5,use_07_metric=False):\n    assert classname=='small-vehicle'\n    assert use_07_metric is True\n    return [1.], [1.], 1.\n")
    ref=DotaReference(source_revision='fixture-not-upstream',module_path=str(fake),module_sha256=file_digest(fake))
    with pytest.raises(CVRSError):run_reference(m,pred,ref,tmp_path/'ref')
    ref.trust_executable_code=True
    value=run_reference(m,pred,ref,tmp_path/'ref')
    assert value['native_result']['mean_ap']==1.
    assert value['parity_verified'] is False
    assert value['native_result']['polyiou_loaded'] is False
    assert verify_directory(tmp_path/'ref')['status']=='VERIFIED'
    fake.write_text('raise ImportError("polyiou not available fixture")\n');ref.module_sha256=file_digest(fake)
    with pytest.raises(CVRSError):run_reference(m,pred,ref,tmp_path/'blocked')
    assert read_json(tmp_path/'blocked/result.json')['reference_metrics_fabricated'] is False
    assert verify_directory(tmp_path/'blocked')['status']=='VERIFIED'


def test_certification_reference_check_leaves_run_untouched(tmp_path,monkeypatch):
    from test_slice02_heritage import _heritage_fixture
    from cvsubstrate.execution.runner import run_experiment
    spec,manifest,config,checkpoint=_heritage_fixture(tmp_path,monkeypatch)
    run=run_experiment(spec,tmp_path/'runs',timeout=30)
    before=file_digest(run/'artifacts.json')
    reference=LegacyExperimentRef(upstream='open-mmlab/mmdetection',revision='fixture-not-upstream',config='tood_fixture.py',
        config_sha256=file_digest(config),environment_reference='fixture-env',reported_metrics={'AP':42.4},licenses=LicenseInfo())
    write_json(tmp_path/'reference.json',reference)
    cert=certify_run(run,tmp_path/'reference.json',output=tmp_path/'certificate.json')
    assert cert['metric_reproduction']['pass'] is False
    assert file_digest(run/'artifacts.json')==before
    assert verify_bundle(run)['status']=='VERIFIED'
    with pytest.raises(CVRSError):certify_run(run,output=run/'bad.json')


def test_reference_coco_nonfinite_tolerance_rejected_before_dependency(dataset):
    from cvsubstrate.evaluation.reference_coco import parity_report
    from cvsubstrate.contracts.models import EvaluationProtocol
    m,_=dataset
    with pytest.raises(ValueError):parity_report(m,'dev',[],EvaluationProtocol(),float('nan'))
