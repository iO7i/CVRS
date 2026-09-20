"""Deterministic JSON, content identity, atomic writes, and bounded file loading."""
from __future__ import annotations
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any
from pydantic import BaseModel
from cvsubstrate.errors import CVRSError
MAX_JSON_BYTES = 64 * 1024 * 1024

def canonical_bytes(value: Any) -> bytes:
    """Python canonical JSON v1, NOT a claim of RFC 8785 conformance.

    UTF-8, sorted string keys, compact separators, no nonfinite numbers;
    lists remain ordered. Contract serialization materializes defaults.
    Numeric spelling follows this Python implementation (recorded in runs).
    """
    def normalize(x):
        if isinstance(x, BaseModel):
            return x.model_dump(mode='json')
        if isinstance(x, dict):
            return {k: normalize(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [normalize(v) for v in x]
        return x
    value = normalize(value)

    def check_keys(x):
        if isinstance(x, dict):
            if any((not isinstance(k, str) for k in x)):
                raise ValueError('JSON keys must be strings')
            for v in x.values():
                check_keys(v)
        elif isinstance(x, (tuple, list)):
            for v in x:
                check_keys(v)
    check_keys(value)
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')

def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()

def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def read_json(path: Path) -> Any:
    p = Path(path)
    if p.stat().st_size > MAX_JSON_BYTES:
        raise CVRSError('JSON_TOO_LARGE', 'JSON exceeds configured size limit')

    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError(f'duplicate JSON key: {k}')
            result[k] = v
        return result
    return json.loads(p.read_text('utf-8'), object_pairs_hook=pairs, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(f'non-finite JSON: {v}')))

def atomic_bytes(path: Path, content: bytes) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.writing-', dir=p.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, p)
    finally:
        if os.path.exists(name):
            os.unlink(name)

def write_json(path: Path, value: Any) -> None:
    atomic_bytes(path, canonical_bytes(value) + b'\n')

def write_jsonl(path: Path, rows) -> None:
    atomic_bytes(path, b''.join((canonical_bytes(x) + b'\n' for x in rows)))

def read_jsonl(path: Path) -> list[dict]:
    if Path(path).stat().st_size > MAX_JSON_BYTES:
        raise CVRSError('JSONL_TOO_LARGE', 'JSONL exceeds configured size limit')

    def unique_pairs(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f'duplicate JSONL key: {key}')
            value[key] = item
        return value
    rows = []
    with Path(path).open('r', encoding='utf-8') as f:
        for number, line in enumerate(f, 1):
            if len(line) > 8 * 1024 * 1024:
                raise CVRSError('ROW_TOO_LARGE', f'JSONL row {number} too large')
            if line.strip():
                row = json.loads(line, object_pairs_hook=unique_pairs, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
                if not isinstance(row, dict):
                    raise ValueError('JSONL records must be objects')
                rows.append(row)
    return rows

def safe_join(root: Path, relative: str) -> Path:
    from cvsubstrate.contracts.models import relative_path
    relative_path(relative)
    root = Path(root).resolve()
    p = (root / relative).resolve()
    if not p.is_relative_to(root):
        raise CVRSError('PATH_ESCAPE', 'artifact/image escapes its declared root')
    return p

def experiment_identity(spec) -> str:
    value = spec.model_dump(mode='json')
    # Locations do not define scientific identity; content digests do.
    value.pop('dataset')
    value.pop('notes', None)
    if value.get('checkpoint'):
        value['checkpoint'].pop('path')
    # Backend config paths may be semantically relevant; no magic rewriting.
    return digest(value)
