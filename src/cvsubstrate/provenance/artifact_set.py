"""Integrity manifests for derived reports/imports, without mutating source runs."""
from __future__ import annotations
from pathlib import Path
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import digest, file_digest, read_json, safe_join, write_json

NAME = 'integrity.json'


def assert_not_inside_sealed(path: Path) -> None:
    """Protect source evidence at high-level derivation APIs, not as a filesystem ACL."""
    target=Path(path).resolve()
    for parent in [target]+list(target.parents):
        if (parent/'artifacts.json').is_file() or (parent/NAME).is_file():
            raise CVRSError('SEALED_PARENT','derived output must be outside existing sealed evidence')


def seal_directory(root: Path) -> dict:
    root = Path(root).resolve()
    if (root / NAME).exists():
        raise CVRSError('SEALED_ARTIFACT_SET', 'refusing to replace an integrity manifest')
    entries = []
    for p in sorted(root.rglob('*')):
        if p.is_symlink():
            raise CVRSError('ARTIFACT_SYMLINK', 'artifact sets cannot contain symlinks')
        if p.is_file():
            entries.append({'path': p.relative_to(root).as_posix(), 'sha256': file_digest(p), 'bytes': p.stat().st_size})
    payload = {'schema_version': '1.0', 'algorithm': 'sha256', 'files': entries,
               'root_digest': digest(entries), 'limits': 'Unsigned integrity only; not authenticity or scientific certification.'}
    write_json(root / NAME, payload)
    return payload


def verify_directory(root: Path) -> dict:
    root = Path(root).resolve()
    errors=[]
    try:
        value = read_json(root/NAME)
        entries=value['files']
        if value.get('schema_version')!='1.0' or value.get('algorithm')!='sha256':
            raise ValueError('unsupported manifest version/algorithm')
        if digest(entries)!=value['root_digest']:
            errors.append('manifest root digest mismatch')
        paths=[]
        for e in entries:
            rel=e['path']; paths.append(rel)
            if rel==NAME:
                raise ValueError('self-referential manifest')
            p=safe_join(root,rel)
            if (root/rel).is_symlink() or not p.is_file() or p.stat().st_size!=e['bytes'] or file_digest(p)!=e['sha256']:
                errors.append('changed/missing/symlink artifact: '+rel)
        if len(paths)!=len(set(paths)):
            errors.append('duplicate manifest paths')
        actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=root/NAME}
        if actual!=set(paths):
            errors.append('unlisted/missing artifact paths')
        if any(p.is_symlink() for p in root.rglob('*')):
            errors.append('symlink in artifact tree')
    except (OSError,ValueError,KeyError,TypeError,CVRSError) as exc:
        errors.append(str(exc)); entries=[]
    return {'status': 'VERIFIED' if not errors else 'FAILED','errors': errors,
            'files_checked':len(entries),'limits':'Unsigned integrity, not origin authentication.'}
