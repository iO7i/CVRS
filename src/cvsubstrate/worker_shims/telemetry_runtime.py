"""Native training observations, stdlib-only until a framework hook is installed.

Single-rank event files avoid pretending a rank-zero ledger covers distributed
training. Batch events mean samples reached the model, not that a gradient was
successfully applied. Actual optimizer step calls are separate observations.
"""
from __future__ import annotations
import contextlib
import functools
import hashlib
import inspect
import json
import os
import sqlite3
import time
from pathlib import Path

def _json(x): return json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False)

def _scalar(x):
    if hasattr(x, 'item'): return x.item()
    return x

class TrainingLedger:
    def __init__(self, path, *, run_id, rank=0, source_map=None, mixing_policy='unobserved', resume=False, world_size=None, sampler_shard=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and not resume: raise ValueError('TELEMETRY_EXISTS: use a new ledger or explicit resume')
        self.db = sqlite3.connect(self.path)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY,v TEXT); CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY,payload TEXT,hash TEXT);')
        self.world_size=None if world_size is None else int(world_size);self.sampler_shard=sampler_shard
        if int(rank)<0 or self.world_size is not None and (self.world_size<1 or int(rank)>=self.world_size):raise ValueError('rank/world_size invalid')
        self.source_map = source_map or {}
        self.run_id, self.rank, self.mixing_policy = str(run_id), int(rank), mixing_policy
        identity = _json({'run':run_id,'rank':rank,'source_map':self.source_map,'mixing_policy':mixing_policy,'world_size':self.world_size,'sampler_shard':sampler_shard})
        old = self.db.execute("SELECT v FROM meta WHERE k='identity'").fetchone()
        if old and old[0] != identity: raise ValueError('TELEMETRY_IDENTITY: resume identity changed')
        self.db.execute("INSERT OR IGNORE INTO meta VALUES('identity',?)", (identity,)); self.db.commit()
        self.emit('SESSION_STARTED', {'resumed':bool(old),'world_size':self.world_size,'sampler_shard':sampler_shard})

    def emit(self, kind, data):
        with self.db:
            row=self.db.execute('SELECT seq,hash FROM events ORDER BY seq DESC LIMIT 1').fetchone()
            seq,prev=(row[0]+1,row[1]) if row else (0,'0'*64)
            payload={'seq':seq,'kind':kind,'run_id':self.run_id,'rank':self.rank,'monotonic_ns':time.monotonic_ns(),'previous':prev,'data':data}
            text=_json(payload); h=hashlib.sha256(text.encode()).hexdigest()
            self.db.execute('INSERT INTO events VALUES(?,?,?)',(seq,text,h))
        return seq

    def batch(self, identities, *, batch_id=None, epoch=None, contribution_ids=None, parent_ids=None, augmentation=None):
        ids=[str(_scalar(x)) for x in identities]
        if not ids: raise ValueError('EMPTY_BATCH: no sample identity observed')
        members=[]
        for sid in ids:
            v=self.source_map.get(sid)
            if v is None: v={'sample_id':sid,'source':'unknown'}
            elif isinstance(v,str): v={'sample_id':sid,'source':v}
            source=v.get('source','unknown')
            if source not in {'real','synthetic','unknown'}: raise ValueError('invalid source kind')
            members.append({'native_id':sid,'sample_id':str(v.get('sample_id',sid)),'source':source})
        return self.emit('MODEL_BATCH',{'batch_id':batch_id,'epoch':epoch,'members':members,
            'contribution_ids':contribution_ids,'mixing_policy':self.mixing_policy,
            'parent_ids':parent_ids,'augmentation':augmentation or {},'world_size':self.world_size,
            'meaning':'observed model inputs, not attributed gradient contribution'})

    def optimizer(self, name='optimizer', learning_rates=None):
        rates=[float(_scalar(x)) for x in (learning_rates or [])]
        if any(not __import__('math').isfinite(x) for x in rates):raise ValueError('nonfinite learning-rate observation')
        return self.emit('OPTIMIZER_STEP',{'optimizer':name,'learning_rates':rates,'meaning':'optimizer.step returned; AMP-skipped calls do not trigger this hook'})

    def loss(self,components,learning_rates=None):
        values={}
        for key,value in components.items():
            if hasattr(value,'detach'):value=value.detach()
            if hasattr(value,'numel') and value.numel()!=1:continue
            if isinstance(value,(int,float)) or hasattr(value,'item'):
                value=float(_scalar(value))
                if not __import__('math').isfinite(value):raise ValueError('nonfinite loss observation')
                values[str(key)]=value
        return self.emit('LOSS',{'components':values,'learning_rates':learning_rates or [],'gradient_contribution':'NOT_MEASURED'})

    def checkpoint(self,path,step=None):
        h=hashlib.sha256()
        with open(path,'rb') as f:
            for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
        return self.emit('CHECKPOINT',{'sha256':h.hexdigest(),'optimizer_step':step})

    def epoch(self, epoch, sampler=None):
        return self.emit('EPOCH',{'epoch':int(epoch),'sampler':sampler or 'unobserved'})

    def summary(self):
        counts={'real':0,'synthetic':0,'unknown':0};batches=steps=0;per_sample={};prev='0'*64
        for seq,text,h in self.db.execute('SELECT seq,payload,hash FROM events ORDER BY seq'):
            event=json.loads(text)
            if not isinstance(event,dict) or event.get('seq')!=seq or event.get('previous')!=prev or hashlib.sha256(text.encode()).hexdigest()!=h:
                raise ValueError('TELEMETRY_INTEGRITY: ledger changed')
            prev=h
            if event['kind']=='MODEL_BATCH':
                batches+=1
                for m in event['data']['members']:
                    counts[m['source']]+=1;sid=m['sample_id'];per_sample[sid]=per_sample.get(sid,0)+1
            if event['kind']=='OPTIMIZER_STEP':steps+=1
        exact=self.mixing_policy=='disabled_or_fully_traced' and counts['unknown']==0 and batches>0
        return {'run_id':self.run_id,'rank':self.rank,'model_batches':batches,'optimizer_step_calls':steps,
            'source_exposures':counts,'sample_exposures':per_sample,'repeat_exposures':sum(max(0,n-1) for n in per_sample.values()),
            'source_accounting':'OBSERVED' if exact else 'PARTIAL','mixing_policy':self.mixing_policy,'head_sha256':prev,
            'gradient_contribution_per_source':'NOT_MEASURED','rank_aggregation':'single rank only','world_size':getattr(self,'world_size',None),'sampler_shard':getattr(self,'sampler_shard',None)}

    def export(self, destination):
        destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
        with (destination/'training-events.jsonl').open('w',encoding='utf-8') as f:
            for payload,h in self.db.execute('SELECT payload,hash FROM events ORDER BY seq'):
                f.write(_json({'event':json.loads(payload),'sha256':h})+'\n')
        result=self.summary();(destination/'training-summary.json').write_text(_json(result)+'\n')
        return result

    def close(self):
        self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');self.db.close()

