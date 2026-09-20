from cvsubstrate.contracts.models import DetectionPrediction
from cvsubstrate.contracts.frontier import GroundedPrediction
from cvsubstrate.provenance.io import digest

def map_grounded(row:GroundedPrediction,mapping:dict[str,int],*,normalization='exact'):
    if normalization not in {'exact','casefold'}:raise ValueError('explicit phrase-normalization policy required')
    norm=(lambda s:s) if normalization=='exact' else (lambda s:s.casefold())
    translated={}
    for key,value in mapping.items():
        n=norm(key)
        if n in translated and translated[n]!=value:raise ValueError('conflicting normalized mappings')
        translated[n]=value
    unknown=sorted({p for p in row.phrases if norm(p) not in translated})
    if unknown:raise ValueError('UNMAPPED_PHRASES: '+str(unknown))
    p=DetectionPrediction(sample_id=row.sample_id,width=row.width,height=row.height,boxes=row.boxes,scores=row.scores,
        category_ids=[translated[norm(x)] for x in row.phrases],transform_provenance={
        'grounding_prompt_sha256':digest(row.prompt),'mapping_sha256':digest(mapping),'phrase_normalization':normalization,
        'prompt_source':row.prompt.source,'native_prediction_sha256':digest(row)})
    return p,{'input_detections':len(row.boxes),'output_detections':len(p.boxes),'unmapped':[],
        'grounding_to_closed_set_is_explicit':True,'does_not_prove_open_vocabulary_generalization':True}

def cross_paradigm_report(records):
    fields=['dataset_sha256','split_sha256','taxonomy_sha256','evaluator_sha256','preprocessing_sha256']
    pairs=[]
    for i,a in enumerate(records):
        for b in records[i+1:]:
            missing=[k for k in fields if not a.get(k) or not b.get(k)]
            differences=[k for k in fields if a.get(k)!=b.get(k)]
            task_same=a.get('evaluation_task')==b.get('evaluation_task')
            prompt_equal=a.get('prompt_protocol_sha256')==b.get('prompt_protocol_sha256')
            oracle=bool(a.get('oracle_prompt') or b.get('oracle_prompt'))
            valid=not missing and not differences and task_same
            pairs.append({'left':a['id'],'right':b['id'],'metric_comparability':'COMPARABLE_UNDER_DECLARED_PROTOCOL' if valid else 'INCOMPARABLE',
                'missing':missing,'differences':differences,'same_task':task_same,'same_prompt_protocol':prompt_equal,
                'training_fairness':'NOT_ESTABLISHED','scientific_use':'DESCRIPTIVE_ONLY' if oracle or not prompt_equal else 'requires explicit training/pretraining controls'})
    return {'records':records,'comparisons':pairs,'ranking':None,'note':'Mask IoU, detector AP and phrase grounding are not interchangeable metrics.'}
