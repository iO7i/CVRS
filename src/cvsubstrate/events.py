"""Hash-chained lifecycle events with an exclusive single-writer file lock.

The ledger is unsigned. Rewriting a whole ledger is not prevented. The operating
system releases advisory locks when an owner exits; a lock file is not ownership.
"""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime,timezone
import os,time
from pathlib import Path
from cvsubstrate.contracts.groundwork import ExecutionEvent
from cvsubstrate.provenance.io import read_jsonl,canonical_bytes,digest
from cvsubstrate.security import sanitize
from cvsubstrate.errors import CVRSError

@contextmanager
def exclusive_lock(path:Path):
    from cvsubstrate.foundation.lifecycle import process_lock
    with process_lock(path):yield

def verify_events(path:Path):
    rows=read_jsonl(path) if Path(path).exists() else [];previous=None
    for i,r in enumerate(rows):
        value=r['event'];e=ExecutionEvent.model_validate(value)
        if e.sequence!=i or e.previous_digest!=previous or r['digest']!=digest(value):raise CVRSError('EVENT_INTEGRITY','invalid event chain at '+str(i))
        previous=r['digest']
    return {'count':len(rows),'head':previous,'status':'VERIFIED'}

def append_event(path:Path,*,run_id,component,event_type,node_id=None,payload=None):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with exclusive_lock(p.with_suffix(p.suffix+'.lock')):
        status=verify_events(p)
        e=ExecutionEvent(sequence=status['count'],at=datetime.now(timezone.utc).isoformat(),run_id=run_id,node_id=node_id,
            component=component,event_type=event_type,payload=sanitize(payload or {}),previous_digest=status['head'])
        value=e.model_dump(mode='json');r={'event':value,'digest':digest(value)}
        with p.open('ab') as f:f.write(canonical_bytes(r)+b'\n');f.flush();os.fsync(f.fileno())
    return r
