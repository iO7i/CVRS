"""Persistent native task drivers for bounded HBB/OBB/mask raster execution."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from runtime_common import main,offline,check_file

def run(request):
    from cvsubstrate.streaming.tasks import execute_task_stream
    from cvsubstrate.streaming.raster import StreamSpec
    from cvsubstrate.provenance.io import digest
    from cvsubstrate.vision.masks import encode_mask
    spec=dict(request['spec']);native=spec.pop('model');task=spec.pop('task','hbb');sensor=spec.pop('sensor',None);policy=spec.pop('mask_policy','winner');maxruns=spec.pop('max_mask_runs',1000000);rss=spec.pop('max_rss_bytes',None)
    checkpoint=check_file(native['checkpoint'],native['checkpoint_sha256'])
    if not native.get('trust_checkpoint'):raise ValueError('explicit local checkpoint trust required')
    spec['model_identity']=digest({k:v for k,v in native.items() if k!='checkpoint'})
    for k in ['bands','scales']:
        if k in spec:spec[k]=tuple(spec[k])
    stream=StreamSpec(**spec);stream.validate();offline()
    mask_threshold=float(native.get('mask_threshold',.5))
    if not 0<=mask_threshold<=1:raise ValueError('invalid mask threshold')
    mapping={int(k):int(v) for k,v in native['category_map'].items()};device=native.get('device','cpu');backend=native['backend']
    if backend=='ultralytics':
        if sensor:raise ValueError('Ultralytics recipe is RGB; use a declared multispectral native adapter for band-normalized tensors')
        from ultralytics import YOLO
        model=YOLO(str(checkpoint),task={'hbb':'detect','obb':'obb','masks':'segment'}[task])
        def predict(images):
            result=model.predict([im[:,:,::-1].copy() for im in images],device=device,verbose=False,retina_masks=True,conf=native.get('threshold',.001));rows=[]
            for r in result:
                instances=[]
                values=r.obb if task=='obb' else r.boxes
                if values is not None:
                    for i,(score,cat) in enumerate(zip(values.conf.cpu().tolist(),values.cls.cpu().tolist())):
                        item={'score':float(score),'category_id':mapping[int(cat)]}
                        if task=='obb':item['polygon']=values.xyxyxyxy[i].cpu().tolist()
                        elif task=='hbb':item['box']=values.xyxy[i].cpu().tolist()
                        else:
                            if r.masks is None:raise ValueError('native masks missing for boxes')
                            item['mask']=encode_mask(r.masks.data[i].cpu().numpy()>mask_threshold).model_dump(mode='json')
                        instances.append(item)
                rows.append(instances)
            return rows
    elif backend in {'native_torch','torchvision_mask'}:
        import torch
        torch.set_num_threads(int(native.get('cpu_threads',1)))
        if task=='obb':raise ValueError('owned torchvision recipe has no OBB head')
        if task=='masks':
            from cvsubstrate.vision.native_mask import build_mask_detector
            model=build_mask_detector(len(mapping)+1);model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True))
        else:
            from cvsubstrate.workers.native_torch import build_selected_model,load_owned_checkpoint
            model=build_selected_model(native.get('config',{}),len(mapping)+1);model.load_state_dict(load_owned_checkpoint(checkpoint,native['checkpoint_sha256'])['model'])
        model.to(device).eval()
        if sensor:
            if native.get('channel_names')!=sensor['model_channel_names']:raise ValueError('model must declare matching normalized channel semantics')
            input_policy=native.get('sensor_input_policy')
            if input_policy not in {'native_model_normalizes','sensor_owns_normalization'}:raise ValueError('declare sensor_input_policy to prevent accidental double normalization')
            if input_policy=='sensor_owns_normalization':model.transform.image_mean=[0.0]*len(sensor['bands']);model.transform.image_std=[1.0]*len(sensor['bands'])
            if len(sensor['bands'])!=3:raise ValueError('owned native conformance detector is three-channel; multispectral model needs supplied compatible predictor')
        def predict(images):
            tensors=[torch.from_numpy(im.copy()).float().to(device) if sensor else torch.from_numpy(im.copy()).permute(2,0,1).float().div(255).to(device) for im in images]
            with torch.inference_mode():results=model(tensors)
            rows=[]
            for v in results:
                instances=[]
                for i,(s,c) in enumerate(zip(v['scores'].cpu().tolist(),v['labels'].cpu().tolist())):
                    item={'score':float(s),'category_id':mapping[int(c)]}
                    if task=='hbb':item['box']=v['boxes'][i].cpu().tolist()
                    else:item['mask']=encode_mask(v['masks'][i,0].cpu().numpy()>mask_threshold).model_dump(mode='json')
                    instances.append(item)
                rows.append(instances)
            return rows
    else:raise ValueError('unsupported persistent native task driver')
    return execute_task_stream(stream,predict,request['output_dir'],task=task,resume=request.get('resume',False),max_tiles=request.get('max_tiles'),mask_policy=policy,max_mask_runs=maxruns,max_rss_bytes=rss,sensor=sensor)
if __name__=='__main__':main(run)
