"""Explicit job states, cancellation tokens and portable kernel-held locks."""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import errno, os, time
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import write_json, read_json

TRANSITIONS={
 'PENDING':{'RUNNING','CANCELLED','BLOCKED','CACHED'},
 'RUNNING':{'SUCCEEDED','FAILED','CANCELLED'},
 'SUCCEEDED':{'INVALIDATED'}, 'CACHED':{'INVALIDATED'},
 'FAILED':{'PENDING','INVALIDATED'}, 'CANCELLED':{'PENDING','INVALIDATED'},
 'BLOCKED':{'PENDING','CANCELLED','INVALIDATED'},'INVALIDATED':{'PENDING'},
}

def transition(current:str,new:str)->str:
    if new not in TRANSITIONS.get(current,set()):raise CVRSError('INVALID_STATE_TRANSITION',f'{current} -> {new}')
    return new

class Cancelled(CVRSError):
    def __init__(self,reason='execution cancelled'):super().__init__('CANCELLED',reason)

class CancellationToken:
    def __init__(self,path:Path|None=None):self.path=Path(path) if path else None;self.local=False
    def cancel(self,reason='requested'):
        self.local=True
        if self.path:write_json(self.path,{'cancelled':True,'reason':reason})
    @property
    def cancelled(self):return self.local or bool(self.path and self.path.exists())
    def check(self):
        if self.cancelled:raise Cancelled()

@contextmanager
def process_lock(path:Path,timeout:float=30.0):
    """Cooperative advisory lock released by the OS on crash, POSIX/Windows.

    Lock files are deliberately not unlinked: unlinking a held lock permits
    another inode to bypass it. This does not protect against hostile writers.
    """
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    if p.is_symlink():raise CVRSError('LOCK_SYMLINK','lock cannot be a symlink')
    f=p.open('a+b');f.seek(0)
    if p.stat().st_size==0:f.write(b'0');f.flush()
    start=time.monotonic();locked=False
    try:
        while not locked:
            try:
                if os.name=='nt':
                    import msvcrt
                    f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                locked=True
            except (BlockingIOError,OSError) as e:
                if isinstance(e,OSError) and e.errno not in (errno.EACCES,errno.EAGAIN,errno.EDEADLK,None):raise
                if time.monotonic()-start>=timeout:raise CVRSError('RESOURCE_LOCKED','timed out acquiring '+p.name) from e
                time.sleep(.025)
        yield
    finally:
        if locked:
            if os.name=='nt':
                import msvcrt
                f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(f.fileno(),fcntl.LOCK_UN)
        f.close()

NON_RETRYABLE=frozenset({'DATA_INTEGRITY','INPUT_INTEGRITY','SCHEMA_MISMATCH','CHECKPOINT_MISMATCH',
 'PATH_ESCAPE','UNSUPPORTED_CAPABILITY','PROTECTED_SPLIT','ARTIFACT_INTEGRITY','CANCELLED','ACTION_OUTPUT'})
def retry_allowed(error:Exception,*,action_retry_safe:bool)->bool:
    return action_retry_safe and isinstance(error,CVRSError) and error.code in {'WORKER_TIMEOUT','TRANSIENT_IO','WORKER_TEMPORARY'}

# Cancellation is inherited by nested subprocess actions in the same controller context.
from contextvars import ContextVar
CURRENT_CANCELLATION=ContextVar('cvrs_cancellation',default=None)
@contextmanager
def cancellation_scope(token):
    previous=CURRENT_CANCELLATION.set(token)
    try:yield
    finally:CURRENT_CANCELLATION.reset(previous)
