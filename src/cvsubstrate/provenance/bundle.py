"""Run lifecycle, sanitized environment capture, and artifact verification.

Unsigned hashes detect accidental changes relative to the manifest; anyone able
to rewrite both artifacts and manifest can forge a new bundle. This is NOT a
signature, remote attestation, sandbox, or guarantee that data are still available.
"""
from __future__ import annotations
from datetime import datetime, timezone
import importlib.metadata
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import uuid
from cvsubstrate import __version__
from cvsubstrate.contracts.models import RunManifest, ArtifactManifest
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import canonical_bytes, digest, file_digest, read_json, safe_join, write_json, atomic_bytes

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def redact(text: str) -> str:
    text = re.sub('(?i)(token|password|secret|api[_-]?key)([=:\\s]+)([^\\s,;]+)', '\\1\\2[REDACTED]', text)
    text = re.sub('https?://[^\\s/@:]+:[^\\s/@]+@', 'https://[REDACTED]@', text)
    return text

def environment_snapshot() -> dict:
    versions = {}
    for package in ['cv-research-substrate', 'pydantic', 'pydantic-core', 'numpy', 'Pillow', 'torch', 'torchvision', 'pycocotools']:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return {'python': platform.python_version(), 'implementation': platform.python_implementation(), 'platform': platform.platform(), 'machine': platform.machine(), 'processor': platform.processor() or 'unknown', 'logical_cpus': os.cpu_count(), 'packages': versions, 'cvsubstrate_version': __version__, 'interpreter_name': Path(sys.executable).name, 'network_downloads_performed_by_runtime': False, 'installed_distribution_versions': dict(sorted(((d.metadata['Name'], d.version) for d in importlib.metadata.distributions() if d.metadata.get('Name'))))}


def _package_payload_snapshot(package: Path) -> dict:
    """Fingerprint selected package bytes, separately from Python-only history.

    Includes Python/type files and every regular file below ``resources/``.
    Never follows symlinks or traverses caller datasets, caches or dependencies.
    Unreadable paths and links make the observation partial, not a false claim
    of closure. Like the legacy scan, this is not an atomic filesystem snapshot.
    """
    excluded_dirs = {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.git', '.hg', '.svn'}
    excluded_suffixes = {'.pyc', '.pyo'}
    files = {}
    unbound = []

    def relative(path):
        return Path(path).relative_to(package).as_posix()

    def onerror(exc):
        path = relative(exc.filename) if exc.filename else '.'
        unbound.append({'path': path, 'reason': 'UNREADABLE_DIRECTORY'})

    for current, directories, names in os.walk(package, topdown=True, followlinks=False, onerror=onerror):
        current = Path(current)
        kept = []
        for name in sorted(directories):
            path = current / name
            if name in excluded_dirs:
                continue
            if path.is_symlink():
                unbound.append({'path': relative(path), 'reason': 'SYMLINK_DIRECTORY_NOT_FOLLOWED'})
            else:
                kept.append(name)
        directories[:] = kept
        for name in sorted(names):
            path = current / name
            rel = path.relative_to(package)
            if path.suffix in excluded_suffixes:
                continue
            if not (path.suffix in {'.py', '.pyi'} or rel.as_posix() == 'py.typed' or rel.parts[0] == 'resources'):
                continue
            if path.is_symlink():
                unbound.append({'path': rel.as_posix(), 'reason': 'SYMLINK_FILE_NOT_FOLLOWED'})
                continue
            try:
                if not path.is_file():
                    unbound.append({'path': rel.as_posix(), 'reason': 'NOT_A_REGULAR_FILE'})
                    continue
                files[rel.as_posix()] = file_digest(path)
            except OSError:
                unbound.append({'path': rel.as_posix(), 'reason': 'UNREADABLE_FILE'})
    payload = {
        'format': 'cvrs-package-payload',
        'schema_version': '1.0',
        'algorithm': 'sha256',
        'selection': {
            'include': ['**/*.py', '**/*.pyi', 'py.typed', 'resources/**'],
            'exclude_directory_names': sorted(excluded_dirs),
            'exclude_file_suffixes': sorted(excluded_suffixes),
            'symlinks': 'not-followed; selected file links and directory links reported as unbound',
            'paths': 'case-preserving package-relative POSIX paths',
        },
        'files': dict(sorted(files.items())),
        'unbound': sorted(unbound, key=lambda item: (item['path'], item['reason'])),
        'status': 'PARTIAL' if unbound else 'COMPLETE',
        'limits': 'Selected installed/source package bytes only; excludes dependencies, external assets, '
                  'repository-level schemas/docs and distribution metadata. Not a wheel hash, '
                  'executed-code trace, atomic snapshot, signature or computation proof.',
    }
    return {**payload, 'root_digest': digest(payload)}


def source_snapshot() -> dict:
    package = Path(__file__).resolve().parents[1]
    files = {p.relative_to(package).as_posix(): file_digest(p) for p in sorted(package.rglob('*.py'))}
    # Historical fields retain their exact Python-only algorithm and meaning.
    result = {'package_files': files, 'package_tree_digest': digest(files), 'git': {'status': 'NOT_A_GIT_CHECKOUT'},
              'package_payload': _package_payload_snapshot(package)}
    try:
        proc = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=package, capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            root = Path(proc.stdout.strip())
            head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True, timeout=5)
            status = subprocess.run(['git', 'status', '--porcelain'], cwd=root, capture_output=True, text=True, timeout=5)
            diff = subprocess.run(['git', 'diff', '--binary', 'HEAD'], cwd=root, capture_output=True, timeout=5)
            result['git'] = {'status': 'DIRTY' if status.stdout else 'CLEAN', 'commit': head.stdout.strip() if head.returncode == 0 else None, 'tracked_patch_sha256': __import__('hashlib').sha256(diff.stdout).hexdigest(), 'note': 'Package tree digest covers shipped Python source, including untracked files. Git patch excludes untracked nonpackage files.'}
    except (OSError, subprocess.SubprocessError):
        pass
    return result

