import pytest
from cvsubstrate.contracts.models import TrainingSpec
from cvsubstrate.protocols.planner import plan, source_seed, stream
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import digest

@pytest.mark.parametrize('arm,real,synthetic,updates', [('R', 2, 0, 2), ('S', 0, 2, 2), ('R+S', 2, 2, 2), ('S->R', 2, 2, 4)])
def test_four_arms_exact_plan_counts(dataset, real_spec, arm, real, synthetic, updates):
    m, _ = dataset
    real_spec.training = TrainingSpec(arm=arm, updates=2, pretrain_updates=2)
    p = plan(real_spec, m)
    assert p['planned_counts']['real_exposures'] == real
    assert p['planned_counts']['synthetic_exposures'] == synthetic
    assert p['planned_counts']['optimizer_updates'] == updates
    assert p['measured_counts'] is None

def test_supplement_preserves_real_sample_and_rng_stream(dataset, real_spec):
    m, _ = dataset
    real_spec.training.updates = 15
    a = plan(real_spec, m)
    real_spec.training.arm = 'R+S'
    b = plan(real_spec, m)
    assert [s['real'] for s in a['stages'][0]['steps']] == [s['real'] for s in b['stages'][0]['steps']]
    assert [s['real_forward_seed'] for s in a['stages'][0]['steps']] == [s['real_forward_seed'] for s in b['stages'][0]['steps']]

def test_pretrain_resets_optimizer_not_weights(dataset, real_spec):
    m, _ = dataset
    real_spec.training.arm = 'S->R'
    p = plan(real_spec, m)
    assert p['stages'][1]['optimizer_reset'] is True
    assert p['stages'][1]['checkpoint_transition'] == 'weights_only_reset_optimizer'

def test_replay_accounted(dataset, real_spec):
    m, _ = dataset
    real_spec.training.updates = 7
    p = plan(real_spec, m)
    assert p['planned_counts']['real_replayed_exposures'] == 3

def test_no_unknown_sources_as_real(dataset, real_spec):
    m, _ = dataset
    for s in m.samples[:4]:
        s.source_kind = 'unknown'
    real_spec.dataset_sha256 = digest(m)
    with pytest.raises(CVRSError, match='empty source'):
        plan(real_spec, m)

def test_distinct_source_seeds():
    assert source_seed(5, 'real') != source_seed(5, 'synthetic')

def test_sampler_replay_deterministic():
    assert stream(['a', 'b', 'c'], 50, 5) == stream(['a', 'b', 'c'], 50, 5)

def test_plan_is_repeatable(dataset, real_spec):
    m, _ = dataset
    assert plan(real_spec, m) == plan(real_spec, m)
