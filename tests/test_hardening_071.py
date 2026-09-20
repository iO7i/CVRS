"""Narrow regressions for explicit exports and additive package identity.

Fixtures are software metadata only; these tests do not certify native models.
"""
from pathlib import Path
import ast
import json
import os
import shutil
from types import SimpleNamespace

import pytest

from cvsubstrate import v1
from cvsubstrate.product.compatibility import freeze_api, compare_api
from cvsubstrate.provenance import bundle
from cvsubstrate.provenance.io import digest, file_digest, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]


def facade_fixture(tmp_path, source):
    root = tmp_path / 'foreign'
    facade = root / 'src/cvsubstrate/v1.py'
    facade.parent.mkdir(parents=True)
    facade.write_text(source, encoding='utf-8')
    write_json(root / 'schemas/Fixture.schema.json', {'title': 'Fixture', 'type': 'object'})
    return root


def snapshot_fixture(tmp_path, declaration):
    root = facade_fixture(tmp_path, 'from pathlib import Path\nfrom collections import Counter\n' + declaration)
    path = tmp_path / 'snapshot.json'
    freeze_api(root, path)
    return read_json(path)


def test_frozen_59_exports_preserve_previous_surface(tmp_path):
    baseline = read_json(ROOT / 'src/cvsubstrate/resources/product/api-surface-v1.json')
    assert len(v1.__all__) == len(set(v1.__all__)) == 59
    assert set(v1.__all__) == set(baseline['symbols'])
    assert all(hasattr(v1, name) for name in v1.__all__)
    tree = ast.parse((ROOT / 'src/cvsubstrate/v1.py').read_text())
    declaration = next(n for n in tree.body if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == '__all__' for t in n.targets))
    assert ast.literal_eval(declaration.value) == v1.__all__
    freeze_api(ROOT, tmp_path / 'now.json')
    compared = compare_api(baseline, read_json(tmp_path / 'now.json'))
    assert compared['status'] == 'STRUCTURALLY_COMPATIBLE'
    assert not compared['additions'] and not compared['review'] and not compared['breaking']


@pytest.mark.parametrize('declaration', ["__all__ = ['Counter']\n", "__all__ = ('Counter',)\n", "__all__: list[str] = ['Counter']\n"])
def test_snapshot_honors_literal_exports_not_imported_helpers(tmp_path, declaration):
    value = snapshot_fixture(tmp_path, declaration)
    assert list(value['symbols']) == ['Counter']
    assert value['symbols']['Counter']['origin'] == 'collections:Counter'


def test_explicit_empty_exports_do_not_fall_back(tmp_path):
    assert snapshot_fixture(tmp_path, '__all__ = []\n')['symbols'] == {}


@pytest.mark.parametrize('declaration', ['', "__all__ = [name for name in globals() if not name.startswith('_')]\n"])
def test_historical_facade_without_literal_boundary_keeps_import_rule(tmp_path, declaration):
    assert set(snapshot_fixture(tmp_path, declaration)['symbols']) == {'Path', 'Counter'}


def test_explicit_underscored_alias_is_respected(tmp_path):
    root = facade_fixture(tmp_path, "from collections import Counter as _Counter\n__all__ = ['_Counter']\n")
    freeze_api(root, tmp_path / 'snapshot.json')
    assert read_json(tmp_path / 'snapshot.json')['symbols']['_Counter']['origin'] == 'collections:Counter'


@pytest.mark.parametrize('declaration', [
    "__all__ = make_exports()\n",
    "__all__ = ['Counter', 'Counter']\n",
    "__all__ = [3]\n",
    "__all__ = 'Counter'\n",
    "__all__ = ['not an identifier']\n",
    "__all__ = ['Missing']\n",
    "__all__ = ['Counter']\n__all__ += ['Path']\n",
    "__all__ = ['Counter']\n__all__.append('Path')\n",
    "__all__ = ['Counter']\n__all__ = ['Path']\n",
    "if True:\n    __all__ = ['Counter']\n",
])
def test_unresolved_or_mutated_boundary_fails_without_partial_snapshot(tmp_path, declaration):
    with pytest.raises(ValueError):
        snapshot_fixture(tmp_path, declaration)
    assert not (tmp_path / 'snapshot.json').exists()