@contextlib.contextmanager
def observe_optimizer(optimizer, ledger, name='optimizer'):
    """Observe actual steps, not framework callback names that may never fire."""
    def observed():
        ledger.optimizer(name,[group['lr'] for group in getattr(optimizer,'param_groups',[]) if 'lr' in group])
    if hasattr(optimizer,'register_step_post_hook'):
        handle=optimizer.register_step_post_hook(lambda *a,**k: observed())
        try: yield
        finally: handle.remove()
    else:
        old=optimizer.step
        @functools.wraps(old)
        def step(*a,**k):
            result=old(*a,**k);observed();return result
        optimizer.step=step
        try: yield
        finally: optimizer.step=old

class ObservedLoader:
    """Loader-yield telemetry, not claimed model consumption; use model hooks below."""
    def __init__(self,loader,ledger,extract):self.loader,self.ledger,self.extract=loader,ledger,extract
    def __len__(self):return len(self.loader)
    def __getattr__(self,key):return getattr(self.loader,key)
    def __iter__(self):
        for batch in self.loader:
            self.ledger.emit('LOADER_YIELD',{'ids':[str(_scalar(x)) for x in self.extract(batch)]})
            yield batch

class UltralyticsTelemetry:
    def __init__(self, ledger): self.ledger,self.cleanups=ledger,[]
    def start(self, trainer):
        if int(os.environ.get('WORLD_SIZE','1')) != 1:
            raise RuntimeError('TELEMETRY_DISTRIBUTED: use explicit per-rank integration; this recipe is single-process')
        old=trainer.preprocess_batch;pending={}
        @functools.wraps(old)
        def preprocess(batch):
            result=old(batch)
            ids=result.get('im_file')
            if ids is None: raise RuntimeError('TELEMETRY_BATCH_ID: native batch omitted im_file')
            pending['batch']=result
            return result
        trainer.preprocess_batch=preprocess
        self.cleanups.append(lambda:setattr(trainer,'preprocess_batch',old))
        def before_forward(mod,args,kwargs):
            value=args[0] if args else kwargs.get('x')
            if isinstance(value,dict):batch=value
            else:
                batch=pending.get('batch')
                if batch is None or value is not batch.get('img'):
                    raise RuntimeError('TELEMETRY_MODEL_BATCH: cannot tie actual model input to native image identities')
            ids=batch.get('im_file')
            if ids is None:raise RuntimeError('TELEMETRY_MODEL_ID: consumed batch has no im_file')
            self.ledger.batch(ids,epoch=int(trainer.epoch),parent_ids=batch.get('cvrs_parent_ids'),augmentation=batch.get('cvrs_augmentation'));pending.clear()
        handle=trainer.model.register_forward_pre_hook(before_forward,with_kwargs=True)
        self.cleanups.append(handle.remove)
        cm=observe_optimizer(trainer.optimizer,self.ledger);cm.__enter__();self.cleanups.append(lambda:cm.__exit__(None,None,None))
    def close(self):
        for cleanup in reversed(self.cleanups):cleanup()
        self.cleanups=[]
    def attach(self, model):
        model.add_callback('on_train_start',self.start)
        model.add_callback('on_train_epoch_start',lambda t:self.ledger.epoch(t.epoch,type(getattr(t.train_loader,'sampler',None)).__name__))

