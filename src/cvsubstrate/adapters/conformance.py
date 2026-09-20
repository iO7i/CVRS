"""External adapter conformance requests. Numerical oracles remain caller supplied."""
from pathlib import Path
import tempfile
from cvsubstrate.contracts.groundwork import PluginDescriptor
from cvsubstrate.execution.services import invoke_service
from cvsubstrate.provenance.io import write_json,digest
from cvsubstrate.provenance.artifact_set import seal_directory,assert_not_inside_sealed
from cvsubstrate.errors import CVRSError

def execute_plugin(descriptor,operation,payload,output:Path,*,worker_python=None,timeout=180,source_sha256=None):
    d=PluginDescriptor.model_validate(descriptor);out=Path(output);assert_not_inside_sealed(out)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','choose a new plugin output')
    out.mkdir(parents=True);request={'descriptor':d.model_dump(mode='json'),'operation':operation,'payload':payload,
        'output_dir':str(out.resolve()),'source_sha256':source_sha256}
    write_json(out/'request.json',request)
    try:result=invoke_service('plugin',request,worker_python=worker_python,timeout=timeout,log=out/'worker.log')
    except Exception as exc:
        write_json(out/'failure.json',{'status':'FAILED','code':getattr(exc,'code',type(exc).__name__),'message':str(exc)});seal_directory(out);raise
    write_json(out/'result.json',result);seal_directory(out);return result

def conformance(descriptor,fixtures,output:Path,*,worker_python=None):
    d=PluginDescriptor.model_validate(descriptor);out=Path(output)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','conformance output must be new')
    out.mkdir(parents=True);checks=[]
    for i,fixture in enumerate(fixtures):
        expected_error=fixture.get('expected_error');expected_digest=fixture.get('expected_result_digest')
        try:
            r=execute_plugin(d.model_dump(mode='json'),fixture['operation'],fixture.get('payload',{}),out/f'case-{i}',worker_python=worker_python,timeout=fixture.get('timeout',30))
            passed=not expected_error and (expected_digest is None or digest(r['result'])==expected_digest)
            checks.append({'case':fixture.get('name',str(i)),'pass':passed,'result_digest':digest(r['result']),
                'numerical_oracle_supplied':expected_digest is not None,'error':None})
        except Exception as exc:
            code=getattr(exc,'code',type(exc).__name__);checks.append({'case':fixture.get('name',str(i)),'pass':code==expected_error,'error':code})
    result={'status':'PASS' if checks and all(c['pass'] for c in checks) else 'FAIL','checks':checks,
        'limits':'Only listed fixtures were executed. Passing transport fixtures does not certify model fidelity.'}
    write_json(out/'conformance.json',result);seal_directory(out);return result
