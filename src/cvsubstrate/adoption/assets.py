"""Explicit checksum-locked downloads, resumable transfers and license receipts.

No automatic extraction or model execution. Network operations always require
allow_network=True; local files are permitted for offline preparation.
"""
from __future__ import annotations
from pathlib import Path
import hashlib,os,shutil,time,socket,ipaddress,urllib.request,urllib.parse
from cvsubstrate.adoption.contracts import ExternalAsset
from cvsubstrate.provenance.io import read_json,write_json,file_digest,digest,safe_join
from cvsubstrate.foundation.lifecycle import process_lock
from cvsubstrate.errors import CVRSError

class AssetManager:
    def __init__(self,root):
        self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
    def path(self,a):return self.root/'objects'/a.sha256
    def acknowledge(self,value,actor,purpose):
        a=ExternalAsset.model_validate(value)
        if not actor.strip() or not purpose.strip():raise ValueError('license acknowledgement needs actor and purpose')
        receipt={'asset_digest':digest(a),'license_id':a.license_id,'license_url':a.license_url,'actor':actor,'purpose':purpose,
                 'acknowledged_at':time.time(),'meaning':'User acknowledgement, not a grant of rights or legal approval'}
        write_json(self.root/'licenses'/(digest(a)+'.json'),receipt);return receipt
    def status(self,values):
        result=[]
        for v in values:
            a=ExternalAsset.model_validate(v);p=self.path(a)
            result.append({'id':a.id,'sha256':a.sha256,'status':'VERIFIED' if p.is_file() and file_digest(p)==a.sha256 else 'MISSING_OR_CORRUPT',
                'license_acknowledged':(self.root/'licenses'/(digest(a)+'.json')).is_file()})
        return result
    def fetch(self,value,*,allow_network=False,max_bytes=20*1024**3):
        a=ExternalAsset.model_validate(value);target=self.path(a)
        if not (self.root/'licenses'/(digest(a)+'.json')).is_file():raise CVRSError('LICENSE_ACK_REQUIRED','acknowledge this exact asset and intended use before fetching')
        if a.size_bytes is not None and a.size_bytes>max_bytes:raise CVRSError('ASSET_LIMIT','declared asset exceeds allowed bytes')
        target.parent.mkdir(exist_ok=True)
        with process_lock(self.root/('fetch-'+a.sha256+'.lock')):
            if target.is_file():
                if file_digest(target)!=a.sha256:raise CVRSError('CACHE_CORRUPT','quarantine corrupt cached object before refetching')
                return {'status':'CACHED','path':str(target),'sha256':a.sha256}
            part=target.with_suffix('.part');side=target.with_suffix('.part.json')
            if side.exists() and read_json(side).get('asset_digest')!=digest(a):raise CVRSError('RESUME_IDENTITY','partial transfer belongs to another descriptor')
            write_json(side,{'asset_digest':digest(a)})
            offset=part.stat().st_size if part.exists() else 0
            parsed=urllib.parse.urlsplit(a.source)
            if parsed.scheme in {'','file'} or len(parsed.scheme)==1 and len(a.source)>2 and a.source[1]==':':
                source=Path(urllib.request.url2pathname(parsed.path)) if parsed.scheme=='file' else Path(a.source)
                if source.resolve() in {part.resolve(),target.resolve()}:raise ValueError('asset source cannot be cache destination')
                stream=source.open('rb');stream.seek(offset);append=True
            else:
                if not allow_network:raise CVRSError('NETWORK_OPT_IN','network fetching is disabled unless explicitly permitted')
                _public_url(a.source)
                opener=urllib.request.build_opener(_CheckedRedirect())
                headers={'Range':f'bytes={offset}-'} if offset else {}
                stream=opener.open(urllib.request.Request(a.source,headers=headers),timeout=30)
                append=bool(offset and stream.status==206)
                if append:
                    cr=stream.headers.get('Content-Range','')
                    if not cr.startswith('bytes '+str(offset)+'-'):stream.close();raise CVRSError('RESUME_RANGE','server returned an incompatible range')
                else:offset=0
            count=offset
            with stream,part.open('ab' if append else 'wb') as out:
                while True:
                    data=stream.read(1024*1024)
                    if not data:break
                    count+=len(data)
                    if count>max_bytes:raise CVRSError('ASSET_LIMIT','download exceeds byte budget')
                    out.write(data)
                out.flush();os.fsync(out.fileno())
            if (a.size_bytes is not None and part.stat().st_size!=a.size_bytes) or file_digest(part)!=a.sha256:
                bad=part.with_name(part.name+'.rejected-'+str(time.time_ns()));os.replace(part,bad)
                raise CVRSError('ASSET_HASH','download quarantined: expected size/digest mismatch')
            os.replace(part,target);side.unlink(missing_ok=True)
            return {'status':'FETCHED','path':str(target),'sha256':a.sha256,'bytes':target.stat().st_size}
    def prune(self,keep,*,apply=False):
        keep=set(keep)
        with process_lock(self.root/'prune.lock'):
            candidates=[p for p in (self.root/'objects').glob('*') if p.is_file() and len(p.name)==64 and p.name not in keep]
            result={'dry_run':not apply,'candidates':[p.name for p in candidates],'bytes':sum(p.stat().st_size for p in candidates)}
            if apply:
                for p in candidates:
                    with process_lock(self.root/('fetch-'+p.name+'.lock')):p.unlink(missing_ok=True)
            return result

