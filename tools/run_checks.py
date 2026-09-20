"""Run the requested local test tier, retaining command, output, JUnit and exit code.

Usage: python tools/run_checks.py --suite fast --out evidence/local-fast
       python tools/run_checks.py --suite native --out evidence/local-native
No package installs, model downloads, GPU requests or external services.
"""
from pathlib import Path
import argparse
import datetime
import json
import os
import subprocess
import sys
import time


def main():
    p=argparse.ArgumentParser();p.add_argument('--suite',choices=['fast','native','all'],default='fast');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];out=a.out.resolve()
    if out.exists():p.error('verification output must be new (prior evidence is never overwritten)')
    out.mkdir(parents=True)
    cmd=[sys.executable,'-m','pytest','-q','--junitxml='+str(out/'results.xml')]
    if a.suite!='all':cmd+=['-m','not native' if a.suite=='fast' else 'native']
    env=dict(os.environ);env['PYTHONPATH']=str(root/'src');env['OMP_NUM_THREADS']='1';env['OPENBLAS_NUM_THREADS']='1';env['MKL_NUM_THREADS']='1';env.setdefault('PYTEST_DISABLE_PLUGIN_AUTOLOAD','1')
    start=time.monotonic();meta={'suite':a.suite,'command':cmd,'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cwd':str(root),'python':sys.version,'state':'RUNNING'}
    (out/'status.json').write_text(json.dumps(meta,indent=2)+'\n')
    with (out/'pytest.log').open('w') as log:proc=subprocess.run(cmd,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
    meta.update(state='COMPLETED',exit_code=proc.returncode,wall_seconds=time.monotonic()-start,finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    (out/'status.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta,indent=2))
    return proc.returncode

if __name__=='__main__':raise SystemExit(main())
