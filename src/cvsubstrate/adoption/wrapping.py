"""Opt-in wrapping of trusted, unchanged research repositories using argv manifests."""
from __future__ import annotations
from pathlib import Path
import re,sys,time,shutil,os
from cvsubstrate.adoption.contracts import PaperRunSpec
from cvsubstrate.adoption.common import output_tree,load_config,write_text
from cvsubstrate.adoption.inspect import inspect_repository
from cvsubstrate.provenance.io import write_json,read_json,file_digest,digest,safe_join
from cvsubstrate.provenance.artifact_set import seal_directory,verify_directory,assert_not_inside_sealed
from cvsubstrate.errors import CVRSError,public_error
from cvsubstrate.security import sanitize

TOKEN=re.compile(r'\$\{([A-Za-z0-9_.-]+)\}')

def wrap_repository(repo,destination,*,python=None,commands=None,purpose='research'):
    report=inspect_repository(repo)
    with output_tree(destination,seal=False) as out:
        operations=commands or {}
        spec=PaperRunSpec(name='paper-experiment',repo=str(Path(repo).resolve()),python=python or sys.executable,
              repository_digest=report.root_identity,operations=operations,purpose=purpose,
              unresolved=[] if operations else ['Review command candidates, set exact argv/output paths, then explicitly trust code.'])
        write_json(out/'paper.json',spec);write_json(out/'repository-report.json',report)
        write_text(out/'RUNME.md',
            '# Bring your own repository\n\nNo source code was rewritten or imported. `paper.json` is editable.\n'
            'Command candidates are not executable recipes. Select exact commands and output paths from the native repository.\n'
            'Use `${python}`, `${repo}`, `${output}`, `${inputs.NAME}` in argv tokens; no shell evaluation.\n'
            'Write outputs beneath `${output}`; existing output files are never harvested as a new run.\n'
            'Set `trust_code: true` only after reviewing all code. Run:\n\n'
            '```bash\ncvrs paper validate paper.json\ncvrs paper run paper.json --operation predict --out NEW_OUTPUT --trust\n```\n\n'
            'The repository retains its native environment and code. Dependency isolation is not a security sandbox.\n'
            'Offline settings are advisory for arbitrary trusted scripts, not an OS network firewall.\n')
    return {'status':'WRAPPED' if commands else 'REVIEW_REQUIRED','path':str(destination),
            'repository_digest':report.root_identity,'candidates':report.command_candidates,'source_modified':False}

def validate_paper(spec_path):
    spec=PaperRunSpec.model_validate(load_config(spec_path));root=Path(spec.repo)
    if not root.is_absolute():root=(Path(spec_path).resolve().parent/root).resolve()
    report=inspect_repository(root)
    issues=[]
    if report.truncated:issues.append('repository scan truncated; full source identity unavailable')
    if report.root_identity!=spec.repository_digest:issues.append('repository inputs changed since wrapping')
    if not spec.operations:issues.append('no executable operations declared')
    issues+=spec.unresolved
    for key,expected in spec.input_digests.items():
        if key not in spec.inputs:issues.append('pinned input has no binding: '+key);continue
        path=Path(spec.inputs[key]);path=path if path.is_absolute() else Path(spec_path).resolve().parent/path
        if not path.is_file() or file_digest(path)!=expected:issues.append('input hash mismatch or missing file: '+key)
    for name,cmd in spec.operations.items():
        for arg in cmd.argv:
            for key in TOKEN.findall(arg):
                if key not in {'python','repo','output'} and not(key.startswith('inputs.') and key[7:] in spec.inputs):
                    issues.append('unbound command parameter: '+key)
        if not cmd.outputs:issues.append('operation '+name+' has no observable outputs')
    return {'status':'READY' if not issues else 'NOT_READY','issues':issues,'trust_required':True,
            'repository_digest':report.root_identity,'operation_names':sorted(spec.operations)}

