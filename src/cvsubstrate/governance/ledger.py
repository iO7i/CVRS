"""Hash-chained, locked, append-only-by-API research ledger.

Anyone who controls the filesystem can rewrite a whole ledger or truncate its
tail. An externally retained head digest can detect this; local hashes alone
cannot. Stale locks require explicit operator inspection/removal, never guessing.
"""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import time
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import canonical_bytes, digest, read_jsonl

GENESIS='0'*64


@contextmanager
def file_lock(path: Path, timeout=5.0):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    deadline=time.monotonic()+timeout
    while True:
        try:
            fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            os.write(fd,canonical_bytes({'pid':os.getpid(),'created_at':datetime.now(timezone.utc).isoformat()}))
            os.fsync(fd); os.close(fd)
            break
        except FileExistsError:
            if time.monotonic()>=deadline:
                raise CVRSError('LEDGER_LOCKED','ledger locked; inspect stale lock rather than deleting it automatically')
            time.sleep(0.02)
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


class Ledger:
    def __init__(self,path: Path):
        self.path=Path(path).absolute()
        self.lock=self.path.with_name(self.path.name+'.lock')

    def rows(self):
        if not self.path.exists():
            return []
        if self.path.is_symlink():
            raise CVRSError('LEDGER_SYMLINK','symlink ledger not allowed')
        if self.path.stat().st_size and not self.path.read_bytes().endswith(b'\n'):
            raise CVRSError('LEDGER_PARTIAL','incomplete final journal line; preserve it and recover explicitly')
        rows=read_jsonl(self.path)
        previous=GENESIS
        for i,row in enumerate(rows):
            expected_keys={'schema_version','sequence','previous_digest','at','event','payload','digest'}
            if set(row)!=expected_keys or row['schema_version']!='1.0' or row['sequence']!=i+1 or row['previous_digest']!=previous:
                raise CVRSError('LEDGER_CHAIN','invalid sequence/schema/parent in ledger')
            base={k:v for k,v in row.items() if k!='digest'}
            if digest(base)!=row['digest']:
                raise CVRSError('LEDGER_CHAIN','ledger payload digest mismatch')
            previous=row['digest']
        return rows

    def _append_locked(self,event,payload,rows):
        if not isinstance(event,str) or not event or not isinstance(payload,dict):
            raise ValueError('event name and JSON object payload required')
        base={'schema_version':'1.0','sequence':len(rows)+1,
              'previous_digest':rows[-1]['digest'] if rows else GENESIS,
              'at':datetime.now(timezone.utc).isoformat(),'event':event,'payload':payload}
        record={**base,'digest':digest(base)}
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open('ab') as f:
            f.write(canonical_bytes(record)+b'\n');f.flush();os.fsync(f.fileno())
        return record

    def append(self,event,payload):
        with file_lock(self.lock):
            return self._append_locked(event,payload,self.rows())

    def verify(self,expected_head=None):
        try:
            rows=self.rows();head=rows[-1]['digest'] if rows else GENESIS
            if expected_head is not None and head!=expected_head:
                raise CVRSError('LEDGER_HEAD','head differs from independently retained expected digest')
            return {'status':'VERIFIED','entries':len(rows),'head_digest':head,
                'limits':'Local hash chain: complete rewrite/tail removal needs an external expected head to detect.'}
        except (CVRSError,OSError,ValueError) as exc:
            return {'status':'FAILED','error':str(exc)}

    def consume(self,event,payload, *, validate):
        """Check then append atomically, for limited-use test approvals."""
        with file_lock(self.lock):
            rows=self.rows();validate(rows)
            return self._append_locked(event,payload,rows)
