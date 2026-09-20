"""Re-evaluate immutable predictions; never invoke a model or edit original runs."""
from pathlib import Path
from cvsubstrate.provenance.io import digest, file_digest, read_json, write_json
from cvsubstrate.provenance.artifact_set import seal_directory, assert_not_inside_sealed
from cvsubstrate.evaluation.service import evaluate_files

def reevaluate(dataset,split,predictions,protocol,out,*,worker_python=None,origin=None):
    out=Path(out).resolve();assert_not_inside_sealed(out)
    sources=[Path(p).resolve() for p in [dataset,predictions,protocol]]
    if out.exists() or any(p.is_relative_to(out) for p in sources):raise ValueError('new derived-output directory required')
    before={str(p):file_digest(p) for p in sources}
    result=evaluate_files(dataset,split,predictions,protocol,worker_python=worker_python)
    if any(file_digest(p)!=before[str(p)] for p in sources):raise ValueError('source artifact changed during evaluation')
    from cvsubstrate.contracts.models import DatasetManifest,EvaluationProtocol
    dataset_value=DatasetManifest.model_validate(read_json(dataset)).model_dump(mode='json')
    protocol_value=EvaluationProtocol.model_validate(read_json(protocol)).model_dump(mode='json')
    from cvsubstrate.research.metrics import scalar_observations
    metrics=scalar_observations(result)
    receipt={'format':'cvrs-evaluation-receipt','version':'1.0','status':'EVALUATED','operation':'reevaluate',
        'dataset_sha256':digest(dataset_value),'protocol_sha256':digest(protocol_value),'predictions_sha256':file_digest(Path(predictions)),
        'dataset_file_sha256':file_digest(Path(dataset)),'protocol_file_sha256':file_digest(Path(protocol)),
        'split':split,'evaluator_identity':{'evaluator':protocol_value.get('evaluator'),'version':protocol_value.get('evaluator_version'), 'protocol_sha256':digest(protocol_value)},
        'metrics':metrics,'result':result,'origin':origin,
        'model_executed':False,'training_executed':False,'purpose':dataset_value.get('purpose','unknown')}
    out.mkdir(parents=True);write_json(out/'evaluation.json',receipt)
    write_json(out/'lineage.json',{'source_artifact_sha256':list(before.values()),'parent':origin,'new_analysis_id':digest(receipt),'original_artifacts_modified':False})
    seal_directory(out)
    return {'status':'REEVALUATED','analysis_id':digest(receipt),'path':str(out),'metrics':receipt['metrics'],'model_executed':False}
