"""Generate environment recipes from explicit measured or declared metadata.

Recipes are not installability certification. No package installation or network
access is performed. No credentials, indexes, editable URLs or shell code copied.
"""
from __future__ import annotations
import importlib.metadata
from pathlib import Path
import platform
import re
import sys
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.artifact_set import seal_directory
from cvsubstrate.provenance.io import digest, write_json, atomic_bytes


def capsule_from_snapshot(output: Path, packages: list[str], *, source: dict | None=None, base_image: str | None=None):
    measured={};missing=[]
    for p in packages:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',p):raise ValueError('invalid package name')
        try:measured[p]=importlib.metadata.version(p)
        except importlib.metadata.PackageNotFoundError:missing.append(p)
    return write_capsule(output,platform.python_version(),measured,source=source,
                         measured=True,missing=missing,base_image=base_image)


def write_capsule(output: Path, python_version: str, packages: dict[str,str], *, source=None,
                  measured=False, missing=None, base_image=None):
    output=Path(output)
    if output.exists():raise CVRSError('OUTPUT_EXISTS','capsule directory must be new')
    if not re.fullmatch(r'\d+\.\d+\.\d+',python_version):raise ValueError('full Python version required')
    for name,version in packages.items():
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',name) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.!+_-]*',version):
            raise ValueError('only exact package names/versions accepted; no URLs or install flags')
    if base_image is not None and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/:-]*@sha256:[a-f0-9]{64}',base_image):
        raise ValueError('Docker base must include an explicit sha256 digest')
    value={'schema_version':'1.0','python':python_version,'packages':dict(sorted(packages.items())),
        'source':source or {},'missing_packages':missing or [],'metadata_status':'MEASURED' if measured else 'DECLARED',
        'execution_verified':False,'container_base':base_image,
        'notes':['Exact versions, NOT a transitive hash-locked lockfile.',
            'Installation/reproduction has not been proven merely by generating this recipe.',
            'CUDA wheels may require an explicitly approved package index; no index credentials are stored.']}
    value['capsule_digest']=digest(value);output.mkdir(parents=True)
    write_json(output/'capsule.json',value)
    atomic_bytes(output/'requirements.exact.txt',(''.join(f'{p}=={v}\n' for p,v in sorted(packages.items()))).encode())
    env='name: cvrs-declared-capsule\ndependencies:\n  - python='+python_version+'\n  - pip\n  - pip:\n'
    env+=''.join(f'      - {p}=={v}\n' for p,v in sorted(packages.items()))
    atomic_bytes(output/'environment.yml',env.encode())
    if base_image:
        text=f'FROM {base_image}\nWORKDIR /workspace\nCOPY requirements.exact.txt /tmp/requirements.exact.txt\nRUN python -m pip install --no-cache-dir -r /tmp/requirements.exact.txt\n'
        atomic_bytes(output/'Dockerfile',text.encode())
    else:
        atomic_bytes(output/'Dockerfile.template',b'# NOT EXECUTABLE: select a Python/CUDA base image and verify its sha256.\n# Then regenerate the capsule with --base-image <image>@sha256:<digest>.\n')
    seal_directory(output)
    return value
