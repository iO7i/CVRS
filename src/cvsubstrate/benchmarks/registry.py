"""Local immutable benchmark identities, preregistration and submission checks."""
from pathlib import Path
from cvsubstrate.contracts.groundwork import BenchmarkSpec
from cvsubstrate.contracts.models import ExperimentSpec,DatasetManifest,CheckpointRef
from cvsubstrate.contracts.research import AccessApproval
from cvsubstrate.provenance.io import read_json,write_json,digest,file_digest,experiment_identity,safe_join
from cvsubstrate.provenance.artifact_set import verify_directory,seal_directory
from cvsubstrate.provenance.bundle import verify_bundle
from cvsubstrate.governance.ledger import Ledger,file_lock
from cvsubstrate.governance.policy import approve_final_test,final_test_report
from cvsubstrate.errors import CVRSError

def register_benchmark(spec:BenchmarkSpec|dict,registry:Path):
    b=spec if isinstance(spec,BenchmarkSpec) else BenchmarkSpec.model_validate(spec);identity=digest(b);root=Path(registry);root.mkdir(parents=True,exist_ok=True)
    with file_lock(root/'.registry.lock'):
        for p in (root/'definitions').glob('*.json') if (root/'definitions').exists() else []:
            old=BenchmarkSpec.model_validate(read_json(p))
            if (old.name,old.version)==(b.name,b.version) and digest(old)!=identity:raise CVRSError('BENCHMARK_VERSION_IMMUTABLE','changed dataset/evaluator/tiling/taxonomy requires a new version')
        target=root/'definitions'/(identity+'.json')
        if not target.exists():write_json(target,b)
        elif read_json(target)!=b.model_dump(mode='json'):raise CVRSError('ARTIFACT_INTEGRITY','benchmark definition changed')
    return {'benchmark_digest':identity,'name':b.name,'version':b.version,'definition':str(target)}

def list_benchmarks(registry):
    rows=[]
    for p in sorted((Path(registry)/'definitions').glob('*.json')):
        b=BenchmarkSpec.model_validate(read_json(p))
        if p.stem!=digest(b):raise CVRSError('ARTIFACT_INTEGRITY','registry filename/content mismatch')
        rows.append({'digest':p.stem,'name':b.name,'version':b.version,'task':b.task})
    return rows

def preregister_selection(benchmark,experiments,checkpoints,seeds,ledger:Path,*,reason,previous_seeds=None):
    b=BenchmarkSpec.model_validate(benchmark);exps=[ExperimentSpec.model_validate(e) for e in experiments];cks=[CheckpointRef.model_validate(c) for c in checkpoints]
    if not exps or not seeds or len(set(seeds))!=len(seeds) or not reason:raise ValueError('selection requires experiments, unique seeds and reason')
    if set(seeds)&set(previous_seeds or []):raise CVRSError('SEED_REUSE','confirmation seed already used for selection')
    minimum=b.seed_policy.get('minimum_fresh_seeds',1)
    if len(seeds)<minimum:raise CVRSError('SEED_POLICY','too few selected seeds')
    for e in exps:
        if e.dataset_sha256 not in b.datasets.values():raise CVRSError('BENCHMARK_VIOLATION','experiment data is outside benchmark')
        if e.evaluation.model_dump(mode='json')!=b.evaluation:raise CVRSError('BENCHMARK_VIOLATION','evaluation differs from benchmark')
        if e.seed not in seeds:raise CVRSError('BENCHMARK_VIOLATION','experiment seed is not selected')
    if {e.checkpoint.sha256 for e in exps if e.checkpoint}!={c.sha256 for c in cks}:raise ValueError('checkpoint selection must match exact experiment references')
    record={'benchmark_digest':digest(b),'experiment_digests':[experiment_identity(e) for e in exps],
        'checkpoint_digests':[c.sha256 for c in cks],'seeds':seeds,'previous_seeds':previous_seeds or [],'evaluation_digest':digest(b.evaluation),'reason':reason}
    record['selection_digest']=digest(record);l=Ledger(ledger)
    def check(rows):
        if any(r['event']=='BENCHMARK_PREREGISTERED' and r['payload'].get('selection_digest')==record['selection_digest'] for r in rows):raise CVRSError('ALREADY_REGISTERED','selection already sealed in ledger')
    event=l.consume('BENCHMARK_PREREGISTERED',record,validate=check);return {'selection':record,'event':event}