def _public_url(url):
    u=urllib.parse.urlsplit(url)
    if u.scheme!='https' or u.username or u.password or not u.hostname:raise CVRSError('ASSET_URL','only credential-free HTTPS URLs are permitted')
    try:addresses=socket.getaddrinfo(u.hostname,u.port or 443,type=socket.SOCK_STREAM)
    except OSError as exc:raise CVRSError('ASSET_DNS','host resolution failed') from exc
    if any(not ipaddress.ip_address(x[4][0]).is_global for x in addresses):raise CVRSError('ASSET_NETWORK','non-public destinations are rejected')
    return url
class _CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        _public_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def hf_inspect(repo_id,revision='main',*,allow_network=False,repo_type='model'):
    if not allow_network:raise CVRSError('NETWORK_OPT_IN','HF metadata resolution requires explicit network permission')
    from huggingface_hub import HfApi
    api=HfApi();info=api.repo_info(repo_id=repo_id,revision=revision,repo_type=repo_type,files_metadata=True)
    rows=[]
    for item in info.siblings or []:
        lfs=getattr(item,'lfs',None)
        rows.append({'filename':item.rfilename,'size_bytes':getattr(item,'size',None),
                     'sha256':getattr(lfs,'sha256',None) if lfs is not None else None,
                     'git_blob_id':getattr(item,'blob_id',None)})
    return {'repo_id':repo_id,'repo_type':repo_type,'requested_revision':revision,'resolved_revision':info.sha,
            'files':rows,'trust_remote_code':False,'note':'Git blob IDs are not SHA-256 file digests; small-file hashes remain unresolved until explicitly fetched.'}

def lock_local_assets(root,*,provider='local',repo_id=None,revision=None):
    root=Path(root).resolve();rows=[]
    for p in sorted(root.rglob('*')):
        if p.is_symlink():raise CVRSError('ASSET_SYMLINK','materialize actual files before creating a portable lock')
        if p.is_file():rows.append({'filename':p.relative_to(root).as_posix(),'sha256':file_digest(p),'bytes':p.stat().st_size})
    if not rows:raise ValueError('asset directory is empty')
    return {'provider':provider,'repo_id':repo_id,'revision':revision,'files':rows,'identity':digest(rows),
            'trust_remote_code':False,'scope':'weights, configuration, tokenizer and processor files are all included'}