def run_paper(spec_path,operation,destination,*,trust=False,cancel_token=None):
    from cvsubstrate.execution.process import run_command
    spec=PaperRunSpec.model_validate(load_config(spec_path))
    if not trust or not spec.trust_code:raise CVRSError('TRUST_REQUIRED','review native code and opt in in both manifest and invocation')
    check=validate_paper(spec_path)
    if check['status']!='READY':raise CVRSError('PAPER_NOT_READY','; '.join(check['issues']))
    if operation not in spec.operations:raise CVRSError('UNSUPPORTED_OPERATION',operation)
    repo=Path(spec.repo);repo=repo if repo.is_absolute() else Path(spec_path).resolve().parent/repo
    repo=repo.resolve();out=Path(destination).resolve();assert_not_inside_sealed(out)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','use a fresh output directory')
    if out.is_relative_to(repo):raise CVRSError('OUTPUT_IN_SOURCE','execution outputs must be outside the native source tree')
    out.mkdir(parents=True);work=out/'outputs';work.mkdir()
    cmd=spec.operations[operation]
    mapping={'python':spec.python,'repo':str(repo),'output':str(work)}
    input_records={}
    for key,value in spec.inputs.items():
        path=Path(value);resolved=path if path.is_absolute() else Path(spec_path).resolve().parent/path
        if resolved.is_file():
            input_records[key]={'kind':'file','sha256':file_digest(resolved),'bytes':resolved.stat().st_size,'pinned':key in spec.input_digests}
            mapping['inputs.'+key]=str(resolved.resolve())
        elif resolved.is_dir():
            input_records[key]={'kind':'directory','status':'REQUIRES_CONTENT_MANIFEST','pinned':False};mapping['inputs.'+key]=str(resolved.resolve())
        else:
            input_records[key]={'kind':'literal_or_missing_path','declared_value_digest':digest(value),'status':'DECLARED_ONLY'};mapping['inputs.'+key]=value
    execution_identity=digest({'spec':spec,'observed_inputs':input_records})
    argv=[TOKEN.sub(lambda m:mapping[m.group(1)],x) for x in cmd.argv]
    started=time.monotonic();status='RUNNING';failure=None;records={}
    write_json(out/'execution.json',{'status':status,'operation':operation,'spec_digest':digest(spec),
       'argv':sanitize(argv),'repository_digest':spec.repository_digest,'network_policy':spec.network,
       'network_enforcement':'offline environment flags only; trusted process is not a firewall'})
    try:
        observed=run_command(argv,cmd.timeout_seconds,log=out/'process.log',cwd=repo,env=cmd.env,pass_env=tuple(cmd.env),cancel_token=cancel_token)
        for key,output_spec in cmd.outputs.items():
            p=safe_join(work,output_spec.path)
            if not p.is_file():
                if output_spec.required:raise CVRSError('OUTPUT_MISSING',key+' was not produced at its declared path')
                continue
            # Geometry validation is opt-in by declared native output kind.
            if output_spec.kind=='cvrs_hbb':
                from cvsubstrate.contracts.models import DetectionPrediction
                from cvsubstrate.provenance.io import read_jsonl
                for row in read_jsonl(p):DetectionPrediction.model_validate(row)
            elif output_spec.kind=='json':read_json(p)
            records[key]={'path':'outputs/'+output_spec.path,'kind':output_spec.kind,'sha256':file_digest(p),'bytes':p.stat().st_size}
        for key,record in input_records.items():
            if record['kind']=='file' and file_digest(Path(mapping['inputs.'+key]))!=record['sha256']:
                raise CVRSError('INPUT_MUTATED','native execution changed an observed input: '+key)
        after=inspect_repository(repo)
        if after.root_identity!=spec.repository_digest:
            raise CVRSError('SOURCE_MUTATED','native command changed observed source; inspect artifacts and re-wrap intentionally')
        status='SUCCEEDED'
    except BaseException as exc:
        status='CANCELLED' if isinstance(exc,KeyboardInterrupt) else 'FAILED'
        failure=public_error(exc) if isinstance(exc,Exception) else {'code':'CANCELLED','message':'interrupted'}
    record={'status':status,'operation':operation,'spec_digest':digest(spec),'repository_digest':spec.repository_digest,
            'argv':sanitize(argv),'outputs':records,'elapsed_seconds':time.monotonic()-started,'error':failure,
            'purpose':spec.purpose,'certification':'NOT_CLAIMED','inputs':input_records,'execution_identity':execution_identity,
            'input_closure':'PARTIAL' if any(x['kind']!='file' for x in input_records.values()) else 'OBSERVED_FILE_INPUTS'}
    write_json(out/'execution.json',record);seal_directory(out)
    return {**record,'bundle':str(out),'verification':verify_directory(out)}