def test_snapshot_never_executes_inspected_source(tmp_path):
    marker = tmp_path / 'executed'
    root = facade_fixture(tmp_path, 'from collections import Counter\n__all__ = [\'Counter\']\n'
                          + f'open({str(marker)!r}, "w").write("BAD")\n')
    freeze_api(root, tmp_path / 'snapshot.json')
    assert not marker.exists()


def test_snapshot_destination_remains_immutable(tmp_path):
    root = facade_fixture(tmp_path, "from collections import Counter\n__all__ = ['Counter']\n")
    out = tmp_path / 'snapshot.json'
    freeze_api(root, out)
    previous = out.read_bytes()
    with pytest.raises(ValueError, match='immutable'):
        freeze_api(root, out)
    assert out.read_bytes() == previous


@pytest.fixture
def package_fixture(tmp_path, monkeypatch):
    package = tmp_path / 'package'
    (package / 'provenance').mkdir(parents=True)
    (package / 'provenance/bundle.py').write_text('# fixture source\n')
    (package / 'worker_shims').mkdir()
    (package / 'worker_shims/example.py').write_text('value = 1\n')
    (package / 'resources').mkdir()
    (package / 'resources/policy.json').write_text('{"policy":1}\n')
    (package / 'py.typed').touch()
    (package / 'typing.pyi').write_text('value: int\n')
    monkeypatch.setattr(bundle, '__file__', str(package / 'provenance/bundle.py'))
    monkeypatch.setattr(bundle.subprocess, 'run', lambda *a, **kw: SimpleNamespace(returncode=1, stdout=''))
    return package


def test_new_payload_preserves_exact_legacy_python_algorithm(package_fixture):
    result = bundle.source_snapshot()
    expected = {p.relative_to(package_fixture).as_posix(): file_digest(p)
                for p in sorted(package_fixture.rglob('*.py'))}
    assert result['package_files'] == expected
    assert result['package_tree_digest'] == digest(expected)
    assert result['git'] == {'status': 'NOT_A_GIT_CHECKOUT'}
    payload = result['package_payload']
    core = {k: v for k, v in payload.items() if k != 'root_digest'}
    assert payload['root_digest'] == digest(core)
    assert payload['status'] == 'COMPLETE' and payload['unbound'] == []
    assert payload['format'] == 'cvrs-package-payload' and payload['schema_version'] == '1.0'
    assert {'worker_shims/example.py', 'resources/policy.json', 'py.typed', 'typing.pyi'} <= payload['files'].keys()


@pytest.mark.parametrize('relative', ['resources/policy.json', 'py.typed', 'typing.pyi'])
def test_non_python_change_alters_only_additive_identity(package_fixture, relative):
    before = bundle.source_snapshot()
    path = package_fixture / relative
    path.write_bytes(path.read_bytes() + b'changed')
    after = bundle.source_snapshot()
    assert before['package_files'] == after['package_files']
    assert before['package_tree_digest'] == after['package_tree_digest']
    assert before['package_payload']['root_digest'] != after['package_payload']['root_digest']


def test_python_worker_change_updates_both_identities(package_fixture):
    before = bundle.source_snapshot()
    (package_fixture / 'worker_shims/example.py').write_text('value = 2\n')
    after = bundle.source_snapshot()
    assert before['package_tree_digest'] != after['package_tree_digest']
    assert before['package_payload']['root_digest'] != after['package_payload']['root_digest']


def test_resource_add_remove_and_rename_are_bound(package_fixture):
    initial = bundle.source_snapshot()['package_payload']['root_digest']
    p = package_fixture / 'resources/template.txt'
    p.write_text('a newly packaged resource')
    added = bundle.source_snapshot()['package_payload']['root_digest']
    renamed = p.rename(p.with_name('renamed.txt'))
    assert initial != added != bundle.source_snapshot()['package_payload']['root_digest']
    renamed.unlink()
    assert bundle.source_snapshot()['package_payload']['root_digest'] == initial


