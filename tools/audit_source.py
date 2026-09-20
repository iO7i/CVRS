"""Offline source/dependency inventory. NOT a vulnerability or security certification.

Reports syntax errors and selected executable-code surfaces without running them.
No secret values or environment credentials are copied. No package installs occur.
"""
import argparse
import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys


def audit(root):
    root=Path(root).resolve();files=[];syntax=[];surfaces=[]
    for path in sorted((root/'src').rglob('*.py')):
        relative=path.relative_to(root).as_posix();raw=path.read_bytes()
        files.append({'path':relative,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
        try:tree=ast.parse(raw,filename=relative)
        except SyntaxError as exc:syntax.append({'path':relative,'line':exc.lineno,'reason':exc.msg});continue
        for node in ast.walk(tree):
            if not isinstance(node,ast.Call):continue
            f=node.func
            name=f.id if isinstance(f,ast.Name) else f.attr if isinstance(f,ast.Attribute) else None
            if name in {'eval','exec','exec_module','fromfile','load','Popen','run'}:
                surfaces.append({'path':relative,'line':node.lineno,'call':name,'status':'MANUAL_REVIEW_SURFACE_NOT_A_VULNERABILITY_VERDICT'})
            if any(k.arg=='shell' and isinstance(k.value,ast.Constant) and k.value.value is True for k in node.keywords):
                surfaces.append({'path':relative,'line':node.lineno,'call':name,'status':'SHELL_TRUE_REVIEW_REQUIRED'})
    dependencies={}
    for name in ['pydantic','pydantic-core','torch','torchvision','Pillow','numpy','pycocotools','rasterio','pyproj','shapely','pytest','ruff','mypy']:
        try:dependencies[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:dependencies[name]=None
    return {'status':'SYNTAX_VALID' if not syntax else 'SYNTAX_FAILURE','python':sys.version,'files':files,
        'syntax_errors':syntax,'review_surfaces':surfaces,'installed_versions':dependencies,
        'limits':['Offline inventory only. No CVE database queried; dependency vulnerability status UNKNOWN.',
            'No transitive wheel-hash lock or hosted CI execution is implied.',
            'Trusted legacy configs/checkpoints/plugins are executable; process isolation is not a sandbox.',
            'Package signatures, remote artifact authenticity and licenses require separate review.']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():p.error('output exists; preserve prior evidence')
    value=audit(a.root);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({'status':value['status'],'files':len(value['files']),'review_surfaces':len(value['review_surfaces']),'output':str(a.out)},indent=2))
    return 0 if not value['syntax_errors'] else 2

if __name__=='__main__':raise SystemExit(main())
