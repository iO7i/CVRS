"""Single-host DAG executor with explicit inputs, immutable attempt directories,
artifact references, safe retry policy, cache identity, and failure preservation.

No shell/task-expression evaluator and no distributed scheduler. Only registered
Python action handlers run. Their code is trusted. Hardware-heavy actions default
to no cache/retry; callers cannot make non-cacheable actions cacheable by a flag.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import importlib.metadata,shutil,uuid
from cvsubstrate.contracts.groundwork import ExecutionGraph
from cvsubstrate.provenance.io import digest,file_digest,read_json,write_json,safe_join
from cvsubstrate.provenance.artifact_set import seal_directory,verify_directory
from cvsubstrate.artifacts.store import ActionCache
from cvsubstrate.events import append_event
from cvsubstrate.foundation.lifecycle import process_lock as exclusive_lock,cancellation_scope
from cvsubstrate.errors import CVRSError

@dataclass(frozen=True)
class Action:
    handler: Callable
    version: str
    cacheable: bool = False
    retry_safe: bool = False

ACTIONS:dict[str,Action]={}

def register_action(name:str,handler:Callable,*,version='1',cacheable=False,retry_safe=False):
    if name in ACTIONS:raise ValueError('duplicate action '+name)
    ACTIONS[name]=Action(handler,version,cacheable,retry_safe)

def implementation_identity():
    root=Path(__file__).parents[1]
    return digest({p.relative_to(root).as_posix():file_digest(p) for p in sorted(root.rglob('*.py'))})

def topological(graph:ExecutionGraph):
    remaining={n.id:n for n in graph.nodes};done=set();ordered=[]
    while remaining:
        ready=[n for n in remaining.values() if (set(n.depends_on)|{x.node for x in n.inputs.values() if x.node})<=done]
        if not ready:raise ValueError('cyclic graph')
        for n in ready:ordered.append(n);done.add(n.id);del remaining[n.id]
    return ordered

def execute_graph(graph:ExecutionGraph,output:Path,*,base:Path|None=None,cache_root:Path|None=None,resume=False,invalidate=None,cancel_token=None):
    from cvsubstrate.experiments.actions import install_actions
    install_actions()
    out=Path(output).resolve();base=Path(base or '.').resolve();identity=digest(graph)
    if out.exists() and not resume:raise CVRSError('OUTPUT_EXISTS','use a new graph directory or explicit resume')
    out.mkdir(parents=True,exist_ok=True);events=out/'events.jsonl';state_path=out/'state.json'
    cache=ActionCache(cache_root) if cache_root else None
    impl=implementation_identity()
    # Metadata versions, not imported ML packages. Included so stale caches cannot
    # survive dependency changes merely because source files stayed the same.
    env=digest(sorted((d.metadata.get('Name','?'),d.version) for d in importlib.metadata.distributions()))
    with exclusive_lock(out/'execution.lock'):
        state=read_json(state_path) if state_path.exists() else {'graph_digest':identity,'run_id':str(uuid.uuid4()),'nodes':{}}
        if state['graph_digest']!=identity:raise CVRSError('GRAPH_IDENTITY','resume graph differs; start a new graph')
        write_json(out/'graph.json',graph)
        append_event(events,run_id=state['run_id'],component='dag',event_type='RUN_RESUMED' if resume else 'RUN_CREATED')
        invalid=set(invalidate or [])
        if invalid-set(n.id for n in graph.nodes):raise ValueError('unknown invalidation node')
        from cvsubstrate.foundation.lifecycle import retry_allowed, Cancelled
        ordered_nodes=topological(graph)
        for n in ordered_nodes:
            if cancel_token is not None and cancel_token.cancelled:
                for pending in ordered_nodes:
                    if state['nodes'].get(pending.id,{}).get('status')!='SUCCEEDED':
                        state['nodes'][pending.id]={'status':'CANCELLED'}
                state['status']='CANCELLED';write_json(state_path,state)
                append_event(events,run_id=state['run_id'],component='dag',event_type='RUN_CANCELLED')
                return state
            deps=set(n.depends_on)|{v.node for v in n.inputs.values() if v.node}
            if deps&invalid:invalid.add(n.id)
            if any(state['nodes'].get(k,{}).get('status')!='SUCCEEDED' for k in deps):
                state['nodes'][n.id]={'status':'BLOCKED','dependencies':sorted(deps)}
                append_event(events,run_id=state['run_id'],node_id=n.id,component='dag',event_type='NODE_BLOCKED')
                write_json(state_path,state);continue
            action=ACTIONS.get(n.action)
            if not action:raise CVRSError('ACTION_UNKNOWN','unknown graph action '+n.action)
            if n.cache and not action.cacheable:raise CVRSError('CACHE_POLICY','action is not cacheable: '+n.action)
            if n.retries and not action.retry_safe:raise CVRSError('RETRY_POLICY','action is not retry-safe: '+n.action)
            input_paths={};input_ids={}
            for label,ref in n.inputs.items():
                if ref.path:
                    p=Path(ref.path);p=p if p.is_absolute() else base/p;expected=ref.sha256
                else:
                    parent=state['nodes'][ref.node]
                    reference=parent.get('outputs',{}).get(ref.artifact,ref.artifact)
                    item=parent['artifacts'].get(reference)
                    if item is None:raise CVRSError('ARTIFACT_REFERENCE','parent did not publish '+ref.artifact)
                    p=safe_join(out,parent['directory']+'/'+reference);expected=item['sha256']
                if p.is_symlink() or not p.is_file() or file_digest(p)!=expected:raise CVRSError('INPUT_INTEGRITY','graph input missing/changed: '+label)
                input_paths[label]=p.resolve();input_ids[label]=expected
            key=ActionCache.key(action=n.action,implementation_digest=impl,parameters={'version':action.version,'parameters':n.parameters},inputs=input_ids,environment=env)
            old=state['nodes'].get(n.id)
            if old and n.id in invalid:
                append_event(events,run_id=state['run_id'],node_id=n.id,component='dag',event_type='NODE_INVALIDATED',payload={'previous_key':old.get('key')})
            if old and old.get('status')=='SUCCEEDED' and old.get('key')==key and n.id not in invalid:
                v=verify_directory(safe_join(out,old['directory']))
                if v['status']!='VERIFIED':raise CVRSError('RESUME_INTEGRITY','completed node artifacts changed')
                continue
            if old and old.get('status')=='RUNNING':
                append_event(events,run_id=state['run_id'],node_id=n.id,component='dag',event_type='NODE_INTERRUPTED')
            attempt_start=len(list((out/'nodes'/n.id).glob('attempt-*'))) if (out/'nodes'/n.id).exists() else 0
            for attempt in range(n.retries+1):
                rel=f'nodes/{n.id}/attempt-{attempt_start+attempt:04d}';directory=out/rel;directory.mkdir(parents=True)
                state['nodes'][n.id]={'status':'RUNNING','key':key,'directory':rel};write_json(state_path,state)
                append_event(events,run_id=state['run_id'],node_id=n.id,component='dag',event_type='NODE_STARTED',payload={'attempt':attempt_start+attempt,'action':n.action})
                try:
                    cached=cache.get(key) if cache and n.cache and n.id not in invalid else None
                    if cached:
                        for name,a in cached['artifacts'].items():cache.store.materialize(a['sha256'],safe_join(directory,name))
                        result=cached['result']
                        append_event(events,run_id=state['run_id'],node_id=n.id,component='dag',event_type='NODE_CACHED')
                    else:
                        with cancellation_scope(cancel_token):result=action.handler(input_paths,dict(n.parameters),directory)
                        if not isinstance(result,dict):raise CVRSError('ACTION_RESULT','action must return JSON mapping')
                        write_json(directory/'result.json',result)
                    # Actions own a fresh directory. Published files must stay within it.
                    artifacts={}
                    for p in sorted(directory.rglob('*')):
                        if p.is_symlink():raise CVRSError('ARTIFACT_SYMLINK','node output symlinks refused')
                        if p.is_file():artifacts[p.relative_to(directory).as_posix()]={'sha256':file_digest(p),'bytes':p.stat().st_size}
                    outputs=result.get('outputs',{})
                    if not isinstance(outputs,dict) or any(not isinstance(k,str) or not isinstance(v,str) or v not in artifacts for k,v in outputs.items()):raise CVRSError('ACTION_OUTPUT','named outputs must reference existing owned artifact files')
                    if cancel_token is not None:cancel_token.check()
                    if cache and n.cache and not cached:
                        for name in artifacts:cache.store.put(safe_join(directory,name))
                        cache.put(key,{'result':result,'artifacts':artifacts})
                    seal_directory(directory)
                    state['nodes'][n.id]={'status':'SUCCEEDED','key':key,'directory':rel,'result':result,'artifacts':artifacts,'outputs':outputs,'cached':cached is not None}
                    append_event(events,run_id=state['run_id'],node_id=n.id,component='dag',event_type='NODE_SUCCEEDED');break
                except (KeyboardInterrupt,Cancelled):
                    state['nodes'][n.id]['status']='CANCELLED';state['status']='CANCELLED'
                    write_json(directory/'cancelled.json',{'status':'CANCELLED','partial_outputs_retained':True});seal_directory(directory);write_json(state_path,state)
                    append_event(events,run_id=state['run_id'],node_id=n.id,component='dag',event_type='RUN_CANCELLED');raise
                except Exception as exc:
                    error=exc.as_dict() if isinstance(exc,CVRSError) else {'code':type(exc).__name__,'message':str(exc)}
                    write_json(directory/'failure.json',error)
                    seal_directory(directory)
                    state['nodes'][n.id]={'status':'FAILED','key':key,'directory':rel,'error':error}
                    append_event(events,run_id=state['run_id'],node_id=n.id,component='dag',event_type='NODE_FAILED',payload=error)
                    if attempt==n.retries or not retry_allowed(exc,action_retry_safe=action.retry_safe):break
                finally:write_json(state_path,state)
            if state['nodes'][n.id]['status']=='FAILED' and not graph.continue_independent_nodes:break
        complete=all(state['nodes'].get(n.id,{}).get('status')=='SUCCEEDED' for n in graph.nodes)
        state['status']='SUCCEEDED' if complete else 'FAILED';write_json(state_path,state)
        append_event(events,run_id=state['run_id'],component='dag',event_type='RUN_SUCCEEDED' if complete else 'RUN_FAILED')
        return state
