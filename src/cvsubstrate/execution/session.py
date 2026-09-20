"""Protocol-2 JSONL sessions with correlation, heartbeats and cancellation.

Legacy file protocol-1 workers remain supported and unchanged. Sessions execute
trusted Python, not sandboxed code. Deadline expiry always terminates the owned
process group; partial outputs are never returned as successful results.
"""
from __future__ import annotations
import json,os,queue,signal,subprocess,sys,threading,time,uuid
from pathlib import Path
from cvsubstrate.errors import CVRSError
from cvsubstrate.foundation.lifecycle import CancellationToken,Cancelled
from cvsubstrate.provenance.io import canonical_bytes
from cvsubstrate.security import sanitize
MAX_LINE=1024*1024

def run_session(argv:list[str],request:dict,*,timeout=180.0,heartbeat_timeout=15.0,
                cancel:CancellationToken|None=None,event_handler=None,capabilities=None,cwd=None):
    if timeout<=0 or heartbeat_timeout<=0:raise ValueError('positive session deadlines required')
    # Deliberately small environment. PYTHONPATH is an explicit trusted import route.
    allowed={'PATH','SYSTEMROOT','WINDIR','TEMP','TMP','TMPDIR','LANG','LC_ALL','PYTHONPATH','LD_LIBRARY_PATH','CUDA_VISIBLE_DEVICES','OMP_NUM_THREADS','MKL_NUM_THREADS'}
    env={k:v for k,v in os.environ.items() if k in allowed}
    env.update(PYTHONUNBUFFERED='1',PYTHONNOUSERSITE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',WANDB_MODE='disabled')
    p=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                       cwd=cwd,env=env,start_new_session=os.name=='posix')
    messages=queue.Queue(maxsize=128);errors=[];stderr=bytearray();stop=threading.Event()
    def read_stdout():
        try:
            while not stop.is_set():
                line=p.stdout.readline(MAX_LINE+1)
                if not line:break
                if len(line)>MAX_LINE or not line.endswith(b'\n'):raise ValueError('oversized/truncated protocol line')
                value=json.loads(line,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
                if not isinstance(value,dict):raise ValueError('message must be an object')
                while not stop.is_set():
                    try:messages.put(value,timeout=.1);break
                    except queue.Full:continue
        except Exception as e:errors.append(str(e))
    def read_stderr():
        for b in iter(lambda:p.stderr.read(1024),b''):
            stderr.extend(b)
            if len(stderr)>65536:del stderr[:-65536]
    for f in (read_stdout,read_stderr):threading.Thread(target=f,daemon=True).start()
    def send(value):
        b=canonical_bytes(value)+b'\n'
        if len(b)>MAX_LINE:raise CVRSError('REQUEST_TOO_LARGE','use file artifacts for large session inputs')
        p.stdin.write(b);p.stdin.flush()
    def terminate():
        if p.poll() is None:
            try:
                if os.name=='posix':os.killpg(p.pid,signal.SIGKILL)
                else:p.kill()
            except ProcessLookupError:pass
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:pass
    rid=uuid.uuid4().hex;start=time.monotonic();last=start;hello=False;sequence=-1
    try:
        send({'type':'hello','versions':['2.0'],'request_id':rid})
        while True:
            now=time.monotonic()
            if cancel and cancel.cancelled:
                try:send({'type':'cancel','request_id':rid})
                except (OSError,BrokenPipeError):pass
                raise Cancelled('session cancelled; worker terminated, partial files retained by owner')
            if now-start>timeout:raise CVRSError('WORKER_TIMEOUT','session deadline exceeded')
            if now-last>heartbeat_timeout:raise CVRSError('WORKER_HEARTBEAT','session heartbeat deadline exceeded')
            if errors:raise CVRSError('WORKER_PROTOCOL',errors[0])
            try:m=messages.get(timeout=.05)
            except queue.Empty:
                if p.poll() is not None:raise CVRSError('WORKER_EXIT','worker exited before terminal response: '+str(p.returncode))
                continue
            if m.get('request_id')!=rid:raise CVRSError('REQUEST_MISMATCH','uncorrelated session message')
            if m.get('version')!='2.0':raise CVRSError('PROTOCOL_VERSION','session must negotiate version 2.0')
            if not isinstance(m.get('sequence'),int) or m['sequence']!=sequence+1:raise CVRSError('WORKER_SEQUENCE','missing/reordered session message')
            sequence=m['sequence'];last=time.monotonic();kind=m.get('type')
            if not hello:
                if kind!='hello':raise CVRSError('WORKER_PROTOCOL','handshake must precede execution')
                declared=m.get('capabilities',[])
                if set(capabilities or [])-set(declared):raise CVRSError('UNSUPPORTED_CAPABILITY','worker does not declare required capabilities')
                hello=True;send({'type':'execute','version':'2.0','request_id':rid,'payload':request});continue
            if kind in {'heartbeat','progress','event'}:
                if event_handler:event_handler(sanitize(m))
                continue
            if kind=='result':
                if m.get('status')=='SUCCEEDED' and isinstance(m.get('result'),dict):
                    return {'result':m['result'],'request_id':rid,'protocol_version':'2.0','messages':sequence+1}
                e=m.get('error') or {};raise CVRSError(e.get('code','WORKER_FAILED'),e.get('message','worker failed'))
            raise CVRSError('WORKER_PROTOCOL','unexpected message type '+str(kind))
    finally:
        stop.set();terminate()
        for f in (p.stdin,p.stdout,p.stderr):
            try:f.close()
            except OSError:pass

def legacy_handler(payload,context):
    """Session-2 envelope around an existing *real* protocol-1 native worker."""
    from cvsubstrate.contracts.models import WorkerRequest
    from cvsubstrate.execution.process import invoke
    context.progress({'phase':'native_worker_start','adapter':payload['adapter']})
    response=invoke(payload['adapter'],WorkerRequest.model_validate(payload['request']),
                    payload.get('worker_python'),payload.get('timeout',180),
                    cancel_token=context.token)
    return response.model_dump(mode='json')
