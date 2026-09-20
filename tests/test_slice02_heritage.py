import json
import os
from pathlib import Path
import sys

import pytest

from cvsubstrate.contracts.models import (
    AdapterSpec,
    CheckpointRef,
    DatasetManifest,
    DetectionPrediction,
    EvaluationProtocol,
    ExperimentSpec,
    LegacyExperimentRef,
    LicenseInfo,
    WorkerRequest,
)
from cvsubstrate.data.fixtures import generate
from cvsubstrate.evaluation.cross_framework import compare_runs
from cvsubstrate.execution.heritage import adapter_fragment, certify_run
from cvsubstrate.execution.process import invoke, worker_command
from cvsubstrate.execution.runner import run_experiment
from cvsubstrate.provenance.bundle import RunBundle, verify_bundle
from cvsubstrate.provenance.io import digest, file_digest, read_json, write_json


def _fake_mm_packages(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    (root / 'mmdet').mkdir()
    (root / 'mmengine').mkdir()
    # 0.4 profiles explicitly require MMCV; this remains a protocol fixture, not real MM evidence.
    (root / 'mmcv').mkdir()
    (root / 'mmcv' / '__init__.py').write_text("__version__='2.fake'\n")
    (root / 'mmdet' / '__init__.py').write_text("__version__='3.fake'\n")
    (root / 'mmengine' / '__init__.py').write_text("__version__='0.fake'\n")
    (root / 'mmengine' / 'config.py').write_text('''
from pathlib import Path
class _Resolved:
    def __init__(self, path):
        self.pretty_text = Path(path).read_text()
class Config:
    @staticmethod
    def fromfile(path):
        return _Resolved(path)
''')
    (root / 'mmdet' / 'apis.py').write_text('''
class T:
    def __init__(self, value): self.value=value
    def detach(self): return self
    def cpu(self): return self
    def tolist(self): return self.value
class P:
    bboxes=T([[1.0,1.0,7.0,7.0]])
    scores=T([0.875])
    labels=T([0])
class R:
    pred_instances=P()
def init_detector(config, checkpoint, device='cpu'):
    return {'config':config, 'checkpoint':checkpoint, 'device':device}
def inference_detector(model, image):
    return R()
''')


def _heritage_fixture(tmp_path: Path, monkeypatch):
    fake = tmp_path / 'fakepkgs'
    _fake_mm_packages(fake)
    previous = os.environ.get('PYTHONPATH')
    monkeypatch.setenv('PYTHONPATH', str(fake) + (os.pathsep + previous if previous else ''))
    fixtures = tmp_path / 'fixtures'
    generated = generate(fixtures)
    manifest = Path(generated['dataset'])
    config = tmp_path / 'tood_fixture.py'
    config.write_text("model=dict(type='TOOD')\n")
    checkpoint = tmp_path / 'fixture.pth'
    checkpoint.write_bytes(b'fixture-only-not-a-real-model')
    m = DatasetManifest.model_validate(read_json(manifest))
    spec = ExperimentSpec(
        name='heritage-fixture',
        dataset=str(manifest),
        dataset_sha256=digest(m),
        eval_split='dev',
        adapter=AdapterSpec(name='mmdetection', config={
            'config_path': str(config),
            'config_sha256': file_digest(config),
            'trust_executable_config': True,
            'category_map': {'0': m.categories[0].id},
            'upstream': 'open-mmlab/mmdetection',
            'revision': 'fixture-not-certified',
            'device': 'cpu',
        }),
        checkpoint=CheckpointRef(path=str(checkpoint), sha256=file_digest(checkpoint), trust='trusted_legacy_pickle'),
        evaluation=EvaluationProtocol(evaluator='diagnostic_detection', evaluator_version='1'),
        notes='Protocol conformance fixture only; not MMDetection certification.',
    )
    spec_path = tmp_path / 'heritage.json'
    write_json(spec_path, spec)
    return spec_path, manifest, config, checkpoint


def test_standalone_worker_has_no_controller_imports_and_runs_without_core_on_pythonpath(tmp_path):
    command = worker_command('mmdetection', sys.executable)
    source = Path(command[1]).read_text('utf-8')
    assert '\nimport cvsubstrate' not in source and '\nfrom cvsubstrate' not in source
    assert '\nimport pydantic' not in source and '\nfrom pydantic' not in source
    # -S removes site packages; capabilities must still produce a structured answer.
    req = tmp_path / 'req.json'; res = tmp_path / 'res.json'
    write_json(req, WorkerRequest(operation='capabilities'))
    import subprocess
    subprocess.run([sys.executable, '-S', command[1], '--request', str(req), '--response', str(res)], check=True)
    payload = json.loads(res.read_text())
    assert payload['status'] == 'SUCCEEDED'
    assert payload['result']['standalone_bridge'] is True
    assert payload['result']['imports_controller_package'] is False


def test_fake_mm_is_protocol_conformance_not_certification(tmp_path, monkeypatch):
    spec_path, manifest, config, checkpoint = _heritage_fixture(tmp_path, monkeypatch)
    run = run_experiment(spec_path, tmp_path / 'runs', worker_python=sys.executable, timeout=30)
    assert verify_bundle(run, manifest)['status'] == 'VERIFIED'
    worker = read_json(run / 'worker_result.json')
    assert worker['heritage_level'] == 'H3_OUTPUT_PARITY_VERIFIED'
    audit = read_json(run / 'heritage' / 'conversion_audit.json')
    assert audit['exact_representation_fidelity'] is True
    assert audit['native_detections'] == audit['canonical_detections']
    assert (run / 'heritage' / 'upstream_predictions.jsonl').is_file()
    cert = certify_run(run)
    assert cert['compatibility_level'] == 'H3_OUTPUT_PARITY_VERIFIED'
    assert cert['independently_reproduced'] is False
    assert any('H4 requires' in x for x in cert['blockers'])


def test_legacy_reference_adapter_fragment_requires_explicit_category_map(tmp_path):
    config = tmp_path / 'config.py'; config.write_text("model=dict(type='TOOD')\n")
    ref = LegacyExperimentRef(
        upstream='open-mmlab/mmdetection', revision='abc123', config='config.py',
        config_sha256=file_digest(config), environment_reference='env.json', trust_executable_config=True,
        licenses=LicenseInfo(code='Apache-2.0', weights='unknown', data='unknown', annotations='unknown'),
    )
    path = tmp_path / 'ref.json'; write_json(path, ref)
    fragment = adapter_fragment(path)
    assert fragment['adapter']['name'] == 'mmdetection'
    assert fragment['adapter']['config']['category_map'] == {}
    assert fragment['checkpoint'] is None


def _sealed_comparison_run(root: Path, name: str, adapter: str, metrics: dict, worker_env: dict):
    exp = ExperimentSpec(
        name=f'compare-{name}', dataset='dataset.json', dataset_sha256='c' * 64,
        adapter=AdapterSpec(name=adapter),
        evaluation=EvaluationProtocol(evaluator='diagnostic_detection', evaluator_version='1'),
    )
    b = RunBundle(root, digest({k:v for k,v in exp.model_dump(mode='json').items() if k not in {'dataset','notes'}}), 'c' * 64)
    # Use the production identity function to avoid a hand-maintained facsimile.
    from cvsubstrate.provenance.io import experiment_identity
    b.manifest.experiment_digest = experiment_identity(exp)
    write_json(b.path / 'experiment.json', exp)
    write_json(b.path / 'metrics.json', metrics)
    write_json(b.path / 'adapter.json', {'environment': worker_env})
    write_json(b.path / 'worker_result.json', {'status': 'ok'})
    write_json(b.path / 'environment.json', {'controller': 'fixture'})
    b.finish('SUCCEEDED')
    return b.path


def test_cross_framework_report_separates_measurement_from_training(tmp_path):
    key = {'dataset_digest': 'd', 'split': 'dev', 'sample_ids': ['x'], 'taxonomy': [{'id': 1}], 'evaluation_protocol': {'evaluator': 'fixture'}}
    metrics = {'comparison_key': key, 'comparison_digest': digest(key)}
    left = _sealed_comparison_run(tmp_path, 'a', 'mmdetection', metrics, {'python': '3.8', 'mmdet': '3.3.0'})
    right = _sealed_comparison_run(tmp_path, 'b', 'native_torch', metrics, {'python': '3.13', 'torchvision': '0.25.0'})
    report = compare_runs(left, right)
    assert report['measurement']['status'] == 'COMPARABLE_UNDER_DECLARED_PROTOCOL'
    assert report['distinct_implementations'] is True
    assert report['distinct_recorded_worker_environments'] is True
    assert report['training_fairness'] == 'NOT_ASSESSED_PRETRAINED_OR_INFERENCE_ONLY'


@pytest.mark.coco
def test_reference_parity_audit_when_pycocotools_available(dataset):
    pytest.importorskip('pycocotools', reason='pycocotools unavailable in build environment')
    from cvsubstrate.evaluation.reference_coco import parity_report
    m, root = dataset
    ids = m.splits['dev'].sample_ids
    rows = [DetectionPrediction(sample_id=sid, width=next(s.width for s in m.samples if s.id == sid), height=next(s.height for s in m.samples if s.id == sid), boxes=[], scores=[], category_ids=[]) for sid in ids]
    protocol = EvaluationProtocol()
    report = parity_report(m, 'dev', rows, protocol, 1e-6)
    assert report['status'] == 'PASS'
