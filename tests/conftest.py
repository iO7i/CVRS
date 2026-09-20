from pathlib import Path
import sys
import pytest
from cvsubstrate.data.fixtures import generate
from cvsubstrate.data.manifest import load_manifest
from cvsubstrate.contracts.models import ExperimentSpec
from cvsubstrate.provenance.io import read_json


@pytest.fixture
def symlink_or_skip():
    """Create a test symlink, or skip when Windows policy forbids the fixture."""
    def create(link, target, **kwargs):
        try:
            link.symlink_to(target, **kwargs)
        except OSError as exc:
            if sys.platform == 'win32' and getattr(exc, 'winerror', None) == 1314:
                pytest.skip('WINDOWS_SYMLINK_PRIVILEGE: symlink creation is not permitted')
            raise
    return create

@pytest.fixture
def dataset(tmp_path):
    root = tmp_path / 'fixtures'
    generate(root)
    return (load_manifest(root / 'dataset.json'), root)

@pytest.fixture
def real_spec(dataset):
    _, root = dataset
    return ExperimentSpec.model_validate(read_json(root / 'real.json'))
