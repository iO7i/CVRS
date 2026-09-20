"""Verify the delivered archive's current manifest; works without installed CVRS."""
from pathlib import Path
import hashlib,json,sys
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'RELEASE_MANIFEST.json').read_text())
errors=[]
for name,record in manifest['files'].items():
    p=(root/name).resolve()
    if not p.is_relative_to(root) or not p.is_file() or p.is_symlink():errors.append(name);continue
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    if h.hexdigest()!=record['sha256'] or p.stat().st_size!=record['bytes']:errors.append(name)
print(json.dumps({'status':'VERIFIED' if not errors else 'FAILED','tracked_files':len(manifest['files']),'mismatches':errors,'note':'Tracked-file verification; cvrs release verify additionally detects untracked files.'},indent=2))
sys.exit(1 if errors else 0)
