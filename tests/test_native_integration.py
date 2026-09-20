from pathlib import Path
import pytest
from cvsubstrate.contracts.models import ExperimentSpec
from cvsubstrate.execution.runner import run_experiment
from cvsubstrate.provenance.bundle import verify_bundle
from cvsubstrate.provenance.io import read_json, read_jsonl, write_json
pytestmark = pytest.mark.native

@pytest.mark.parametrize('arm_file,real,synthetic,updates', [('real.json', 2, 0, 2), ('synthetic.json', 0, 2, 2), ('supplement.json', 2, 2, 2), ('pretrain.json', 2, 2, 4)])
def test_real_detector_four_micro_campaign_arms(dataset, tmp_path, arm_file, real, synthetic, updates):
    pytest.importorskip('torch')
    pytest.importorskip('torchvision')
    m, root = dataset
    run = run_experiment(root / arm_file, tmp_path / 'runs', timeout=90)
    result = read_json(run / 'worker_result.json')
    assert result['parameters_changed'] is True
    assert result['checkpoint_roundtrip_predictions_exact'] is True
    assert result['measured_counts']['real_exposures'] == real
    assert result['measured_counts']['synthetic_exposures'] == synthetic
    assert result['measured_counts']['optimizer_updates'] == updates
    assert result['prediction_images'] == 4
    assert verify_bundle(run, root / 'dataset.json')['status'] == 'VERIFIED'
    assert len(read_jsonl(run / 'training_trace.jsonl')) == updates
    assert read_json(run / 'metrics.json')['kind'] == 'DIAGNOSTIC_NOT_COCO'

def test_repeated_real_training_is_exact_in_same_environment(dataset, tmp_path):
    pytest.importorskip('torch')
    pytest.importorskip('torchvision')
    m, root = dataset
    a = run_experiment(root / 'real.json', tmp_path / 'a', timeout=90)
    b = run_experiment(root / 'real.json', tmp_path / 'b', timeout=90)
    assert read_jsonl(a / 'predictions.jsonl') == read_jsonl(b / 'predictions.jsonl')
    assert read_json(a / 'worker_result.json')['final_parameter_digest'] == read_json(b / 'worker_result.json')['final_parameter_digest']
    assert read_json(a / 'run.json')['run_id'] != read_json(b / 'run.json')['run_id']
    assert read_json(a / 'run.json')['experiment_digest'] == read_json(b / 'run.json')['experiment_digest']

def test_checkpoint_continuation_exact(dataset, tmp_path):
    pytest.importorskip('torch')
    pytest.importorskip('torchvision')
    from cvsubstrate.workers.native_torch import resume_selftest
    m, root = dataset
    result = resume_selftest(m, root, tmp_path / 'resume')
    assert result['parameter_state_exact'] and result['predictions_exact']

def test_reinitialize_prediction_from_owned_checkpoint(dataset, tmp_path):
    pytest.importorskip('torch')
    pytest.importorskip('torchvision')
    from cvsubstrate.contracts.models import CheckpointRef
    from cvsubstrate.provenance.io import file_digest
    m, root = dataset
    a = run_experiment(root / 'real.json', tmp_path / 'a', timeout=90)
    spec = ExperimentSpec.model_validate(read_json(root / 'real.json'))
    spec.training = None
    ck = a / 'worker' / 'checkpoint.pt'
    spec.checkpoint = CheckpointRef(path=str(ck), sha256=file_digest(ck))
    write_json(root / 'predict.json', spec)
    b = run_experiment(root / 'predict.json', tmp_path / 'b', timeout=90)
    assert read_jsonl(a / 'predictions.jsonl') == read_jsonl(b / 'predictions.jsonl')
    assert read_json(b / 'worker_result.json')['parameters_changed'] is False
