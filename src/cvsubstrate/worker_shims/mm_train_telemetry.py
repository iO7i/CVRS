"""Trusted upstream train.py launcher with MM2/MM3 runner telemetry hooks."""
import argparse, contextlib, importlib, os, runpy, sys
from pathlib import Path
from runtime_common import read, offline
from telemetry_runtime import TrainingLedger, observe_mm_runner

def launch():
    p=argparse.ArgumentParser();p.add_argument('--entry',required=True);p.add_argument('--telemetry-spec',required=True)
    args,rest=p.parse_known_args();spec=read(args.telemetry_spec)
    world=int(os.environ.get('WORLD_SIZE','1'));rank=int(os.environ.get('RANK','0'))
    ledger_path=Path(spec['path'])
    if world>1:ledger_path=ledger_path.with_name(ledger_path.stem+'-rank'+str(rank)+ledger_path.suffix)
    ledger=TrainingLedger(ledger_path,run_id=spec['run_id'],rank=rank,world_size=world,source_map=spec['source_map'],mixing_policy=spec.get('mixing_policy','unobserved'),sampler_shard={'rank':rank,'world_size':world})
    stack=contextlib.ExitStack();patched=[];active=set()
    module='mmcv.runner.base_runner' if spec['profile']=='mmdet2' else 'mmengine.runner.runner'
    name='BaseRunner' if spec['profile']=='mmdet2' else 'Runner'
    cls=getattr(importlib.import_module(module),name);original=cls.call_hook
    def call_hook(runner,hook,*a,**k):
        start='before_run' if spec['profile']=='mmdet2' else 'before_train'
        if hook==start and id(runner) not in active:
            stack.enter_context(observe_mm_runner(runner,ledger));active.add(id(runner))
        return original(runner,hook,*a,**k)
    cls.call_hook=call_hook
    oldargv=sys.argv
    try:
        offline();sys.argv=[args.entry,*rest]
        sys.path.insert(0,str(Path(args.entry).resolve().parents[1]))
        runpy.run_path(args.entry,run_name='__main__')
    finally:
        stack.close();cls.call_hook=original;sys.argv=oldargv
        ledger.export(Path(spec['path']).parent/('telemetry' if world==1 else 'telemetry-rank'+str(rank)));ledger.close()
if __name__=='__main__':launch()
