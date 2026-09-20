"""Explicit interruption recovery; never converts partial execution into success."""
from pathlib import Path
from cvsubstrate.contracts.models import RunManifest
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.bundle import RunBundle, verify_bundle
from cvsubstrate.provenance.io import read_json


def recover_interrupted_run(path: Path, *, reason: str, acknowledge_process_stopped: bool) -> dict:
    path=Path(path).resolve()
    if not acknowledge_process_stopped or not reason.strip():
        raise CVRSError('RECOVERY_APPROVAL', 'explicit reason and confirmation that the worker is stopped are required')
    if (path/'artifacts.json').exists():
        raise CVRSError('SEALED_BUNDLE', 'a sealed run must not be rewritten')
    manifest=RunManifest.model_validate(read_json(path/'run.json'))
    if manifest.state!='RUNNING':
        raise CVRSError('RECOVERY_STATE','only an unsealed RUNNING run can be marked interrupted')
    bundle=object.__new__(RunBundle)
    bundle.path=path; bundle.manifest=manifest
    bundle.finish('INTERRUPTED', {'code':'EXPLICIT_RECOVERY','message':reason})
    return verify_bundle(path)