def authorize_final(benchmark,experiment,selection_digest,ledger_path,*,requested_by,reason,max_uses=1):
    b=BenchmarkSpec.model_validate(benchmark);e=ExperimentSpec.model_validate(experiment);ledger=Ledger(ledger_path)
    matches=[r for r in ledger.rows() if r['event']=='BENCHMARK_PREREGISTERED' and r['payload'].get('selection_digest')==selection_digest]
    if len(matches)!=1:raise CVRSError('PREREGISTRATION_REQUIRED','selection is not uniquely preregistered')
    selection=matches[0]['payload']
    if selection['benchmark_digest']!=digest(b) or experiment_identity(e) not in selection['experiment_digests']:raise CVRSError('SELECTION_CHANGED','experiment/benchmark differs from preregistration')
    if e.training:raise CVRSError('BENCHMARK_VIOLATION','final test cannot train')
    if b.split_roles.get(e.eval_split)!='locked_test':raise CVRSError('BENCHMARK_VIOLATION','requested split not locked test')
    # AccessApproval exact field names are fixed by the original foundation contract.
    a=AccessApproval(dataset_digest=e.dataset_sha256,experiment_digest=experiment_identity(e),split=e.eval_split,reason=reason,approved_by=requested_by,max_uses=max_uses)
    return approve_final_test(ledger,a)

def final_evaluate(benchmark_path,experiment_path,ledger_path,approval_digest,output,*,worker_python=None,evaluator_python=None,timeout=300):
    from cvsubstrate.execution.runner import run_experiment
    b=BenchmarkSpec.model_validate(read_json(benchmark_path));e=ExperimentSpec.model_validate(read_json(experiment_path))
    if e.dataset_sha256 not in b.datasets.values() or e.evaluation.model_dump(mode='json')!=b.evaluation:raise CVRSError('BENCHMARK_VIOLATION','data/protocol changed')
    m=DatasetManifest.model_validate(read_json((Path(experiment_path).parent/e.dataset).resolve()))
    if digest(m.categories)!=b.taxonomy_digest:raise CVRSError('BENCHMARK_VIOLATION','taxonomy differs')
    return run_experiment(Path(experiment_path),Path(output),worker_python,timeout,access_ledger=Ledger(Path(ledger_path)),approval_digest=approval_digest,evaluator_python=evaluator_python)

def validate_submission(benchmark,run:Path):
    b=BenchmarkSpec.model_validate(benchmark);run=Path(run);verification=verify_bundle(run)
    failures=[]
    if verification.get('status')!='VERIFIED' or verification.get('run_state')!='SUCCEEDED':failures.append('run did not verify as successful')
    for name in b.required_artifacts:
        if not safe_join(run,name).is_file():failures.append('missing required artifact '+name)
    exp=ExperimentSpec.model_validate(read_json(run/'experiment.json'))
    if exp.dataset_sha256 not in b.datasets.values():failures.append('dataset outside benchmark')
    if exp.evaluation.model_dump(mode='json')!=b.evaluation:failures.append('evaluation protocol differs')
    if exp.seed not in b.seed_policy.get('allowed_seeds',[exp.seed]):failures.append('seed outside benchmark policy')
    if exp.training and exp.dataset_sha256 not in b.allowed_training_datasets:failures.append('training dataset not explicitly allowed')
    return {'status':'VALID' if not failures else 'INVALID','benchmark_digest':digest(b),'run':str(run),'violations':failures,
        'limits':'Checks declared artifacts, not undisclosed pretraining leakage or external test accesses.'}
