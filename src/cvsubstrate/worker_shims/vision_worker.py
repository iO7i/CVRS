"""Native, local-asset-only Grounding DINO / SAM / SAM2 / YOLO-World inference.

Each job owns one worker process and one framework environment. Optional native
APIs are called directly; no canned predictions or fallback to another model.
"""
from pathlib import Path
import sys,hashlib,importlib.metadata,time
from typing import Any
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from runtime_common import main,check_file,offline,dependency,write,write_lines,sha,safe_path

def run(req):
    from cvsubstrate.contracts.frontier import VisionJob,GroundedPrediction,MaskInstance,MaskPrediction
    from cvsubstrate.vision.masks import encode_mask
    from cvsubstrate.provenance.io import digest
    job=VisionJob.model_validate(req['job']);out=Path(req['output_dir']);out.mkdir(parents=True,exist_ok=True)
    if req['operation']=='capabilities':
        return {'backend':job.backend,'operations':['predict'],'model_execution_verified':False,'network_fallback':False}
    root=Path(job.model_dir).resolve()
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual!=set(job.model_files):raise ValueError('model_files must hash every file in local asset directory')
    for rel,h in job.model_files.items():check_file(safe_path(root,rel),h)
    for image in job.images:check_file(image['path'],image['sha256'])
    for pkg,version in job.package_versions.items():dependency(pkg,version)
    offline();import torch
    import numpy as np
    from PIL import Image
    torch.set_num_threads(int(job.config.get('cpu_threads',1)))
    bysample: dict[str, list[Any]]={}
    for p in job.prompts:bysample.setdefault(p.sample_id,[]).append(p)
    if len({p.id for p in job.prompts})!=len(job.prompts):raise ValueError('prompt IDs must be unique across job')
    backend=job.backend
    from vision_drivers import get_driver
    driver=get_driver(backend);processor,model=driver.load(job,root)
    mapping={int(k):int(v) for k,v in job.config.get('category_map',{}).items()}
    rows=[];raw_files=[];start=time.perf_counter()
    for image in job.images:
        with Image.open(image['path']) as opened:
            if opened.getexif().get(274,1)!=1:raise ValueError('normalize EXIF orientation and labels before ingestion')
            pil=opened.convert('RGB')
        w,h=pil.size;sid=image['id'];prompts=bysample.get(sid,[])
        if 'width' in image and (image['width'],image['height'])!=(w,h):raise ValueError('declared image dimensions differ')
        for p in prompts:
            if p.kind=='points' and any(x>=w or y>=h for x,y in p.points):raise ValueError('prompt outside image')
            if p.kind=='box' and (p.box[2]>w or p.box[3]>h):raise ValueError('box prompt outside image')
        if backend in {'hf_grounding_dino','yolo_world'}:
            if len(prompts)!=1 or prompts[0].kind!='text':raise ValueError('one text prompt per image required')
            p=prompts[0]
            if backend=='hf_grounding_dino':
                inputs=processor(images=pil,text=p.text,return_tensors='pt').to(job.device)
                with torch.inference_mode():outputs=model(**inputs)
                values=processor.post_process_grounded_object_detection(outputs,inputs.input_ids,
                    threshold=job.config.get('box_threshold',.25),text_threshold=job.config.get('text_threshold',.25),target_sizes=[(h,w)])[0]
                boxes=values['boxes'].cpu().tolist();scores=values['scores'].cpu().tolist()
                phrases=values.get('text_labels',values.get('labels'))
                if phrases is None or any(not isinstance(x,str) for x in phrases):raise ValueError('processor did not return grounded phrases; unsupported API version')
            else:
                classes=job.config.get('classes')
                if not classes or p.text!= '. '.join(classes)+'.':raise ValueError('YOLO-World prompt must exactly describe configured class phrases')
                model.set_classes(classes)
                r=model.predict(pil,device=job.device,verbose=False,conf=job.config.get('box_threshold',.25))[0]
                boxes=r.boxes.xyxy.cpu().tolist();scores=r.boxes.conf.cpu().tolist();phrases=[classes[int(c)] for c in r.boxes.cls.cpu().tolist()]
            native={'sample_id':sid,'boxes':boxes,'scores':scores,'phrases':phrases,'prompt':p.model_dump(mode='json')}
            raw=out/(digest(sid)[:20]+'-native.json');write(raw,native);raw_files.append(raw.name)
            rows.append(GroundedPrediction(sample_id=sid,width=w,height=h,prompt=p,boxes=boxes,scores=scores,phrases=list(phrases),native_output_sha256=sha(raw)).model_dump(mode='json'))
        else:
            instances=[];rawmasks=[];rawscores=[]
            if backend=='torchvision_mask':
                if prompts:raise ValueError('closed-set native mask conformance path takes no prompts')
                tensor=torch.from_numpy(np.asarray(pil).copy()).permute(2,0,1).float().div(255).to(job.device)
                with torch.inference_mode():native=model([tensor])[0]
                for i,(m,score,cat) in enumerate(zip(native['masks'][:,0].cpu().numpy(),native['scores'].cpu().tolist(),native['labels'].cpu().tolist())):
                    mask=m>float(job.config.get('mask_threshold',.5));rawmasks.append(mask);rawscores.append(score)
                    instances.append(MaskInstance(id='instance-'+str(i),mask=encode_mask(mask),score=float(score),score_kind='detection_confidence',score_semantics='native detection confidence, not calibrated mask IoU',category_id=mapping[int(cat)]))
            elif backend=='ultralytics_seg':
                if prompts:raise ValueError('fixed-class instance segmenter does not consume prompts')
                r=model.predict(pil,device=job.device,verbose=False,retina_masks=True,conf=job.config.get('threshold',.25))[0]
                if r.masks is not None:
                    mapping={int(k):int(v) for k,v in job.config['category_map'].items()}
                    for i,(m,score,cat) in enumerate(zip(r.masks.data.cpu().numpy(),r.boxes.conf.cpu().tolist(),r.boxes.cls.cpu().tolist())):
                        if m.shape!=(h,w):raise ValueError('native mask not in original coordinates')
                        mask=m>0.5;rawmasks.append(mask);rawscores.append(score)
                        instances.append(MaskInstance(id='instance-'+str(i),mask=encode_mask(mask),score=float(score),score_kind='detection_confidence',score_semantics='native detection confidence, not calibrated mask IoU',category_id=mapping[int(cat)]))
            else:
                if not prompts:raise ValueError('promptable segmenter requires explicit prompts')
                if backend=='sam2':model.set_image(np.asarray(pil))
                from vision_drivers import grouped_prompts,mask_logits
                for representative,group in grouped_prompts(prompts,job.config.get('prompt_groups')):
                    points=[point for p in group if p.kind=='points' for point in p.points]
                    labels=[label for p in group if p.kind=='points' for label in p.point_labels]
                    box=next((p.box for p in group if p.kind=='box'),None)
                    mask_prompt=next((p for p in group if p.kind=='mask'),None)
                    if backend=='sam2':
                        kw={'multimask_output':job.config.get('multimask_output',True)}
                        if points:kw.update(point_coords=np.asarray(points),point_labels=np.asarray(labels))
                        if box is not None:kw['box']=np.asarray(box)
                        if mask_prompt is not None:kw['mask_input']=mask_logits(mask_prompt,backend,job,model,processor)
                        with torch.inference_mode():masks,scores,_=model.predict(**kw)
                    else:
                        kw={}
                        if points:kw.update(input_points=[[points]],input_labels=[[labels]])
                        if box is not None:kw['input_boxes']=[[box]]
                        inputs=processor(images=pil,return_tensors='pt',**kw).to(job.device)
                        if mask_prompt is not None:inputs['input_masks']=mask_logits(mask_prompt,backend,job,model,processor)
                        with torch.inference_mode():output=model(**inputs,multimask_output=job.config.get('multimask_output',True))
                        masks=processor.image_processor.post_process_masks(output.pred_masks.cpu(),inputs['original_sizes'].cpu(),inputs['reshaped_input_sizes'].cpu())[0][0].numpy()
                        scores=output.iou_scores.cpu().numpy()[0,0]
                    for j,(m,score) in enumerate(zip(masks,scores)):
                        if m.shape!=(h,w):raise ValueError('native mask shape differs from original image')
                        mask=np.asarray(m,dtype=bool);rawmasks.append(mask);rawscores.append(float(score))
                        instances.append(MaskInstance(id=f'{representative}-{j}',mask=encode_mask(mask),score=float(score),prompt_id=representative))
            raw=out/(digest(sid)[:20]+'-native.npz')
            np.savez_compressed(raw,masks=np.stack(rawmasks) if rawmasks else np.empty((0,h,w),dtype=bool),scores=np.asarray(rawscores))
            raw_files.append(raw.name)
            rows.append(MaskPrediction(sample_id=sid,width=w,height=h,instances=instances,prompts=prompts,native_output_sha256=sha(raw)).model_dump(mode='json'))
    write_lines(out/'predictions.jsonl',rows)
    result={'status':'EXECUTED','backend':backend,'task':'grounded_detection' if backend in {'hf_grounding_dino','yolo_world'} else 'instance_masks',
        'samples':len(rows),'native_artifacts':raw_files,'model_assets_sha256':digest(job.model_files),'prompt_protocol_sha256':digest({'prompts':job.prompts,'groups':job.config.get('prompt_groups',[])}),'model_identity':digest({'backend':job.backend,'files':job.model_files,'config':job.config,'packages':job.package_versions}),'mask_prompt_policy':{'binary_to_logits':job.config.get('binary_mask_logit',10.0),'resampling':'nearest','native_resolution':'model_declared'},
        'elapsed_seconds':time.perf_counter()-start,'purpose':job.purpose,'pretrained_quality':'NOT_CERTIFIED',
        'packages':{name:importlib.metadata.version(name) for name in ['torch'] + (['transformers'] if backend.startswith('hf_') or backend=='sam_hf' else ['ultralytics'] if backend.startswith('yolo') or backend=='ultralytics_seg' else [])}}
    write(out/'execution.json',result);return result
if __name__=='__main__':main(run)
