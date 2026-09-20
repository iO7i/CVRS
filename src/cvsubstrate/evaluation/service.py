"""Evaluation location is separate from model/controller dependency environments."""
from pathlib import Path
from cvsubstrate.contracts.models import DatasetManifest,DetectionPrediction,EvaluationProtocol
from cvsubstrate.provenance.io import read_json,read_jsonl,digest
from cvsubstrate.execution.services import invoke_service
from cvsubstrate.evaluation.metrics import validate_predictions,to_coco,evaluate
from cvsubstrate.errors import CVRSError

def evaluate_isolated(m,split,rows,protocol,*,worker_python,timeout=180.0,log=None):
    from cvsubstrate.data.manifest import validate_manifest
    validate_manifest(m,check_files=False)
    validate_predictions(m,split,rows)
    if protocol.evaluator!='pycocotools':return evaluate(m,split,rows,protocol)
    gt,dt,mapping=to_coco(m,split,rows,protocol.score_threshold)
    result=invoke_service('evaluator',{'operation':'evaluate','ground_truth':gt,'detections':dt,'image_id_mapping':mapping,'protocol':protocol.model_dump(mode='json')},worker_python=worker_python,timeout=timeout,log=log)
    result['comparison_key']={'dataset_digest':digest(m),'split':split,'sample_ids':m.splits[split].sample_ids,
        'taxonomy':[c.model_dump(mode='json') for c in m.categories],'evaluation_protocol':protocol.model_dump(mode='json')}
    result['comparison_digest']=digest(result['comparison_key']);result['dataset_purpose']=m.purpose
    if m.purpose=='software_fixture':result['scientific_claim']='NONE: software fixtures do not establish detector quality or Sim2Real improvement'
    return result

def evaluate_files(dataset,split,predictions,protocol,*,worker_python=None,timeout=180.0):
    m=DatasetManifest.model_validate(read_json(dataset));p=EvaluationProtocol.model_validate(read_json(protocol))
    if split not in m.splits or m.splits[split].role not in {'dev','selection'}:raise CVRSError('PROTECTED_SPLIT','standalone evaluation accepts development/selection; final test needs governed run')
    rows=[DetectionPrediction.model_validate(r) for r in read_jsonl(predictions)]
    if worker_python:return evaluate_isolated(m,split,rows,p,worker_python=worker_python,timeout=timeout)
    return evaluate(m,split,rows,p)
