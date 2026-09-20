"""CAS lifecycle: cooperative multi-writer publication, roots, pins and GC.

All operations performed by this class use one process lock, so an object cannot
be collected while it is being pinned. Garbage collection defaults to dry-run
and requires a freshness-bound plan for deletion. Legacy store objects remain
addressable and are included in inventory; absent roots are not assumed live.
"""
from __future__ import annotations
import os, re, time
from pathlib import Path
from cvsubstrate.artifacts.store import LocalArtifactStore
from cvsubstrate.foundation.lifecycle import process_lock
from cvsubstrate.provenance.io import read_json,write_json,digest,file_digest,atomic_bytes
from cvsubstrate.errors import CVRSError

class ManagedArtifactStore(LocalArtifactStore):
    def __init__(self,root):
        super().__init__(root);self.lock=self.root/'lifecycle.lock';self.roots=self.root/'roots.json'
    def _roots(self):return read_json(self.roots) if self.roots.exists() else {}
    def put(self,path,media_type='application/octet-stream',*,pin=None):
        with process_lock(self.lock):
            ref=super().put(path,media_type)
            if pin is not None:
                roots=self._roots();roots[pin]=sorted(set(roots.get(pin,[])+[ref.sha256]));write_json(self.roots,roots)
            return ref
    def pin(self,name,hashes):
        if not isinstance(name,str) or not name or len(name)>256:raise ValueError('nonempty root name required')
        hashes=sorted(set(hashes))
        with process_lock(self.lock):
            for sha in hashes:self.get(sha)
            roots=self._roots();roots[name]=hashes;write_json(self.roots,roots)
        return {'root':name,'objects':hashes}
    def unpin(self,name):
        with process_lock(self.lock):
            roots=self._roots()
            if name not in roots:raise KeyError(name)
            del roots[name];write_json(self.roots,roots)
    def inventory(self):
        rows=[]
        for p in sorted(self.objects.glob('*/*')):
            sha=p.parent.name+p.name
            if not re.fullmatch('[a-f0-9]{64}',sha):continue
            if p.is_symlink():raise CVRSError('ARTIFACT_SYMLINK','symlink in object store')
            rows.append({'sha256':sha,'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns})
        return rows
    def gc(self,*,minimum_age_seconds=86400,dry_run=True,plan_digest=None):
        if minimum_age_seconds<0:raise ValueError('negative grace period')
        with process_lock(self.lock):
            roots=self._roots();live={s for h in roots.values() for s in h}
            # Action-cache references are roots, too. Corrupt indexes block deletion.
            for p in sorted((self.root/'actions').glob('*.json')):
                entry=read_json(p)
                if entry.get('record_digest')!=digest(entry.get('record')):raise CVRSError('CACHE_CORRUPT','invalid action index')
                live.update(a['sha256'] for a in entry['record'].get('artifacts',{}).values())
            inventory=self.inventory();now=time.time_ns()
            candidates=[x for x in inventory if x['sha256'] not in live and (now-x['mtime_ns'])/1e9>=minimum_age_seconds]
            plan={'roots_digest':digest(roots),'live':sorted(live),'inventory':inventory,'candidates':candidates,
                  'minimum_age_seconds':minimum_age_seconds}
            key=digest(plan)
            if not dry_run:
                if plan_digest!=key:raise CVRSError('GC_PLAN_CHANGED','re-run dry-run and approve the exact plan')
                for x in candidates:
                    p=self.get(x['sha256']);p.unlink()
                write_json(self.root/'gc-history'/(str(time.time_ns())+'.json'),{'plan':plan,'digest':key})
            return {'dry_run':dry_run,'plan_digest':key,'objects':len(candidates),'bytes':sum(x['bytes'] for x in candidates),'candidates':candidates}
    def materialize(self,sha256,destination):
        dst=Path(destination)
        with process_lock(self.lock):
            if dst.exists():raise CVRSError('OUTPUT_EXISTS','materialization does not overwrite')
            src=self.get(sha256);dst.parent.mkdir(parents=True,exist_ok=True)
            # create-new final file: no race with an existing destination
            with dst.open('xb') as out,src.open('rb') as inp:
                for chunk in iter(lambda:inp.read(1024*1024),b''):out.write(chunk)
                out.flush();os.fsync(out.fileno())
            if file_digest(dst)!=sha256:raise CVRSError('ARTIFACT_INTEGRITY','materialization mismatch')
        return dst