def test_payload_ignores_declared_caches_and_external_assets(package_fixture):
    before = bundle.source_snapshot()['package_payload']
    for relative in ['__pycache__/x.pyc', 'resources/__pycache__/x.pyc',
                     'resources/cache.pyc', 'resources/.pytest_cache/cache.json',
                     '.git/HEAD', '.mypy_cache/typing.json']:
        p = package_fixture / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('ephemeral')
    (package_fixture.parent / 'dataset-secret.txt').write_text('external asset')
    assert bundle.source_snapshot()['package_payload'] == before


def test_payload_is_location_and_mtime_independent(package_fixture, tmp_path):
    before = bundle.source_snapshot()['package_payload']
    target = tmp_path / 'relocated'
    shutil.copytree(package_fixture, target)
    for path in target.rglob('*'):
        os.utime(path, (1, 1))
    assert bundle._package_payload_snapshot(target) == before
    assert str(package_fixture) not in json.dumps(before)


@pytest.mark.parametrize('is_directory', [False, True])
def test_symlinks_are_reported_partial_without_following(package_fixture, tmp_path, is_directory):
    outside = tmp_path / 'outside'
    if is_directory:
        outside.mkdir()
        (outside / 'never-read.json').write_text('private')
    else:
        outside.write_text('private')
    link = package_fixture / 'resources/link'
    try:
        link.symlink_to(outside, target_is_directory=is_directory)
    except OSError:
        pytest.skip('symlinks unavailable on this platform')
    payload = bundle.source_snapshot()['package_payload']
    assert payload['status'] == 'PARTIAL'
    assert payload['unbound'][0]['path'] == 'resources/link'
    assert not any('link' in name for name in payload['files'])
    assert 'private' not in json.dumps(payload)


def test_unreadable_selected_resource_is_not_claimed_complete(package_fixture, monkeypatch):
    original = bundle.file_digest
    def denied(path):
        if Path(path).suffix == '.json':
            raise PermissionError('contains sensitive absolute path')
        return original(path)
    monkeypatch.setattr(bundle, 'file_digest', denied)
    payload = bundle.source_snapshot()['package_payload']
    assert payload['status'] == 'PARTIAL'
    assert payload['unbound'] == [{'path': 'resources/policy.json', 'reason': 'UNREADABLE_FILE'}]
    assert 'sensitive' not in json.dumps(payload)


def test_legacy_and_new_source_records_both_seal_and_verify(package_fixture, tmp_path):
    current = bundle.source_snapshot()
    legacy = {k: v for k, v in current.items() if k != 'package_payload'}
    for value in (legacy, current):
        run = bundle.RunBundle(tmp_path / 'runs', 'a' * 64, 'b' * 64)
        write_json(run.path / 'source.json', value)
        run.finish('SUCCEEDED')
        assert bundle.verify_bundle(run.path)['status'] == 'VERIFIED'
        if value is current:
            changed = read_json(run.path / 'source.json')
            changed['package_payload']['files']['resources/policy.json'] = 'c' * 64
            write_json(run.path / 'source.json', changed)
            assert bundle.verify_bundle(run.path)['status'] == 'FAILED'


def test_release_preparation_preserves_nested_historical_manifests(tmp_path):
    """Only current top-level inventories are regenerated, not history copies."""
    from cvsubstrate.release import prepare_release
    source = tmp_path / 'original'
    (source / 'src/cvsubstrate').mkdir(parents=True)
    (source / 'src/cvsubstrate/__init__.py').write_text('__version__ = "0.1.0"\n')
    (source / 'pyproject.toml').write_text('[project]\nname = "fixture"\nversion = "0.1.0"\n')
    inventories = ['RELEASE_MANIFEST.json', 'SBOM.cdx.json', 'LINE_COUNTS.json']
    historical = {}
    for name in inventories:
        write_json(source / name, {'current': name})
        path = source / 'docs/history/previous' / name
        write_json(path, {'historical': name})
        historical[name] = path.read_bytes()
    target = tmp_path / 'prepared'
    prepare_release(source, target, '0.1.1', ['Preserve historical evidence.'])
    for name in inventories:
        assert not (target / name).exists()
        assert (target / 'docs/history/previous' / name).read_bytes() == historical[name]
        assert (source / 'docs/history/previous' / name).read_bytes() == historical[name]
