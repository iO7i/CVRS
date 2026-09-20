"""Explicit original-image mask universe -> isolated official mask evaluator."""
from cvsubstrate.contracts.frontier import MaskPrediction,MaskAnnotation,MaskEvaluationProtocol
from cvsubstrate.contracts.models import EvaluationProtocol
from cvsubstrate.execution.services import invoke_service
from cvsubstrate.provenance.io import digest

def mask_reference_payload(images,annotations,predictions,categories,protocol):
    p=MaskEvaluationProtocol.model_validate(protocol)
    native=EvaluationProtocol.model_validate(p.bbox_parameters)
    ps=[MaskPrediction.model_validate(x) for x in predictions];gs=[MaskAnnotation.model_validate(x) for x in annotations]
    universe={i['id']:i for i in images}
    if len(universe)!=len(images) or len({x.sample_id for x in ps})!=len(ps) or set(universe)!={x.sample_id for x in ps}:raise ValueError('mask prediction image universe differs')
    mapping={sid:i+1 for i,sid in enumerate(sorted(universe))}
    cats={c['id'] for c in categories}
    if len(cats)!=len(categories) or not cats:raise ValueError('explicit unique taxonomy required')
    prompt_conditioned=any(x.prompts for x in ps)
    if prompt_conditioned and p.prompt_policy=='no_prompts':raise ValueError('prompt-conditioned masks cannot masquerade as unprompted segmentation')
    for pred in ps:
        i=universe[pred.sample_id]
        if (pred.width,pred.height)!=(i['width'],i['height']):raise ValueError('image/mask dimensions differ')
    gt={'info':{},'images':[{'id':mapping[sid],'width':i['width'],'height':i['height']} for sid,i in universe.items()],'categories':categories,'annotations':[]};dt=[]
    gkeys=set()
    for i,a in enumerate(gs):
        if a.sample_id not in universe or a.category_id not in cats:raise ValueError('unknown GT image/category')
        if (a.sample_id,a.instance_id) in gkeys:raise ValueError('duplicate annotation identity')
        gkeys.add((a.sample_id,a.instance_id))
        if a.ignore and not a.iscrowd:raise ValueError('COCO adapter rejects noncrowd ignore rather than silently changing semantics')
        img=universe[a.sample_id]
        if (a.mask.width,a.mask.height)!=(img['width'],img['height']):raise ValueError('GT mask size differs')
        gt['annotations'].append({'id':i+1,'image_id':mapping[a.sample_id],'category_id':a.category_id,'segmentation':{'size':[a.mask.height,a.mask.width],'counts':a.mask.counts},'iscrowd':int(a.iscrowd)})
    for pred in ps:
        for a in pred.instances:
            if a.category_id not in cats:raise ValueError('mask needs explicit category mapping for reference AP')
            if a.score>=native.score_threshold:dt.append({'image_id':mapping[pred.sample_id],'category_id':a.category_id,'score':a.score,'segmentation':{'size':[a.mask.height,a.mask.width],'counts':a.mask.counts}})
    return {'operation':'evaluate_masks','ground_truth':gt,'detections':dt,'image_id_mapping':mapping,'protocol':native.model_dump(mode='json')},p

def evaluate_masks(images,annotations,predictions,categories,protocol,*,worker_python=None,timeout=180):
    request,p=mask_reference_payload(images,annotations,predictions,categories,protocol)
    result=invoke_service('evaluator',request,worker_python=worker_python,timeout=timeout)
    result['task_protocol']=p.model_dump(mode='json');result['protocol_sha256']=digest(p)
    result['comparison_warning']='Prompt-conditioned result; not equivalent to unprompted instance segmentation' if p.prompt_policy=='explicit_prompt_conditioned' else None
    return result
