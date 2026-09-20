"""Shared worker entrypoint with structured failures and independent validation."""
import argparse
from pathlib import Path
from cvsubstrate.contracts.models import WorkerRequest, WorkerResponse, ExperimentSpec, DatasetManifest
from cvsubstrate.data.manifest import validate_experiment, validate_manifest
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import read_json, write_json

def validated_inputs(req: WorkerRequest):
    if req.experiment is None or req.manifest is None or req.data_root is None:
        raise CVRSError('WORKER_INPUT', 'experiment, manifest, and data root required')
    spec = ExperimentSpec.model_validate(req.experiment)
    m = DatasetManifest.model_validate(req.manifest)
    validate_manifest(m, Path(req.data_root), check_files=True)
    validate_experiment(spec, m, req.final_test_authorization)
    if req.output_dir is None:
        raise CVRSError('OUTPUT_REQUIRED', 'worker output directory required')
    out = Path(req.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise CVRSError('OUTPUT_NOT_EMPTY', 'worker refuses to overwrite existing artifacts')
    return (spec, m, Path(req.data_root).resolve(), out)

def entrypoint(handler):
    p = argparse.ArgumentParser()
    p.add_argument('--request', required=True)
    p.add_argument('--response', required=True)
    args = p.parse_args()
    try:
        req = WorkerRequest.model_validate(read_json(Path(args.request)))
        result = handler(req)
        response = WorkerResponse(status='SUCCEEDED', result=result)
    except CVRSError as exc:
        response = WorkerResponse(status='FAILED', error=exc.as_dict())
    except Exception as exc:
        response = WorkerResponse(status='FAILED', error={'code': 'WORKER_EXCEPTION', 'message': f'{type(exc).__name__}: {exc}'})
    write_json(Path(args.response), response)
