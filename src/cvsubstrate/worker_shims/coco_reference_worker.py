"""Isolated reference COCO evaluation; no CVRS/Pydantic dependency in this worker."""
import contextlib,io
from runtime_common import main,dependency,offline

def run(req):
    op=req['operation']
    if op=='capabilities':
        try:v=dependency('pycocotools');installed=True
        except RuntimeError:v=None;installed=False
        return {'installed':installed,'evaluator':'pycocotools','version':v,'execution_verified':False}
    if op not in {'evaluate','evaluate_masks'}:raise RuntimeError('OPERATION_UNSUPPORTED: '+op)
    offline();p=req['protocol'];version=dependency('pycocotools',p['evaluator_version'])
    import numpy as np
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval
    gt,dt,mapping=req['ground_truth'],req['detections'],req['image_id_mapping']
    if op=='evaluate_masks':
        from pycocotools import mask as mask_api
        for is_gt, items in [(True,gt['annotations']),(False,dt)]:
            for item in items:
                rle=item['segmentation']
                item['segmentation']=mask_api.frPyObjects(rle,rle['size'][0],rle['size'][1])
                item['area']=float(mask_api.area(item['segmentation']))
                if is_gt:item['bbox']=mask_api.toBbox(item['segmentation']).tolist()
    with contextlib.redirect_stdout(io.StringIO()):
        a=COCO();a.dataset=gt;a.createIndex()
        if dt:b=a.loadRes(dt)
        else:b=COCO();b.dataset={'images':gt['images'],'categories':gt['categories'],'annotations':[]};b.createIndex()
        ev=COCOeval(a,b,'segm' if op=='evaluate_masks' else 'bbox');ev.params.imgIds=list(mapping.values());ev.params.catIds=[c['id'] for c in gt['categories']]
        ev.params.iouThrs=np.asarray(p['iou_thresholds']);ev.params.recThrs=np.asarray(p['recall_thresholds'])
        ev.params.maxDets=p['max_detections'];ev.params.areaRng=list(p['area_ranges'].values());ev.params.areaRngLbl=list(p['area_ranges']);ev.params.useCats=1
        ev.evaluate();ev.accumulate()
    metrics={}
    def mean(values):
        v=values[values>-1]
        return {'value':float(v.mean()) if v.size else None,'reason':None if v.size else 'no evaluable ground truth in this slice'}
    for ai,area in enumerate(p['area_ranges']):
        for mi,maximum in enumerate(p['max_detections']):
            metrics['AP/'+area+'/maxDets='+str(maximum)]=mean(ev.eval['precision'][:,:,:,ai,mi])
            metrics['AR/'+area+'/maxDets='+str(maximum)]=mean(ev.eval['recall'][:,:,ai,mi])
    ap50=None
    if 0.5 in p['iou_thresholds']:
        ti=p['iou_thresholds'].index(0.5);ai=list(p['area_ranges']).index('all');ap50=mean(ev.eval['precision'][ti,:,:,ai,-1])
    return {'kind':'REFERENCE_COCO_MASK' if op=='evaluate_masks' else 'REFERENCE_COCO_BBOX','evaluator':'pycocotools','evaluator_version':version,'metrics':metrics,'AP50':ap50,'image_id_mapping':mapping,
        'support':{'images':len(mapping),'objects':len(gt['annotations']),'categories':len(gt['categories'])},
        'execution_environment':{'python':__import__('sys').version.split()[0],'numpy':np.__version__},
        'note':'Reference library invoked under declared parameters; not independent published-score reproduction.'}
if __name__=='__main__':main(run)
