"""Structured comparison of task, image treatment, postprocessing and training."""
from cvsubstrate.provenance.io import digest
EVALUATION_FIELDS=('dataset_sha256','split','taxonomy_sha256','task','evaluator','evaluator_version','iou_thresholds','area_ranges','max_detections','ignore_policy','tile_policy','merge_policy')
PIPELINE_FIELDS=('color_order','bands','resize','padding','normalization','score_threshold','nms','max_detections','checkpoint_sha256','pretraining','training_budget','prompt_policy','prompt_set_sha256','model_assets_sha256')

def normalization_report(left:dict,right:dict):
    def diff(fields):
        return [{'field':k,'left':left.get(k),'right':right.get(k),'status':
            'UNKNOWN' if k not in left or k not in right else 'MATCH' if left[k]==right[k] else 'DIFFERENT'} for k in fields]
    ev=diff(EVALUATION_FIELDS);pipeline=diff(PIPELINE_FIELDS)
    incompatible=[x['field'] for x in ev if x['status']=='DIFFERENT']
    unknown=[x['field'] for x in ev if x['status']=='UNKNOWN']
    return {'left_digest':digest(left),'right_digest':digest(right),'evaluation':ev,'pipeline':pipeline,
      'comparability':'INCOMPARABLE' if incompatible else 'DESCRIPTIVE_ONLY' if unknown else 'COMPARABLE_UNDER_DECLARED_PROTOCOL',
      'incompatible_fields':incompatible,'unknown_fields':unknown,
      'training_fairness':'NOT_ESTABLISHED','note':'Matching evaluation contracts do not equalize models, pretraining, prompts, or compute.'}
