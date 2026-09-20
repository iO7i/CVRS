"""Calibration manifest validation and isolated native quantization."""
from pathlib import Path
from cvsubstrate.contracts.frontier import QuantizationSpec
from cvsubstrate.provenance.io import read_json,write_json,file_digest,digest
from cvsubstrate.execution.services import invoke_service
from cvsubstrate.provenance.artifact_set import seal_directory

def validate_calibration(spec):
    q=spec if isinstance(spec,QuantizationSpec) else QuantizationSpec.model_validate(spec)
    if file_digest(Path(q.model_path))!=q.model_sha256:raise ValueError('model changed')
    for item in q.calibration:
        if Path(item.path).suffix!='.npz':raise ValueError('calibration requires explicit preprocessed named tensors in .npz')
        if file_digest(Path(item.path))!=item.sha256:raise ValueError('calibration item changed')
    return {'status':'INPUT_IDENTITIES_VERIFIED','items':len(q.calibration),'calibration_sha256':digest(q.calibration),
        'preprocessing_sha256':q.preprocessing_sha256,'accuracy_certified':False}

def quantize(spec_path,output,*,worker_python=None,timeout=600):
    q=QuantizationSpec.model_validate(read_json(Path(spec_path)) if isinstance(spec_path,(str,Path)) else spec_path)
    valid=validate_calibration(q);out=Path(output).resolve()
    if out.exists():raise ValueError('new quantization directory required')
    out.mkdir(parents=True);write_json(out/'spec.json',q);write_json(out/'calibration-validation.json',valid)
    try:
        result=invoke_service('quantization',{'operation':'quantize','spec':q.model_dump(mode='json'),'output_dir':str(out/'worker')},worker_python=worker_python,timeout=timeout,log=out/'worker.log')
        write_json(out/'result.json',result);seal_directory(out);return result
    except Exception as exc:
        write_json(out/'failure.json',{'status':'FAILED','message':str(exc)});seal_directory(out);raise
