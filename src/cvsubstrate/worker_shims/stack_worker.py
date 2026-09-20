"""Native research-stack workers. No imports from the modern controller.

Supported families keep their complete model graph in one native interpreter.
No splitting of jointly trained model internals, no downloaded model fallback.
"""
from pathlib import Path
import sys,os,math,json,importlib,importlib.metadata,runpy
from runtime_common import main,read,write,write_lines,check_file,sha,offline

def rle(mask):
    import numpy as np
    a=np.asarray(mask,dtype=bool);counts=[];old=False;count=0
    for v in a.reshape(-1,order='F'):
        if bool(v)==old:count+=1
        else:counts.append(count);count=1;old=bool(v)
    counts.append(count)
    return {'size':[int(a.shape[0]),int(a.shape[1])],'counts':counts,'order':'F'}

def numpy(value):
    return value.detach().cpu().numpy() if hasattr(value,'detach') else value

def polygon(box):
    cx,cy,w,h,a=map(float,box);c=math.cos(a);s=math.sin(a)
    return [[cx+x*c-y*s,cy+x*s+y*c] for x,y in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]]

def handle(req):
    offline();p=req['payload'];family=p['family'];op=req['operation'];out=Path(req['output_dir']);out.mkdir(parents=True,exist_ok=True)
    if not p.get('trust_code'):raise RuntimeError('TRUST_REQUIRED: native config/checkpoint execution must be reviewed')
    if p.get('repo'):sys.path.insert(0,str(Path(p['repo']).resolve()))
    config=check_file(p['config'],p['config_sha256']) if p.get('config') else None
    checkpoint=check_file(p['checkpoint'],p['checkpoint_sha256']) if p.get('checkpoint') else None
    if op=='native_train':
        if not config:raise ValueError('native train requires config')
        entry=check_file(p['entrypoint'],p['entrypoint_sha256'])
        sys.argv=[str(entry),str(config),'--work-dir',str(out/'native')]+p.get('extra_args',[])
        try:runpy.run_path(str(entry),run_name='__main__')
        except SystemExit as exc:
            if exc.code not in (0,None):raise RuntimeError('native entrypoint failed: '+str(exc.code))
        return {'status':'COMPLETED_NATIVE_COMMAND','native_output':'native','entrypoint_sha256':sha(entry),
                'training_semantics':'native config; no inferred exposure equivalence'}
    if family=='mmdeploy' and op=='export':
        entry=check_file(p['entrypoint'],p['entrypoint_sha256']);deployment=check_file(p['deployment_config'],p['deployment_config_sha256'])
        image=check_file(p['image'],p['image_sha256'])
        if not(config and checkpoint):raise ValueError('MMDeploy needs explicit model config and checkpoint')
        sys.argv=[str(entry),str(deployment),str(config),str(checkpoint),str(image),'--work-dir',str(out/'native')]+p.get('extra_args',[])
        try:runpy.run_path(str(entry),run_name='__main__')
        except SystemExit as exc:
            if exc.code not in (0,None):raise RuntimeError('native entrypoint failed: '+str(exc.code))
        return {'status':'EXPORTED_NATIVE','native_output':'native','fidelity_verified':False}
    if not checkpoint:raise ValueError('real native inference requires explicit local checkpoint')
    import numpy as np
    from PIL import Image
    category_map={int(k):int(v) for k,v in p.get('category_mapping',{}).items()}
    rows=[];native=[];device=p.get('device','cpu')
    if family=='detectron2':
        from detectron2.config import get_cfg
        from detectron2.engine import DefaultPredictor,DefaultTrainer
        cfg=get_cfg();cfg.merge_from_file(str(config));cfg.MODEL.WEIGHTS=str(checkpoint);cfg.MODEL.DEVICE=device
        if op=='train':
            cfg.OUTPUT_DIR=str(out/'native');trainer=DefaultTrainer(cfg);trainer.resume_or_load(resume=p.get('resume',False));trainer.train()
            return {'status':'TRAINED','output':'native','exposure_semantics':'native trainer'}
        predictor=DefaultPredictor(cfg)
        def infer(image):return predictor(np.asarray(Image.open(image).convert('RGB'))[:,:,::-1])
    elif family in {'mmseg0','mmseg1'}:
        if family=='mmseg1':
            from mmseg.apis import init_model,inference_model
            model=init_model(str(config),str(checkpoint),device=device)
            def infer(image):return numpy(inference_model(model,image).pred_sem_seg.data)[0]
        else:
            from mmseg.apis import init_segmentor,inference_segmentor
            model=init_segmentor(str(config),str(checkpoint),device=device)
            def infer(image):return inference_segmentor(model,image)[0]
    elif family in {'mmrotate','mmyolo','mmdetection2','mmdetection3','onedl'}:
        if family=='mmrotate':import mmrotate
        if family=='mmyolo':
            from mmyolo.utils import register_all_modules
            register_all_modules()
        from mmdet.apis import init_detector,inference_detector
        model=init_detector(str(config),str(checkpoint),device=device)
        def infer(image):return inference_detector(model,image)
    elif family=='sam3':
        from sam3.model_builder import build_sam3_image_model
        from sam3.model.sam3_image_processor import Sam3Processor
        # Additional assets such as BPE vocabulary must be supplied locally in model_kwargs.
        kwargs=dict(p.get('model_kwargs',{}));kwargs.update(checkpoint_path=str(checkpoint),load_from_HF=False,device=device)
        model=build_sam3_image_model(**kwargs);processor=Sam3Processor(model)
        def infer(image):
            state=processor.set_image(Image.open(image).convert('RGB'))
            return [(prompt,processor.set_text_prompt(state=state,prompt=prompt)) for prompt in p['text_prompts']]
    else:raise ValueError('unsupported stack family '+family)
    for index,sample in enumerate(p.get('images',[])):
        image=str(check_file(sample['path'],sample['sha256']));im=Image.open(image);w,h=im.size
        result=infer(image);sid=sample['id']
        if family in {'mmseg0','mmseg1'}:
            labels=np.asarray(result,dtype=np.int32)
            if labels.shape!=(h,w):raise ValueError('semantic model did not return original-image shape')
            fn='labels-'+str(index)+'.npy';np.save(out/fn,labels,allow_pickle=False)
            rows.append({'task':'semantic_segmentation','sample_id':sid,'width':w,'height':h,'labels':fn,'sha256':sha(out/fn),
                         'category_mapping':p.get('category_mapping',{}),'ignore_index':p.get('ignore_index',255),'reduce_zero_label':p.get('reduce_zero_label',False)})
            native.append({'sample_id':sid,'array':fn});continue
        if family=='sam3':
            regions=[]
            for prompt,pred in result:
                masks=numpy(pred['masks']);boxes=numpy(pred['boxes']);scores=numpy(pred['scores'])
                for i,(box,score,mask) in enumerate(zip(boxes,scores,masks)):
                    regions.append({'phrase':prompt,'box':box.tolist(),'score':float(score),'mask':rle(np.squeeze(mask))})
            rows.append({'task':'grounded_masks','sample_id':sid,'width':w,'height':h,'regions':regions,'prompts':p['text_prompts'],'prompt_source':p.get('prompt_source','unknown')})
            native.append({'sample_id':sid,'regions':regions});continue
        boxes=[];scores=[];labels=[];masks=None;obb=False
        if family=='detectron2':
            if 'instances' not in result:raise ValueError('this Detectron2 profile requires instance predictions')
            ins=result['instances'].to('cpu');boxes=numpy(ins.pred_boxes.tensor);scores=numpy(ins.scores);labels=numpy(ins.pred_classes)
            masks=numpy(ins.pred_masks) if ins.has('pred_masks') else None
        elif hasattr(result,'pred_instances'):
            ins=result.pred_instances;boxes=numpy(ins.bboxes);scores=numpy(ins.scores);labels=numpy(ins.labels)
            masks=numpy(ins.masks) if hasattr(ins,'masks') else None
        else:
            if isinstance(result,tuple):result,masks=result
            all_rows=[]
            for cid,arr in enumerate(result):
                for x in arr:all_rows.append((x[:-1],x[-1],cid))
            boxes=[x[0] for x in all_rows];scores=[x[1] for x in all_rows];labels=[x[2] for x in all_rows]
            # Legacy mask list is grouped by class; preserve order matching boxes.
            if masks is not None:masks=[m for group in masks for m in group]
        boxes=np.asarray(boxes).reshape((-1,5 if family=='mmrotate' else 4));scores=np.asarray(scores);labels=np.asarray(labels)
        if any(int(cid) not in category_map for cid in labels):raise ValueError('native prediction contains unmapped categories')
        native.append({'sample_id':sid,'boxes':boxes.tolist(),'scores':scores.tolist(),'labels':labels.tolist()})
        if family=='mmrotate':
            if p.get('angle_convention') not in {'oc','le90','le135'}:raise ValueError('declare native MMRotate angle convention: oc/le90/le135')
            if p.get('angle_unit','radians')!='radians':raise ValueError('MMRotate native xywha requires radians in this profile')
            rows.append({'task':'obb_detection','sample_id':sid,'width':w,'height':h,'polygons':[polygon(b) for b in boxes],
                         'scores':scores.tolist(),'category_ids':[category_map[int(c)] for c in labels],
                         'angle_convention':p.get('angle_convention','native_explicit_required')})
        else:
            row={'schema_version':'1.0','sample_id':sid,'width':w,'height':h,'boxes':boxes.tolist(),
                 'scores':scores.tolist(),'category_ids':[category_map[int(c)] for c in labels],'coordinate_frame':'original_image_xyxy'}
            rows.append(row)
            if masks is not None:
                encoded=[]
                for m in masks:
                    if isinstance(m,dict):
                        from pycocotools import mask as mask_util
                        m=mask_util.decode(m)
                    encoded.append(rle(m))
                write(out/('masks-'+str(index)+'.json'),{'sample_id':sid,'masks':encoded,'category_ids':row['category_ids'],'scores':row['scores']})
    write_lines(out/'predictions.jsonl',rows);write_lines(out/'native-predictions.jsonl',native)
    return {'family':family,'operation':op,'samples':len(rows),'checkpoint_sha256':sha(checkpoint),
            'config_sha256':sha(config) if config else None,'predictions':'predictions.jsonl','native_outputs':'native-predictions.jsonl',
            'scope':'native environment execution, not published-result reproduction'}

if __name__=='__main__':main(handle)