@contextlib.contextmanager
def observe_rfdetr(ledger):
    """Instrument RF-DETR's native train_one_epoch, not its model implementation.
    Requires named model/optimizer/data_loader arguments; unsupported revisions fail.
    Targets are observed by the training model's pre-forward hook, after microbatching.
    """
    import rfdetr.engine as engine
    import sys
    original=engine.train_one_epoch;signature=inspect.signature(original)
    if not {'model','optimizer','data_loader'} <= set(signature.parameters):
        raise RuntimeError('RFDETR_TELEMETRY_API: unsupported native training signature')
    @functools.wraps(original)
    def epoch(*args,**kwargs):
        bound=signature.bind(*args,**kwargs);bound.apply_defaults();values=bound.arguments
        model=values['model'];optimizer=values['optimizer'];ledger.epoch(values.get('epoch',0))
        def pre(mod,args,kwargs):
            targets=kwargs.get('targets',args[1] if len(args)>1 else None)
            if targets is None: raise RuntimeError('RFDETR_TELEMETRY_TARGETS: model did not receive target identities')
            ledger.batch([t['image_id'] for t in targets],epoch=int(values.get('epoch',0)))
        hook=model.register_forward_pre_hook(pre,with_kwargs=True)
        try:
            with observe_optimizer(optimizer,ledger):return original(*args,**kwargs)
        finally:hook.remove()
    # Patch imported aliases as well as the defining module, and restore all.
    slots=[]
    for name,module in list(sys.modules.items()):
        if name.startswith('rfdetr') and module:
            for key,value in list(vars(module).items()):
                if value is original:slots.append((module,key));setattr(module,key,epoch)
    try:yield
    finally:
        for module,key in slots:setattr(module,key,original)

def mm_sample_ids(data):
    """Read MM2 img_metas or MM3 data_samples without importing either stack."""
    values=data.get('data_samples',data.get('img_metas',[]))
    result=[]
    def walk(x):
        if isinstance(x,(list,tuple)):
            for y in x:walk(y)
        elif isinstance(x,dict):
            identifier=x.get('img_path',x.get('filename',x.get('img_id')))
            if identifier is None: raise RuntimeError('MM_TELEMETRY_ID: identity missing')
            result.append(identifier)
        elif hasattr(x,'metainfo'):walk(x.metainfo)
        elif hasattr(x,'data'):walk(x.data)
        else:raise RuntimeError('MM_TELEMETRY_BATCH: unsupported data container')
    walk(values)
    if not result:raise RuntimeError('MM_TELEMETRY_BATCH: no data sample identities')
    return result

@contextlib.contextmanager
def observe_mm_runner(runner,ledger):
    model=runner.model;old=model.train_step
    @functools.wraps(old)
    def step(data,*a,**k):
        ledger.batch(mm_sample_ids(data),epoch=int(getattr(runner,'epoch',0)))
        result=old(data,*a,**k)
        components=result.get('log_vars',result) if isinstance(result,dict) else {}
        ledger.loss(components)
        return result
    model.train_step=step
    wrapper=getattr(runner,'optim_wrapper',None)
    optimizer=getattr(wrapper,'optimizer',None) or getattr(runner,'optimizer',None)
    optimizers=optimizer if isinstance(optimizer,dict) else {'optimizer':optimizer}
    with contextlib.ExitStack() as stack:
        try:
            for name,opt in optimizers.items():
                if opt is None:raise RuntimeError('MM_TELEMETRY_OPTIMIZER: optimizer unavailable')
                stack.enter_context(observe_optimizer(opt,ledger,name))
            yield
        finally:model.train_step=old
