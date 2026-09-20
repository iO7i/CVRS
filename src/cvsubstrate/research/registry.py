"""Local transactional research registry. Integrity is not publisher authentication.

All public write methods append immutable content-addressed records. An attempt
never edits its claim. Failed attempts and supersession edges remain queryable.
Evidence files are copied into a verified object store, not executed or unpickled.
"""
from __future__ import annotations
import contextlib
import html
import json
import os
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any
from cvsubstrate.contracts.frontier import ClaimSpec, ReproductionAttempt, IndependenceReview
from cvsubstrate.provenance.io import canonical_bytes, digest, file_digest, read_json, write_json
from cvsubstrate.provenance.artifact_set import seal_directory, verify_directory, assert_not_inside_sealed
from cvsubstrate.errors import CVRSError

KINDS={'claim':ClaimSpec,'attempt':ReproductionAttempt,'review':IndependenceReview}
LEVELS=['R0_METADATA','R1_ARTIFACTS','R2_EXECUTION','R3_METRICS','R4_REVIEWED_INDEPENDENT_ENVIRONMENT','R5_REVIEWED_CROSS_IMPLEMENTATION']

def _hash(value):
    if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('invalid SHA-256 object reference')
    return value

class ResearchRegistry:
    def __init__(self, root:Path):
        self.root=Path(root).resolve();assert_not_inside_sealed(self.root)
        self.root.mkdir(parents=True,exist_ok=True);(self.root/'objects').mkdir(exist_ok=True)
        self.db=sqlite3.connect(self.root/'registry.sqlite',timeout=30)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS objects(sha TEXT PRIMARY KEY,bytes INTEGER NOT NULL,media_type TEXT NOT NULL,license_status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY,kind TEXT NOT NULL,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS edges(source TEXT NOT NULL,target TEXT NOT NULL,reason TEXT NOT NULL,PRIMARY KEY(source,target));
        CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY,kind TEXT NOT NULL,record_id TEXT NOT NULL,previous TEXT NOT NULL,hash TEXT NOT NULL,payload TEXT NOT NULL);
        """)
        row=self.db.execute('SELECT value FROM metadata WHERE key="format"').fetchone()
        if row and row[0]!='cvrs-research-registry/1.0':raise ValueError('unsupported registry format')
        with self.db:self.db.execute('INSERT OR IGNORE INTO metadata VALUES("format","cvrs-research-registry/1.0")')
    def close(self):
        self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');self.db.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def _event(self,kind,record_id,payload):
        payload={**payload,'recorded_at_unix':time.time()}
        last=self.db.execute('SELECT seq,hash FROM events ORDER BY seq DESC LIMIT 1').fetchone()
        seq=last['seq']+1 if last else 1;previous=last['hash'] if last else '0'*64
        body={'seq':seq,'kind':kind,'record_id':record_id,'previous':previous,'payload':payload}
        self.db.execute('INSERT INTO events VALUES(?,?,?,?,?,?)',(seq,kind,record_id,previous,digest(body),canonical_bytes(payload).decode()))
    def _insert(self,kind,model):
        payload=model.model_dump(mode='json') if hasattr(model,'model_dump') else model
        rid=digest({'kind':kind,'payload':payload});encoded=canonical_bytes(payload).decode()
        old=self.db.execute('SELECT kind,payload FROM records WHERE id=?',(rid,)).fetchone()
        if old:
            if old['kind']!=kind or old['payload']!=encoded:raise ValueError('content identity collision')
            return rid
        self.db.execute('INSERT INTO records VALUES(?,?,?)',(rid,kind,encoded));self._event('REGISTER_'+kind.upper(),rid,{'kind':kind})
        return rid
    def add_file(self,path:Path,*,media_type='application/octet-stream',license_status='UNKNOWN',expected_sha256=None):
        source=Path(path)
        if source.is_symlink() or not source.is_file():raise ValueError('regular local evidence file required')
        sha=file_digest(source)
        if expected_sha256 and sha!=_hash(expected_sha256):raise ValueError('evidence hash mismatch')
        target=self.root/'objects'/sha
        fd,tmp=tempfile.mkstemp(prefix='.import-',dir=self.root/'objects');os.close(fd)
        try:
            shutil.copyfile(source,tmp)
            if file_digest(Path(tmp))!=sha:raise CVRSError('SOURCE_CHANGED','evidence changed during import')
            if target.exists():
                if file_digest(target)!=sha:raise CVRSError('ARTIFACT_INTEGRITY','stored evidence was modified')
            else:os.replace(tmp,target)
        finally:
            if Path(tmp).exists():Path(tmp).unlink()
        size=target.stat().st_size
        with self.db:
            row=self.db.execute('SELECT bytes FROM objects WHERE sha=?',(sha,)).fetchone()
            if row and row['bytes']!=size:raise ValueError('object size mismatch')
            if not row:
                self.db.execute('INSERT INTO objects VALUES(?,?,?,?)',(sha,size,media_type,license_status));self._event('IMPORT_EVIDENCE',sha,{'bytes':size})
        return sha
    def add_json(self,value,*,license_status='UNKNOWN'):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'evidence.json';write_json(p,value)
            return self.add_file(p,media_type='application/json',license_status=license_status)
    def object_path(self,sha):
        sha=_hash(sha);row=self.db.execute('SELECT bytes FROM objects WHERE sha=?',(sha,)).fetchone();p=self.root/'objects'/sha
        if not row or p.is_symlink() or not p.is_file() or p.stat().st_size!=row['bytes'] or file_digest(p)!=sha:
            raise CVRSError('ARTIFACT_INTEGRITY','missing or modified evidence: '+sha)
        return p
    def evidence_json(self,sha):return read_json(self.object_path(sha))
    def get(self,rid,kind=None):
        row=self.db.execute('SELECT kind,payload FROM records WHERE id=?',(_hash(rid),)).fetchone()
        if not row:raise KeyError(rid)
        if kind and row['kind']!=kind:raise ValueError('wrong record kind')
        payload=json.loads(row['payload'])
        if digest({'kind':row['kind'],'payload':payload})!=rid:raise CVRSError('ARTIFACT_INTEGRITY','record identity mismatch')
        return {'id':rid,'kind':row['kind'],'payload':payload}
    def list(self,kind=None):
        rows=self.db.execute('SELECT id FROM records WHERE kind=? ORDER BY id',(kind,)) if kind else self.db.execute('SELECT id FROM records ORDER BY kind,id')
        return [self.get(r['id']) for r in rows]
    def register_claim(self,claim):
        c=ClaimSpec.model_validate(claim)
        with self.db:return self._insert('claim',c)
    def register_attempt(self,attempt):
        a=ReproductionAttempt.model_validate(attempt);claim=ClaimSpec.model_validate(self.get(a.claim_id,'claim')['payload'])
        if a.purpose!=claim.purpose:raise ValueError('fixture/research purposes cannot be mixed')
        for sha in a.evidence.values():self.object_path(sha)
        with self.db:return self._insert('attempt',a)
    def register_review(self,review):
        r=IndependenceReview.model_validate(review);a=ReproductionAttempt.model_validate(self.get(r.attempt_id,'attempt')['payload']);c=ClaimSpec.model_validate(self.get(a.claim_id,'claim')['payload'])
        if r.reviewer_id in {a.actor_id,c.author_id}:raise ValueError('self-review cannot establish independence')
        self.object_path(r.evidence_sha256)
        with self.db:return self._insert('review',r)
    def supersede(self,old,new,reason):
        if not reason or len(reason.strip())<10:raise ValueError('explicit supersession rationale required')
        self.get(old,'claim');self.get(new,'claim')
        if old==new:raise ValueError('self supersession')
        # Existing edges old -> newer must remain a DAG.
        todo=[new];seen=set()
        while todo:
            cur=todo.pop()
            if cur==old:raise ValueError('supersession cycle')
            if cur in seen:continue
            seen.add(cur);todo.extend(r[0] for r in self.db.execute('SELECT target FROM edges WHERE source=?',(cur,)))
        with self.db:
            existing=self.db.execute('SELECT reason FROM edges WHERE source=? AND target=?',(old,new)).fetchone()
            if existing and existing[0]!=reason:raise ValueError('immutable supersession edge')
            if not existing:
                self.db.execute('INSERT INTO edges VALUES(?,?,?)',(old,new,reason));self._event('SUPERSEDE',old,{'new':new,'reason':reason})
        return {'source':old,'target':new,'reason':reason}
    def _receipt(self,a,name):
        sha=a.evidence.get(name)
        return self.evidence_json(sha) if sha else None
    def assess_attempt(self,attempt_id):
        a=ReproductionAttempt.model_validate(self.get(attempt_id,'attempt')['payload']);c=ClaimSpec.model_validate(self.get(a.claim_id,'claim')['payload'])
        for sha in a.evidence.values():self.object_path(sha)
        mismatch=[k for k in ['dataset_sha256','protocol_sha256','estimand'] if getattr(c,k)!=getattr(a,k)]
        result={'attempt_id':attempt_id,'claim_id':a.claim_id,'outcome':a.outcome,'purpose':a.purpose,'level':LEVELS[0],
                'status':'CLAIMED','mismatches':mismatch,'failure_reason':a.failure_reason,'metric_deltas':{},
                'limits':['Unsigned evidence is not proof of publisher identity, genuine model execution, or reviewer independence.','Different implementations may reproduce a declared estimand without being equivalent algorithms.']}
        if mismatch:result['status']='INCOMPARABLE';return result
        if a.outcome!='completed':result['status']='FAILED_TO_REPRODUCE' if a.outcome=='failed' else 'BLOCKED';return result
        required={'dataset','protocol','predictions','environment','experiment'}
        if required.issubset(a.evidence):
            for name, expected in [('dataset',a.dataset_sha256),('protocol',a.protocol_sha256),('experiment',a.experiment_sha256)]:
                if digest(self._receipt(a,name))!=expected:
                    result['status']='EVIDENCE_MISMATCH';result['evidence_gap']=name+' identity differs';return result
            result['level']=LEVELS[1];result['status']='ARTIFACTS_PRESERVED'
        if a.implementation_id==c.implementation_id and a.experiment_sha256!=c.experiment_sha256:
            result['status']='INCOMPARABLE';result['mismatches'].append('experiment_sha256');return result
        # Receipts must bind the actual immutable evidence bytes, not just contain PASS.
        execute=self._receipt(a,'execution')
        native_ok=(isinstance(execute,dict) and execute.get('status')=='SUCCEEDED' and execute.get('operation') in {'predict','train_predict'}
            and execute.get('execution_kind')=='native' and execute.get('purpose')==a.purpose
            and execute.get('dataset_sha256')==a.dataset_sha256 and execute.get('experiment_sha256')==a.experiment_sha256
            and execute.get('predictions_sha256')==a.evidence.get('predictions')
            and execute.get('implementation_id')==a.implementation_id)
        if native_ok and result['level']==LEVELS[1]:result['level']=LEVELS[2];result['status']='EXECUTED'
        ev=self._receipt(a,'evaluation')
        eval_ok=(isinstance(ev,dict) and ev.get('status')=='EVALUATED' and ev.get('dataset_sha256')==a.dataset_sha256
            and ev.get('protocol_sha256')==a.protocol_sha256 and ev.get('predictions_sha256')==a.evidence.get('predictions')
            and ev.get('metrics')==a.metrics and ev.get('evaluator_identity'))
        if not eval_ok:result['evidence_gap']='bound evaluation receipt missing';return result
        if not set(c.reported_metrics).issubset(a.metrics):result['evidence_gap']='required metric missing';return result
        result['metric_deltas']={k:a.metrics[k]-v for k,v in c.reported_metrics.items()}
        within=all(abs(result['metric_deltas'][k])<=c.absolute_tolerances[k] for k in c.reported_metrics)
        if not within:result['status']='FAILED_TO_REPRODUCE';result['reason']='predeclared metric tolerance exceeded';return result
        if result['level']!=LEVELS[2]:result['status']='REEVALUATED_ARTIFACTS_ONLY';return result
        if a.attempt_kind=='original':
            result['status']='ORIGINAL_EXECUTION_RECORDED';result['reported_metrics_matched']=True
            if a.purpose=='software_fixture':result['status']='FIXTURE_'+result['status']
            return result
        if a.attempt_kind=='reevaluation':
            result['status']='REEVALUATED_ARTIFACTS_ONLY';return result
        originals=[x['payload'] for x in self.list('attempt') if x['payload']['claim_id']==a.claim_id and x['payload'].get('attempt_kind')=='original']
        if any(x['evidence'].get('execution')==a.evidence.get('execution') for x in originals):
            result['status']='DUPLICATE_ORIGINAL_ARTIFACTS';return result
        result['level']=LEVELS[3];result['status']='REPRODUCED' 
        # Machine/operator names alone never promote a result. Explicit third-party
        # review is retained as attestation, not silently treated as authentication.
        reviews=[r for r in self.list('review') if r['payload']['attempt_id']==attempt_id]
        baselines=[r['payload'] for r in self.list('attempt') if r['payload']['claim_id']==a.claim_id and r['payload']['actor_id']==c.author_id and r['payload']['implementation_id']==c.implementation_id]
        eligible=[r for r in reviews if r['payload']['independent_operator_attested'] and r['payload']['independent_machine_attested']]
        independent_ids=(a.actor_id!=c.author_id and any(b['machine_id']!=a.machine_id and b['outcome']=='completed' for b in baselines))
        if eligible and independent_ids:
            for r in eligible:self.object_path(r['payload']['evidence_sha256'])
            result['level']=LEVELS[4];result['status']='INDEPENDENTLY_REPRODUCED_ATTESTED';result['review_ids']=[r['id'] for r in eligible]
            if a.implementation_id!=c.implementation_id and any(r['payload']['independent_implementation_attested'] for r in eligible):result['level']=LEVELS[5]
        if a.purpose=='software_fixture':
            result['status']='FIXTURE_'+result['status'];result['scientific_certification']='NONE'
        return result
    def status(self,claim_id):
        claim=self.get(claim_id,'claim');attempts=[self.assess_attempt(r['id']) for r in self.list('attempt') if r['payload']['claim_id']==claim_id]
        best=max([LEVELS.index(a['level']) for a in attempts]+[0])
        newer=[dict(r) for r in self.db.execute('SELECT target,reason FROM edges WHERE source=? ORDER BY target',(claim_id,))]
        return {'claim':claim,'level':LEVELS[best],'purpose':claim['payload']['purpose'],'superseded_by':newer,'attempts':attempts,
            'failed_attempts':sum('FAILED_TO_REPRODUCE' in a['status'] for a in attempts),'blocked_attempts':sum(a['status']=='BLOCKED' for a in attempts),
            'certification':'EVIDENCE_SCOPED; independence is separately attested, not authenticated'}
    def verify(self):
        errors=[]
        for r in self.db.execute('SELECT sha FROM objects'):
            try:self.object_path(r['sha'])
            except Exception as exc:errors.append(str(exc))
        for r in self.db.execute('SELECT id FROM records'):
            try:self.get(r['id'])
            except Exception as exc:errors.append(str(exc))
        previous='0'*64;seq=0;seen_records=set();seen_objects=set();seen_edges={}
        for row in self.db.execute('SELECT * FROM events ORDER BY seq'):
            seq+=1
            try:
                payload=json.loads(row['payload'])
                body={'seq':row['seq'],'kind':row['kind'],'record_id':row['record_id'],'previous':row['previous'],'payload':payload}
                if row['seq']!=seq or row['previous']!=previous or digest(body)!=row['hash']:errors.append('event chain mismatch at '+str(seq))
                if row['kind'].startswith('REGISTER_'):
                    record=self.get(row['record_id'])
                    if row['kind']!='REGISTER_'+record['kind'].upper():errors.append('record event kind mismatch')
                    seen_records.add(row['record_id'])
                elif row['kind']=='IMPORT_EVIDENCE':
                    obj=self.db.execute('SELECT bytes FROM objects WHERE sha=?',(row['record_id'],)).fetchone()
                    if not obj or obj['bytes']!=payload['bytes']:errors.append('evidence event inventory mismatch')
                    seen_objects.add(row['record_id'])
                elif row['kind']=='SUPERSEDE':
                    self.get(row['record_id'],'claim');self.get(payload['new'],'claim')
                    seen_edges[(row['record_id'],payload['new'])]=payload['reason']
                else:errors.append('unsupported event kind '+row['kind'])
            except Exception as exc:errors.append('event reference invalid at '+str(seq)+': '+str(exc))
            previous=row['hash']
        if seen_records!={x['id'] for x in self.db.execute('SELECT id FROM records')}:errors.append('record/event inventory mismatch')
        if seen_objects!={x['sha'] for x in self.db.execute('SELECT sha FROM objects')}:errors.append('evidence/event inventory mismatch')
        actual_edges={(x['source'],x['target']):x['reason'] for x in self.db.execute('SELECT * FROM edges')}
        if actual_edges!=seen_edges:errors.append('supersession/event inventory mismatch')
        for item in self.db.execute('SELECT id FROM records'):
            try:
                record=self.get(item['id'])
                if record['kind']=='attempt':
                    a=ReproductionAttempt.model_validate(record['payload']);self.get(a.claim_id,'claim')
                    for sha in a.evidence.values():self.object_path(sha)
                elif record['kind']=='review':
                    rv=IndependenceReview.model_validate(record['payload']);self.get(rv.attempt_id,'attempt');self.object_path(rv.evidence_sha256)
                elif record['kind']=='claim':ClaimSpec.model_validate(record['payload'])
                else:errors.append('unknown record kind')
            except Exception as exc:errors.append('record reference invalid: '+str(exc))
        return {'status':'VERIFIED' if not errors else 'FAILED','errors':errors,'events':seq,'records':self.db.execute('SELECT COUNT(*) FROM records').fetchone()[0],
            'head':previous,'authentication':'NOT_AUTHENTICATED'}
    def export(self,destination:Path):
        target=Path(destination).resolve();assert_not_inside_sealed(target)
        if target.exists() or target.is_relative_to(self.root):raise ValueError('new snapshot path outside registry required')
        v=self.verify()
        if v['status']!='VERIFIED':raise CVRSError('ARTIFACT_INTEGRITY','registry does not verify')
        target.mkdir(parents=True);(target/'objects').mkdir()
        payload={'format':'cvrs-research-registry-snapshot','version':'1.0','records':self.list(),
            'objects':[dict(r) for r in self.db.execute('SELECT * FROM objects ORDER BY sha')],
            'supersessions':[dict(r) for r in self.db.execute('SELECT * FROM edges ORDER BY source,target')],
            'events':[dict(r) for r in self.db.execute('SELECT * FROM events ORDER BY seq')],
            'verification':v,'limits':['Local/static snapshot; no remote publication','Unsigned integrity, not independent authentication']}
        for obj in payload['objects']:shutil.copyfile(self.object_path(obj['sha']),target/'objects'/obj['sha'])
        write_json(target/'registry.json',payload)
        rows=[]
        for c in self.list('claim'):
            status=self.status(c['id']);write_json(target/'claims'/f"{c['id']}.json",status)
            rows.append('<tr><td><a href="claims/'+c['id']+'.json">'+html.escape(c['payload']['title'])+'</a></td><td>'+html.escape(status['level'])+'</td><td>'+str(len(status['attempts']))+'</td><td>'+html.escape(status['purpose'])+'</td></tr>')
        (target/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>CVRS Research Registry</title><h1>Research records</h1><p>Evidence-scoped reports. Review attestations are not authenticated independence. Fixture records are not research results.</p><table><thead><tr><th>Claim</th><th>Evidence level</th><th>Attempts</th><th>Purpose</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></html>')
        seal_directory(target);return {'status':'EXPORTED','path':str(target),'claims':len(rows),'verification':verify_directory(target)}

def import_snapshot(source:Path,destination:Path):
    source=Path(source);destination=Path(destination)
    if destination.exists():raise ValueError('new registry destination required')
    if verify_directory(source)['status']!='VERIFIED':raise CVRSError('ARTIFACT_INTEGRITY','snapshot failed verification')
    payload=read_json(source/'registry.json')
    if payload.get('format')!='cvrs-research-registry-snapshot' or payload.get('version')!='1.0':raise ValueError('unsupported snapshot')
    # Build separately; a failed import cannot leave an apparently usable registry.
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=Path(tempfile.mkdtemp(prefix='.registry-',dir=destination.parent))
    try:
        with ResearchRegistry(temporary) as reg:
            for obj in payload['objects']:reg.add_file(source/'objects'/_hash(obj['sha']),media_type=obj['media_type'],license_status=obj['license_status'],expected_sha256=obj['sha'])
            for kind in ['claim','attempt','review']:
                for record in payload['records']:
                    if record['kind']!=kind:continue
                    fn={'claim':reg.register_claim,'attempt':reg.register_attempt,'review':reg.register_review}[kind]
                    if fn(record['payload'])!=record['id']:raise ValueError('record identity changed')
            for edge in payload['supersessions']:reg.supersede(edge['source'],edge['target'],edge['reason'])
            # Preserve the original event chain, not a fabricated new historical order.
            with reg.db:
                reg.db.execute('DELETE FROM events')
                for e in payload['events']:reg.db.execute('INSERT INTO events VALUES(?,?,?,?,?,?)',(e['seq'],e['kind'],e['record_id'],e['previous'],e['hash'],e['payload']))
            v=reg.verify()
            if v['status']!='VERIFIED' or v['head']!=payload['verification']['head']:raise ValueError('imported event history mismatch')
        os.replace(temporary,destination)
        return {'status':'IMPORTED','path':str(destination),'verification':v}
    finally:
        if temporary.exists():shutil.rmtree(temporary)
