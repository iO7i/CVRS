"""An actual offline CPU workflow after dependencies are installed.

Creates random-initialized detectors and procedural data. Never labels this as
model quality, a real paper reproduction, or an independent reproduction.
"""
from pathlib import Path
import sys,time
from cvsubstrate.provenance.io import read_json,write_json,file_digest

def demo(destination,*,worker_python=None,timeout=240):
    from cvsubstrate.data.fixtures import generate
    from cvsubstrate.execution.runner import run_experiment
    from cvsubstrate.research.capture import capture_run
    from cvsubstrate.research.reevaluate import reevaluate
    from cvsubstrate.research.capsule import export_registry_capsule
    from cvsubstrate.research.registry import ResearchRegistry
    from cvsubstrate.publication.site import results_site
    root=Path(destination).resolve()
    if root.exists():raise ValueError('demo needs a new directory')
    root.mkdir();start=time.monotonic()
    try:
        generate(root/'fixture');spec=root/'fixture/real.json';v=read_json(spec);v['training']['updates']=1;write_json(spec,v)
        runs: list[Path]=[];captures: list[dict]=[]
        for index in range(2):
            p=run_experiment(spec,root/('run-'+str(index+1)),worker_python=worker_python,timeout=timeout);runs.append(p)
            cap=capture_run(root/'registry',p,root/'fixture/dataset.json',title='CPU pipeline fixture',
                question='Does the same native execution produce the same diagnostic observations?',estimand='fixture_pipeline',
                author_id='local-demo-operator',machine_id='same-demo-machine',implementation_id='native-cpu-fixture',
                existing_claim_id=captures[0]['claim_id'] if captures else None)
            captures.append(cap)
        protocol=read_json(runs[0]/'experiment.json')['evaluation'];protocol['score_threshold']=0.1
        before=file_digest(runs[0]/'predictions.jsonl')
        write_json(root/'reevaluation-protocol.json',protocol)
        reeval=reevaluate(root/'fixture/dataset.json','dev',runs[0]/'predictions.jsonl',root/'reevaluation-protocol.json',root/'reevaluation')
        if file_digest(runs[0]/'predictions.jsonl')!=before:raise RuntimeError('re-evaluation changed original output')
        with ResearchRegistry(root/'registry') as reg:reg.export(root/'registry-site')
        capsule=export_registry_capsule(root/'registry',root/'capsule',archive=root/'capsule.zip')
        results_site(runs,root/'results-site')
        result={'status':'SUCCEEDED','runs':[str(p.relative_to(root)) for p in runs],'captures':captures,
            'reevaluation':reeval,'capsule':capsule,'elapsed_seconds':time.monotonic()-start,
            'limits':'Same-machine procedural CPU fixture; not independent research, pretrained performance, or real Sim2Real.'}
        write_json(root/'demo.json',result);return result
    except BaseException as exc:
        write_json(root/'failure.json',{'status':'FAILED','error':type(exc).__name__,'message':str(exc),'elapsed_seconds':time.monotonic()-start});raise
