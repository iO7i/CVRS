"""Worker side of protocol 2. One active request per process, native stdout isolated."""
from __future__ import annotations
import argparse,contextlib,importlib,json,sys,threading,time
from cvsubstrate.foundation.lifecycle import CancellationToken
from cvsubstrate.provenance.io import canonical_bytes
from cvsubstrate.errors import CVRSError

class SessionContext:
    def __init__(self,send,token):self._send=send;self.token=token
    def check_cancelled(self):self.token.check()
    def progress(self,value):self._send('progress',payload=value)

def serve(handler,capabilities=('execute',),heartbeat_interval=1.0):
    wire=sys.stdout.buffer;lock=threading.Lock();sequence=0
    first=sys.stdin.buffer.readline(1024*1024+1)
    if len(first)>1024*1024 or not first.endswith(b'\n'):raise ValueError('invalid handshake line')
    hello=json.loads(first);rid=hello.get('request_id')
    if hello.get('type')!='hello' or '2.0' not in hello.get('versions',[]):raise ValueError('protocol negotiation failed')
    def send(kind,**data):
        nonlocal sequence
        with lock:
            wire.write(canonical_bytes({'type':kind,'version':'2.0','request_id':rid,'sequence':sequence,**data})+b'\n');wire.flush();sequence+=1
    send('hello',capabilities=list(capabilities))
    line=sys.stdin.buffer.readline(1024*1024+1)
    if len(line)>1024*1024 or not line.endswith(b'\n'):raise ValueError('invalid request line')
    request=json.loads(line)
    if request.get('type')!='execute' or request.get('request_id')!=rid or request.get('version')!='2.0':raise ValueError('invalid execute request')
    token=CancellationToken();finished=threading.Event()
    def control():
        for line in iter(lambda:sys.stdin.buffer.readline(1024*1024+1),b''):
            if len(line)>1024*1024:token.cancel('oversized control');return
            try:m=json.loads(line)
            except (ValueError,TypeError):token.cancel('invalid control');return
            if m.get('type')=='cancel' and m.get('request_id')==rid:token.cancel();return
    def heartbeat():
        while not finished.wait(heartbeat_interval):send('heartbeat')
    threading.Thread(target=control,daemon=True).start();threading.Thread(target=heartbeat,daemon=True).start()
    try:
        with contextlib.redirect_stdout(sys.stderr):result=handler(request['payload'],SessionContext(send,token))
        token.check()
        if not isinstance(result,dict):raise ValueError('handler must return a JSON object')
        finished.set();send('result',status='SUCCEEDED',result=result)
    except Exception as exc:
        finished.set();send('result',status='FAILED',error=exc.as_dict() if isinstance(exc,CVRSError) else {'code':'WORKER_FAILURE','message':str(exc)})

def main():
    p=argparse.ArgumentParser();p.add_argument('--handler',default='cvsubstrate.execution.session:legacy_handler');p.add_argument('--trust-local-code',action='store_true');a=p.parse_args()
    if a.handler!='cvsubstrate.execution.session:legacy_handler' and not a.trust_local_code:p.error('external handler requires --trust-local-code')
    module,name=a.handler.split(':',1);serve(getattr(importlib.import_module(module),name))
if __name__=='__main__':main()
