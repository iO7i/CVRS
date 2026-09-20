"""Artifact-only task-dispatched re-evaluation with immutable inputs.

Official COCO/DOTA use their existing isolated reference workers. Local mask,
OBB and grounding diagnostics are explicitly named and never relabeled AP.
"""
from pathlib import Path
from cvsubstrate.provenance.io import read_json,read_jsonl,write_json,digest,file_digest
from cvsubstrate.provenance.artifact_set import seal_directory,assert_not_inside_sealed

def reevaluate_task(spec,out,*,worker_python=None,timeout=180):
    task=spec['task'];out=Path(out).resolve();assert_not_inside_sealed(out)
    if out.exists():raise ValueError('re-evaluation output must be new')
    inputs={k:Path(spec[k]).resolve() for k in ['dataset','predictions','protocol']}
    if any(p.is_relative_to(out) for p in inputs.values()):raise ValueError('source belongs to destination')
    before={k:file_digest(p) for k,p in inputs.items()};dataset=read_json(inputs['dataset']);rows=read_jsonl(inputs['predictions']);protocol=read_json(inputs['protocol'])
    out.mkdir(parents=True)
    population_receipt=None;access_receipt=None
    try:
        protected=(dataset.get('role')=='locked_test' or any(i.get('split_role')=='locked_test' for i in dataset.get('images',[]))
                   or dataset.get('splits',{}).get(spec.get('split'),{}).get('role')=='locked_test')
        if protected:
            from cvsubstrate.research.task_access import consume_task_authorization
            access_receipt=consume_task_authorization(spec)
        if spec.get('population_slice'):
            from cvsubstrate.analysis.population import population_slice
            from cvsubstrate.provenance.io import write_jsonl
            dataset,rows,population_receipt=population_slice(dataset,rows,task=task,predicate=spec['population_slice'],split=spec.get('split'))
            write_json(out/'population-dataset.json',dataset);write_jsonl(out/'population-predictions.jsonl',rows);write_json(out/'population.json',population_receipt)
        if task=='hbb':
            from cvsubstrate.evaluation.service import evaluate_files
            if access_receipt:
                from cvsubstrate.evaluation.service import evaluate_isolated
                from cvsubstrate.evaluation.metrics import evaluate
                from cvsubstrate.contracts.models import DatasetManifest,DetectionPrediction,EvaluationProtocol
                m=DatasetManifest.model_validate(dataset);pred=[DetectionPrediction.model_validate(x) for x in rows];p=EvaluationProtocol.model_validate(protocol)
                result=evaluate_isolated(m,spec['split'],pred,p,worker_python=worker_python,timeout=timeout) if worker_python else evaluate(m,spec['split'],pred,p)
            else:
                result=evaluate_files(out/'population-dataset.json' if population_receipt else inputs['dataset'],spec['split'],out/'population-predictions.jsonl' if population_receipt else inputs['predictions'],inputs['protocol'],worker_python=worker_python)
        elif task=='obb':
            from cvsubstrate.contracts.research import OrientedDataset,OrientedPrediction
            from cvsubstrate.evaluation.reference_dota import DotaReference,run_reference
            result=run_reference(OrientedDataset.model_validate(dataset),[OrientedPrediction.model_validate(x) for x in rows],DotaReference.model_validate(protocol),out/'reference',worker_python=worker_python,timeout=timeout)
        elif task=='masks':
            from cvsubstrate.vision.evaluation import evaluate_masks
            result=evaluate_masks(dataset['images'],dataset['annotations'],rows,dataset['categories'],protocol,worker_python=worker_python,timeout=timeout)
        elif task=='grounding':
            from cvsubstrate.vision.ontology import ConceptOntology,evaluate_open_set
            from cvsubstrate.vision.ontology import canonical_grounding_rows
            flattened,prompt_receipt=canonical_grounding_rows(rows,dataset['images'])
            result=evaluate_open_set(flattened,dataset['annotations'],ConceptOntology.model_validate(protocol['ontology']),iou_threshold=protocol.get('iou_threshold',.5),score_threshold=protocol.get('score_threshold',0.0),prompt_source=prompt_receipt['prompt_source'])
            result['conversion_receipt']=prompt_receipt
        elif task=='mask_diagnostics':
            from cvsubstrate.vision.diagnostics import mask_diagnostics
            result=mask_diagnostics(dataset,rows,protocol)
        else:raise ValueError('unknown task evaluator')
        if any(file_digest(p)!=before[k] for k,p in inputs.items()):raise ValueError('evaluation mutated source artifacts')
        receipt={'format':'cvrs-task-reevaluation/1.0','task':task,'inputs':before,'protocol_sha256':digest(protocol),'dataset_sha256':digest(dataset),'result':result,'model_executed':False,'training_executed':False,'parent_evaluation':spec.get('parent_evaluation'),'population_receipt':population_receipt,'final_test_access':access_receipt,'purpose':spec.get('purpose','research')}
        write_json(out/'evaluation.json',receipt);seal_directory(out);return receipt
    except Exception as e:
        write_json(out/'failure.json',{'status':'FAILED','message':str(e),'inputs':before,'model_executed':False});seal_directory(out);raise

def register_evaluation(registry,output,*,prediction_record_id=None):
    from cvsubstrate.provenance.artifact_set import verify_directory
    p=Path(output)
    if verify_directory(p)['status']!='VERIFIED':raise ValueError('evaluation evidence failed integrity')
    value=read_json(p/'evaluation.json');sha=registry.add_file(p/'evaluation.json')
    rid=registry.add('evaluation',{'receipt_sha256':sha,'task':value['task'],'inputs':value['inputs'],'model_executed':False})
    if prediction_record_id:registry.add_edge({'source':rid,'target':prediction_record_id,'relation':'derived_from','evidence':[sha]})
    return rid
