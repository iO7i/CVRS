"""Registry v2: immutable records, evidence DAGs, signed exchange and multi-writer merge.

SQLite transactions serialize local writers. Independent clones retain their
original event DAGs on merge; no writer's history is relabeled or flattened.
Events are content-addressed and every record/object/edge must be accounted for.
A signed snapshot detects deletion relative to that snapshot, not a rewrite by
someone who controls both the database and all trusted signing keys.
"""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import html,json,os,shutil,sqlite3,tempfile,time,uuid
from cvsubstrate.provenance.io import canonical_bytes,digest,file_digest,read_json,write_json,safe_join
from cvsubstrate.errors import CVRSError
from cvsubstrate.research.claims import ScientificClaim,EvidenceAttempt,IndependenceAttestation,EvidenceEdge,ActorIdentity

FORMAT='cvrs-research-exchange/2.0'
KINDS={'claim':ScientificClaim,'attempt':EvidenceAttempt,'review':IndependenceAttestation,'actor':ActorIdentity}

class FederatedRegistry:
    def __init__(self,root):
        from cvsubstrate.provenance.artifact_set import assert_not_inside_sealed
        if Path(root).is_symlink():raise ValueError('registry root symlink refused')
        self.root=Path(root).resolve();assert_not_inside_sealed(self.root);self.root.mkdir(parents=True,exist_ok=True);self.objects=self.root/'objects';self.objects.mkdir(exist_ok=True)
        if self.root.is_symlink() or self.objects.is_symlink():raise ValueError('registry symlinks refused')
        self.db=sqlite3.connect(self.root/'registry-v2.sqlite',timeout=30,isolation_level=None);self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA foreign_keys=ON');self.db.execute('PRAGMA busy_timeout=30000')
        self.db.executescript("""CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY,kind TEXT NOT NULL,payload TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS objects(id TEXT PRIMARY KEY,bytes INTEGER NOT NULL);
          CREATE TABLE IF NOT EXISTS edges(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS signatures(id TEXT PRIMARY KEY,subject TEXT NOT NULL,payload TEXT NOT NULL);""")
        with self.transaction():
            self.db.execute('INSERT OR IGNORE INTO meta VALUES(?,?)',('format',FORMAT))
            if self.db.execute('SELECT value FROM meta WHERE key="format"').fetchone()[0]!=FORMAT:raise ValueError('unsupported registry format')
            self.db.execute('INSERT OR IGNORE INTO meta VALUES(?,?)',('writer_id',uuid.uuid4().hex))
        self.writer=self.db.execute('SELECT value FROM meta WHERE key="writer_id"').fetchone()[0]
    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:yield;self.db.execute('COMMIT')
        except BaseException:self.db.execute('ROLLBACK');raise
    def close(self):self.db.close()
    def __enter__(self):return self
    def __exit__(self,*a):self.close()
    def _heads(self):
        ids=set();parents=set()
        for row in self.db.execute('SELECT id,payload FROM events'):
            ids.add(row['id']);parents.update(json.loads(row['payload'])['parents'])
        return sorted(ids-parents)
    def _event(self,operation,subjects):
        e={'format':'cvrs-event-dag/1.0','writer_id':self.writer,'parents':self._heads(),
           'operation':operation,'subjects':sorted(subjects),'nonce':uuid.uuid4().hex,'at_unix_ns':time.time_ns()}
        eid=digest(e);self.db.execute('INSERT INTO events VALUES(?,?)',(eid,canonical_bytes(e).decode()));return eid
    @staticmethod
    def record_id(kind,payload):return digest({'kind':kind,'payload':payload})
    def get(self,rid,kind=None):
        r=self.db.execute('SELECT kind,payload FROM records WHERE id=?',(rid,)).fetchone()
        if not r:raise CVRSError('RECORD_MISSING',str(rid))
        payload=json.loads(r['payload'])
        if self.record_id(r['kind'],payload)!=rid:raise CVRSError('REGISTRY_INTEGRITY','record content changed')
        if kind and kind!=r['kind']:raise ValueError('record kind differs')
        return {'id':rid,'kind':r['kind'],'payload':payload}
    def _check_payload(self,kind,payload,lookup=None,object_lookup=None):
        lookup=lookup or self.get;object_lookup=object_lookup or self.object_path
        if kind in KINDS:payload=KINDS[kind].model_validate(payload).model_dump(mode='json')
        elif kind not in {'artifact','legacy_record','evaluation','run','environment','benchmark'}:raise ValueError('unsupported record kind')
        if kind=='attempt':
            a=EvidenceAttempt.model_validate(payload);c=ScientificClaim.model_validate(lookup(a.claim_id,'claim')['payload'])
            if a.scope_fingerprint!=c.scope_fingerprint:raise ValueError('attempt belongs to a different claim scope')
            if a.purpose!=c.purpose:raise ValueError('fixture/research purposes differ')
            for sha in a.evidence.values():object_lookup(sha)
        elif kind=='review':
            v=IndependenceAttestation.model_validate(payload);a=EvidenceAttempt.model_validate(lookup(v.attempt_id,'attempt')['payload']);c=ScientificClaim.model_validate(lookup(a.claim_id,'claim')['payload'])
            if v.reviewer_id in {a.actor_id,c.author_id}:raise ValueError('self-review cannot attest independence')
            for sha in v.evidence:object_lookup(sha)
        elif kind=='actor':
            for sha in payload.get('attestation_evidence',[]):object_lookup(sha)
        elif kind=='artifact':object_lookup(payload['sha256'])
        return payload
    def add(self,kind,payload):
        with self.transaction():
            payload=self._check_payload(kind,payload);rid=self.record_id(kind,payload);text=canonical_bytes(payload).decode()
            old=self.db.execute('SELECT kind,payload FROM records WHERE id=?',(rid,)).fetchone()
            if old:
                if (old['kind'],old['payload'])!=(kind,text):raise ValueError('conflicting immutable record ID')
                return rid
            self.db.execute('INSERT INTO records VALUES(?,?,?)',(rid,kind,text));self._event('ADD_RECORD',[rid]);return rid
    def add_file(self,path):
        src=Path(path)
        if not src.is_file() or src.is_symlink():raise ValueError('regular evidence file required')
        sha=file_digest(src);dest=self.objects/sha
        with self.transaction():
            if dest.exists() and file_digest(dest)!=sha:raise CVRSError('REGISTRY_INTEGRITY','stored object corrupt')
            if not dest.exists():
                fd,tmp=tempfile.mkstemp(dir=self.objects,prefix='.incoming-');os.close(fd)
                try:
                    shutil.copyfile(src,tmp)
                    if file_digest(Path(tmp))!=sha:raise CVRSError('SOURCE_CHANGED','evidence changed during capture')
                    os.replace(tmp,dest)
                finally:Path(tmp).unlink(missing_ok=True)
            old=self.db.execute('SELECT bytes FROM objects WHERE id=?',(sha,)).fetchone()
            if old and old[0]!=dest.stat().st_size:raise ValueError('object identity/size conflict')
            if not old:self.db.execute('INSERT INTO objects VALUES(?,?)',(sha,dest.stat().st_size));self._event('ADD_OBJECT',[sha])
        return sha
    def add_json(self,value):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'evidence.json';write_json(p,value);return self.add_file(p)
    def object_path(self,sha):
        if not isinstance(sha,str) or len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha):raise ValueError('invalid evidence SHA')
        row=self.db.execute('SELECT bytes FROM objects WHERE id=?',(sha,)).fetchone();p=self.objects/sha
        if row is None or p.is_symlink() or not p.is_file() or p.stat().st_size!=row[0] or file_digest(p)!=sha:raise CVRSError('REGISTRY_INTEGRITY','missing or altered object')
        return p
    def add_edge(self,value):
        edge=EvidenceEdge.model_validate(value);payload=edge.model_dump(mode='json');eid=digest(payload)
        with self.transaction():
            self.get(edge.source);self.get(edge.target)
            for sha in edge.evidence:self.object_path(sha)
            graph={}
            for r in self.db.execute('SELECT payload FROM edges'):
                e=json.loads(r[0]);graph.setdefault(e['source'],[]).append(e['target'])
            todo=[edge.target];seen=set()
            while todo:
                x=todo.pop()
                if x==edge.source:raise ValueError('evidence graph cycle')
                if x in seen:continue
                seen.add(x);todo.extend(graph.get(x,[]))
            if not self.db.execute('SELECT 1 FROM edges WHERE id=?',(eid,)).fetchone():
                self.db.execute('INSERT INTO edges VALUES(?,?)',(eid,canonical_bytes(payload).decode()));self._event('ADD_EDGE',[eid])
        return eid
    def sign_record(self,rid,key_path,*,password=None):
        from cvsubstrate.research.signing import sign_payload
        record=self.get(rid);sig=sign_payload(record,key_path,password=password);sid=digest(sig)
        with self.transaction():
            if not self.db.execute('SELECT 1 FROM signatures WHERE id=?',(sid,)).fetchone():
                self.db.execute('INSERT INTO signatures VALUES(?,?,?)',(sid,rid,canonical_bytes(sig).decode()));self._event('ADD_SIGNATURE',[sid])
        return sig
    def records(self,kind=None):
        query='SELECT id FROM records'+(' WHERE kind=?' if kind else '')+' ORDER BY id'
        return [self.get(r[0]) for r in self.db.execute(query,(kind,) if kind else ())]
    def snapshot(self):
        records=self.records();edges=[{'id':r[0],'payload':json.loads(r[1])} for r in self.db.execute('SELECT id,payload FROM edges ORDER BY id')]
        events=[{'id':r[0],'payload':json.loads(r[1])} for r in self.db.execute('SELECT id,payload FROM events ORDER BY id')]
        objects=[{'id':r[0],'bytes':r[1]} for r in self.db.execute('SELECT id,bytes FROM objects ORDER BY id')]
        signatures=[{'id':r[0],'subject':r[1],'payload':json.loads(r[2])} for r in self.db.execute('SELECT id,subject,payload FROM signatures ORDER BY id')]
        body={'format':FORMAT,'records':records,'edges':edges,'objects':objects,'events':events,'signatures':signatures,'heads':self._heads()}
        return {**body,'root_digest':digest(body)}
    @staticmethod
    def validate_snapshot(s,object_root=None,*,verify_signatures=True):
        if s.get('format')!=FORMAT:raise ValueError('snapshot format unsupported')
        body={k:v for k,v in s.items() if k!='root_digest'}
        if digest(body)!=s.get('root_digest'):raise CVRSError('REGISTRY_INTEGRITY','snapshot root changed')
        tables={}
        for name in ['records','edges','objects','events','signatures']:
            rows=s.get(name,[]);table={x['id']:x for x in rows}
            if len(table)!=len(rows):raise ValueError('duplicate '+name+' identity')
            tables[name]=table
        records=tables['records'];objects=tables['objects'];edges=tables['edges'];events=tables['events'];sigs=tables['signatures']
        for rid,r in records.items():
            if FederatedRegistry.record_id(r['kind'],r['payload'])!=rid:raise ValueError('record identity conflict')
            if r['kind'] in KINDS:KINDS[r['kind']].model_validate(r['payload'])
        for oid,o in objects.items():
            if len(oid)!=64 or any(x not in '0123456789abcdef' for x in oid) or o['bytes']<0:raise ValueError('invalid object descriptor')
            if object_root:
                p=safe_join(Path(object_root),oid)
                if p.is_symlink() or not p.is_file() or p.stat().st_size!=o['bytes'] or file_digest(p)!=oid:raise ValueError('missing/changed exchanged object')
        references=[]
        for r in records.values():
            p=r['payload']
            if r['kind']=='attempt':
                if p['claim_id'] not in records or records[p['claim_id']]['kind']!='claim':raise ValueError('dangling attempt')
                c=ScientificClaim.model_validate(records[p['claim_id']]['payload'])
                if p['scope_fingerprint']!=c.scope_fingerprint or p['purpose']!=c.purpose:raise ValueError('attempt scope/purpose mismatch')
                references.extend(p['evidence'].values())
            if r['kind']=='review':
                if p['attempt_id'] not in records or records[p['attempt_id']]['kind']!='attempt':raise ValueError('dangling review')
                a=records[p['attempt_id']]['payload'];c=records[a['claim_id']]['payload']
                if p['reviewer_id'] in {a['actor_id'],c['author_id']}:raise ValueError('self independence review')
                references.extend(p['evidence'])
            if r['kind']=='artifact':references.append(p['sha256'])
            if r['kind']=='actor':references.extend(p.get('attestation_evidence',[]))
        graph={}
        for eid,row in edges.items():
            e=EvidenceEdge.model_validate(row['payload'])
            if digest(e)!=eid or e.source not in records or e.target not in records:raise ValueError('invalid/dangling edge')
            references.extend(e.evidence);graph.setdefault(e.source,[]).append(e.target)
        if set(references)-set(objects):raise ValueError('dangling evidence reference')
        def acyclic(graph):
            done=set();active=set()
            def visit(k):
                if k in active:raise ValueError('cycle in graph')
                if k in done:return
                active.add(k)
                for v in graph.get(k,[]):visit(v)
                active.remove(k);done.add(k)
            for k in graph:visit(k)
        acyclic(graph)
        accounted={'ADD_RECORD':set(),'ADD_EDGE':set(),'ADD_OBJECT':set(),'ADD_SIGNATURE':set()};parents=set();event_graph={}
        for eid,row in events.items():
            e=row['payload']
            if digest(e)!=eid or e.get('format')!='cvrs-event-dag/1.0' or e['operation'] not in accounted:raise ValueError('invalid event')
            if len(set(e['parents']))!=len(e['parents']) or set(e['parents'])-set(events):raise ValueError('dangling/duplicate event parents')
            parents.update(e['parents']);event_graph[eid]=e['parents'];accounted[e['operation']].update(e['subjects'])
        acyclic(event_graph)
        if sorted(set(events)-parents)!=s['heads']:raise ValueError('event heads mismatch')
        for operation,ids in [('ADD_RECORD',records),('ADD_EDGE',edges),('ADD_OBJECT',objects),('ADD_SIGNATURE',sigs)]:
            if accounted[operation]!=set(ids):raise ValueError('deleted/injected '+operation+' not covered by event history')
        for sid,row in sigs.items():
            if digest(row['payload'])!=sid or row['subject'] not in records:raise ValueError('signature identity/subject conflict')
            if verify_signatures:
                from cvsubstrate.research.signing import verify_signature
                verify_signature(records[row['subject']],row['payload'])
        return {'status':'VERIFIED','root_digest':s['root_digest'],'records':len(records),'objects':len(objects),'edges':len(edges),'events':len(events),'signature_checks':len(sigs) if verify_signatures else 'NOT_RUN'}
    def verify(self):
        if self.db.in_transaction:return self.validate_snapshot(self.snapshot(),self.objects)
        with self.transaction():return self.validate_snapshot(self.snapshot(),self.objects)
    def exchange(self,output,*,signing_key=None,password=None):
        out=Path(output)
        if out.exists():raise ValueError('new exchange destination required')
        # Snapshot is transaction-consistent even if another process writes concurrently.
        with self.transaction():s=self.snapshot();self.validate_snapshot(s,self.objects)
        out.mkdir(parents=True);(out/'objects').mkdir()
        for o in s['objects']:shutil.copyfile(self.object_path(o['id']),out/'objects'/o['id'])
        write_json(out/'exchange.json',s)
        if signing_key:
            from cvsubstrate.research.signing import sign_payload
            write_json(out/'exchange-signature.json',sign_payload(s,signing_key,password=password))
        self.validate_snapshot(read_json(out/'exchange.json'),out/'objects');return s['root_digest']
    def merge(self,exchange,*,trusted_keys=None,require_signature=False):
        path=Path(exchange);incoming=read_json(path/'exchange.json');self.validate_snapshot(incoming,path/'objects')
        if require_signature or (path/'exchange-signature.json').exists():
            if not (path/'exchange-signature.json').is_file():raise ValueError('signed exchange required')
            from cvsubstrate.research.signing import verify_signature
            sig=verify_signature(incoming,read_json(path/'exchange-signature.json'),trusted_keys=trusted_keys or [])
            if require_signature and not sig['trusted_key']:raise ValueError('exchange key is not trusted by caller')
        with self.transaction():
            current=self.snapshot();self.validate_snapshot(current,self.objects)
            merged={'format':FORMAT}
            for name in ['records','edges','objects','events','signatures']:
                values={x['id']:x for x in current[name]}
                for x in incoming[name]:
                    if x['id'] in values and values[x['id']]!=x:raise CVRSError('REGISTRY_CONFLICT','same ID has different immutable content')
                    values[x['id']]=x
                merged[name]=sorted(values.values(),key=lambda x:x['id'])
            ids={e['id'] for e in merged['events']};parents={p for e in merged['events'] for p in e['payload']['parents']};merged['heads']=sorted(ids-parents);merged['root_digest']=digest(merged)
            # Combined graph can introduce a cycle even if each input was valid.
            self.validate_snapshot(merged,verify_signatures=True)
            for o in incoming['objects']:
                dst=self.objects/o['id']
                if dst.exists() and file_digest(dst)!=o['id']:raise ValueError('existing evidence object corrupt')
                if not dst.exists():
                    tmp=self.objects/('.merge-'+uuid.uuid4().hex);shutil.copyfile(path/'objects'/o['id'],tmp)
                    if file_digest(tmp)!=o['id']:tmp.unlink();raise ValueError('source exchange changed during merge')
                    os.replace(tmp,dst)
                self.db.execute('INSERT OR IGNORE INTO objects VALUES(?,?)',(o['id'],o['bytes']))
            for r in incoming['records']:self.db.execute('INSERT OR IGNORE INTO records VALUES(?,?,?)',(r['id'],r['kind'],canonical_bytes(r['payload']).decode()))
            for r in incoming['edges']:self.db.execute('INSERT OR IGNORE INTO edges VALUES(?,?)',(r['id'],canonical_bytes(r['payload']).decode()))
            for r in incoming['events']:self.db.execute('INSERT OR IGNORE INTO events VALUES(?,?)',(r['id'],canonical_bytes(r['payload']).decode()))
            for r in incoming['signatures']:self.db.execute('INSERT OR IGNORE INTO signatures VALUES(?,?,?)',(r['id'],r['subject'],canonical_bytes(r['payload']).decode()))
        return self.verify()
    def status(self,claim_id):
        claim=ScientificClaim.model_validate(self.get(claim_id,'claim')['payload']);attempts=[r for r in self.records('attempt') if r['payload']['claim_id']==claim_id]
        originals=[];original_run_ids=set()
        for r in attempts:
            payload=r['payload']
            if payload['role']!='original' or payload['outcome']!='completed':continue
            sha=payload['evidence'].get('execution')
            if not sha:continue
            receipt=read_json(self.object_path(sha))
            if receipt.get('status')!='SUCCEEDED' or not receipt.get('run_id') or receipt.get('scope_fingerprint')!=claim.scope_fingerprint:continue
            originals.append(r);original_run_ids.add(receipt['run_id'])
        results=[]
        for r in attempts:
            a=EvidenceAttempt.model_validate(r['payload']);result={'id':r['id'],'role':a.role,'outcome':a.outcome,'level':'R0','assertion':a.effect.assess(claim) if a.effect else None,'limitations':[]}
            if a.evidence:result['level']='R1'
            if a.role!='reproduction' or a.outcome!='completed':results.append(result);continue
            sha=a.evidence.get('execution');execution=read_json(self.object_path(sha)) if sha else {}
            evaluation_sha=a.evidence.get('evaluation');evaluation=read_json(self.object_path(evaluation_sha)) if evaluation_sha else {}
            run_id=execution.get('run_id')
            if execution.get('status')!='SUCCEEDED' or not run_id or run_id in original_run_ids:
                result['limitations'].append('no distinct successful execution receipt');results.append(result);continue
            if execution.get('scope_fingerprint')!=claim.scope_fingerprint:result['limitations'].append('execution scope mismatch');results.append(result);continue
            if not originals:
                result['limitations'].append('no original execution to reproduce');results.append(result);continue
            result['level']='R2'
            if evaluation.get('run_id')!=run_id or evaluation.get('metric')!=claim.metric or evaluation.get('effect_digest')!=digest(a.effect):
                result['limitations'].append('evaluation receipt does not bind this run/effect');results.append(result);continue
            reference_effects=[EvidenceAttempt.model_validate(o['payload']).effect for o in originals if o['payload'].get('effect')]
            if not any(abs(a.effect.baseline-e.baseline)<=claim.reproduction_tolerance and abs(a.effect.treatment-e.treatment)<=claim.reproduction_tolerance for e in reference_effects):
                result['limitations'].append('observed metrics did not reproduce an original effect within the declared tolerance');results.append(result);continue
            result['level']='R3'
            reviews=[IndependenceAttestation.model_validate(x['payload']) for x in self.records('review') if x['payload']['attempt_id']==r['id']]
            honest=[v for v in reviews if v.independent_operator and v.independent_machine and all(a.actor_id!=o['payload']['actor_id'] and a.machine_id!=o['payload']['machine_id'] for o in originals)]
            if honest and originals:result['level']='R4'
            if result['level']=='R4' and any(v.independent_implementation for v in honest) and originals and all(a.implementation_id!=o['payload']['implementation_id'] for o in originals):
                original_assertions={EvidenceAttempt.model_validate(o['payload']).effect.assess(claim)['assertion'] for o in originals if o['payload'].get('effect')}
                if result['assertion']['assertion'] in original_assertions:result['level']='R5'
            result['limitations'].append('levels are evidence-scoped; signatures/attestations do not prove scientific truth or independent identity')
            results.append(result)
        return {'claim_id':claim_id,'scope_fingerprint':claim.scope_fingerprint,'level':max((r['level'] for r in results),default='R0'),'attempts':results}
    def search(self,*,kind=None,filters=None,minimum_level=None):
        if minimum_level is not None and minimum_level not in {'R0','R1','R2','R3','R4','R5'}:raise ValueError('unknown reproduction level')
        rows=self.records(kind);filters=filters or {};selected=[]
        def value(obj,path):
            for key in path.split('.'):
                if not isinstance(obj,dict):return None
                obj=obj.get(key)
            return obj
        for r in rows:
            if any(value(r['payload'],key)!=v for key,v in filters.items()):continue
            if minimum_level and (r['kind']!='claim' or self.status(r['id'])['level']<minimum_level):continue
            selected.append(r)
        return selected
    def export_site(self,output):
        out=Path(output)
        if out.exists():raise ValueError('new static output required')
        with self.transaction():
            s=self.snapshot();self.validate_snapshot(s,self.objects)
            statuses={r['id']:self.status(r['id']) for r in s['records'] if r['kind']=='claim'}
        out.mkdir(parents=True);write_json(out/'registry.json',s)
        esc=lambda x:html.escape(str(x),quote=True)
        links=[]
        for r in s['records']:
            title=r['payload'].get('title',r['kind']+' '+r['id'][:12]);links.append(f'<li><a href="{r["id"]}.html">{esc(title)}</a> ({esc(r["kind"])})</li>')
            relations=[x for x in s['edges'] if r['id'] in {x['payload']['source'],x['payload']['target']}]
            status=statuses.get(r['id'])
            body='<h1>'+esc(title)+'</h1><pre>'+esc(json.dumps(r,indent=2))+'</pre><h2>Evidence lineage</h2><pre>'+esc(json.dumps(relations,indent=2))+'</pre>'
            if status:body+='<h2>Reproduction attempts</h2><pre>'+esc(json.dumps(status,indent=2))+'</pre>'
            (out/(r['id']+'.html')).write_text('<!doctype html><meta charset="utf-8"><title>'+esc(title)+'</title>'+body,encoding='utf-8')
        (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>CVRS research registry</title><h1>Research registry</h1><p>Evidence-scoped local records. Identity and scientific truth are not authenticated by this page.</p><ul>'+''.join(links)+'</ul>',encoding='utf-8')
        return {'pages':len(links)+1,'root_digest':s['root_digest']}

def migrate_registry_v1(source,destination):
    """Lossless legacy records/history capture; never invent structured claim semantics."""
    from cvsubstrate.research.registry import ResearchRegistry
    with ResearchRegistry(source) as old:
        check=old.verify();records=old.list()
        if check.get('status')!='VERIFIED':raise ValueError('legacy registry must verify')
        with FederatedRegistry(destination) as new:
            with tempfile.TemporaryDirectory() as tmp:
                backup=Path(tmp)/'legacy.sqlite';dest=sqlite3.connect(backup);old.db.backup(dest);dest.close();source_db=new.add_file(backup)
            mapping={}
            for row in old.db.execute('SELECT sha FROM objects'):new.add_file(old.object_path(row[0]))
            for record in records:mapping[record['id']]=new.add('legacy_record',{'original_format':'cvrs-research-registry/1.0','original_record':record,'source_registry_sha256':source_db,'level_not_promoted':True})
            write_json(Path(destination)/'migration.json',{'legacy_verification':check,'record_mapping':mapping,'source_sha256':source_db,'semantic_conversion':'NONE; preserved legacy records'})
            return {'records':len(mapping),'verification':new.verify(),'mapping':mapping}
