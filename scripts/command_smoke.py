"""Run the installed package's documented CPU flow in a fresh output directory."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

p=argparse.ArgumentParser()
p.add_argument('destination',type=Path)
p.add_argument('--worker-python',default=sys.executable)
a=p.parse_args()
if a.destination.exists() and any(a.destination.iterdir()):raise SystemExit('output directory must be absent or empty')
commands=[['doctor'],['demo',str(a.destination),'--worker-python',a.worker_python]]
results=[]
for args in commands:
    r=subprocess.run([sys.executable,'-m','cvsubstrate',*args],check=True,capture_output=True,text=True)
    results.append({'command':args,'result':json.loads(r.stdout)})
print(json.dumps(results,indent=2))