class RunBundle:

    def __init__(self, root: Path, experiment_digest: str, dataset_digest: str):
        from cvsubstrate.provenance.artifact_set import assert_not_inside_sealed
        assert_not_inside_sealed(root)
        self.path = Path(root) / f'{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:12]}'
        self.path.mkdir(parents=True, exist_ok=False)
        self.manifest = RunManifest(run_id=self.path.name, experiment_digest=experiment_digest, dataset_digest=dataset_digest, state='RUNNING', created_at=now())
        write_json(self.path / 'run.json', self.manifest)
        self.event('RUNNING')

    def event(self, kind: str, details: dict | None=None):
        if (self.path / 'artifacts.json').exists():
            raise CVRSError('SEALED_BUNDLE', 'sealed run cannot be changed')
        payload = {'at': now(), 'event': kind, 'details': details or {}}
        with (self.path / 'events.jsonl').open('ab') as f:
            f.write(canonical_bytes(payload) + b'\n')
            f.flush()
            os.fsync(f.fileno())

    def finish(self, state: str, failure: dict | None=None):
        if self.manifest.state != 'RUNNING':
            raise CVRSError('RUN_TRANSITION', 'only a RUNNING bundle may be finalized')
        self.manifest.state = state
        self.manifest.finished_at = now()
        self.manifest.failure = failure
        self.event(state, failure)
        write_json(self.path / 'run.json', self.manifest)
        self.seal()

    def seal(self):
        entries = []
        for p in sorted(self.path.rglob('*')):
            if p.is_symlink():
                raise CVRSError('ARTIFACT_SYMLINK', 'symlink artifacts are not permitted')
            if p.is_file() and p != self.path / 'artifacts.json':
                entries.append({'path': p.relative_to(self.path).as_posix(), 'sha256': file_digest(p), 'bytes': p.stat().st_size})
        write_json(self.path / 'artifacts.json', {'schema_version': '1.0', 'algorithm': 'sha256', 'files': entries, 'root_digest': digest(entries), 'limits': 'Unsigned manifest; no authenticity or continued external-data-availability guarantee.'})

def verify_bundle(path: Path, dataset: Path | None=None) -> dict:
    path = Path(path)
    errors = []
    if not (path / 'artifacts.json').is_file():
        return {'status': 'INCOMPLETE', 'errors': ['missing final artifact manifest'], 'run_state': 'RUNNING_OR_INTERRUPTED'}
    try:
        a = read_json(path / 'artifacts.json')
        ArtifactManifest.model_validate(a)
    except (ValueError, OSError, TypeError) as exc:
        return {'status': 'FAILED', 'errors': [f'invalid artifact manifest: {exc}'], 'run_state': 'UNKNOWN'}
    entries = a['files']
    if digest(entries) != a.get('root_digest'):
        errors.append('artifact manifest root digest mismatch')
    names = [e['path'] for e in entries]
    if len(set(names)) != len(names):
        errors.append('duplicate artifact manifest entries')
    for e in entries:
        try:
            p = safe_join(path, e['path'])
        except (ValueError, CVRSError):
            errors.append('unsafe artifact path')
            continue
        original = path / e['path']
        if original.is_symlink():
            errors.append(f"symlink artifact: {e['path']}")
            continue
        if not p.is_file():
            errors.append(f"missing artifact: {e['path']}")
            continue
        if p.stat().st_size != e['bytes'] or file_digest(p) != e['sha256']:
            errors.append(f"changed artifact: {e['path']}")
    actual = {p.relative_to(path).as_posix() for p in path.rglob('*') if p.is_file() and p != path / 'artifacts.json'}
    if actual != set(names):
        errors.append('unlisted or missing artifact paths')
    run = None
    try:
        run = RunManifest.model_validate(read_json(path / 'run.json'))
        if run.state == 'RUNNING':
            errors.append('sealed run still marked RUNNING')
        if (path / 'experiment.json').exists():
            from cvsubstrate.contracts.models import ExperimentSpec
            from cvsubstrate.provenance.io import experiment_identity
            exp = ExperimentSpec.model_validate(read_json(path / 'experiment.json'))
            if experiment_identity(exp) != run.experiment_digest:
                errors.append('experiment identity mismatch')
        if (path / 'dataset_manifest.json').exists():
            from cvsubstrate.contracts.models import DatasetManifest
            m = DatasetManifest.model_validate(read_json(path / 'dataset_manifest.json'))
            if digest(m) != run.dataset_digest:
                errors.append('embedded dataset identity mismatch')
        if dataset is not None:
            from cvsubstrate.data.manifest import load_manifest
            external = load_manifest(dataset)
            if digest(external) != run.dataset_digest:
                errors.append('external dataset identity mismatch')
    except (ValueError, KeyError, OSError, CVRSError) as exc:
        errors.append(f'invalid evidence: {exc}')
    return {'status': 'VERIFIED' if not errors else 'FAILED', 'errors': errors, 'run_state': run.state if run else 'UNKNOWN', 'artifacts_checked': len(entries), 'external_dataset_checked': dataset is not None, 'limits': 'Integrity only. No signatures, independent reproduction, or scientific validity implied.'}
