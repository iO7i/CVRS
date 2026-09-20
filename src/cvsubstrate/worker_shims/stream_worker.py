"""Persistent native model for a raster stream; model loads once, never per tile."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from runtime_common import main, offline, check_file, sha

def run(req):
    from cvsubstrate.streaming.raster import StreamSpec,execute_stream
    spec=dict(req['spec']);native=spec.pop('model');resume=req.get('resume',False)
    checkpoint=check_file(native['checkpoint'],native['checkpoint_sha256'])
    if not native.get('trust_checkpoint'):raise ValueError('explicit checkpoint trust required')
    from cvsubstrate.provenance.io import digest
    identity=digest({k:v for k,v in native.items() if k!='checkpoint'})
    spec['model_identity']=identity
    for key in ['scales','bands']:
        if key in spec:spec[key]=tuple(spec[key])
    stream=StreamSpec(**spec);stream.validate();offline()
    backend=native['backend'];device=native.get('device','cpu');mapping={int(k):int(v) for k,v in native['category_map'].items()}
    if backend=='ultralytics':
        from ultralytics import YOLO
        model=YOLO(str(checkpoint),task='detect')
        def predict(images):
            # Ultralytics array convention is BGR; raster is explicitly RGB.
            results=model.predict(source=[im[:,:,::-1].copy() for im in images],device=device,verbose=False,conf=native.get('threshold',.001))
            return [{'boxes':r.boxes.xyxy.cpu().tolist(),'scores':r.boxes.conf.cpu().tolist(),'category_ids':[mapping[int(c)] for c in r.boxes.cls.cpu().tolist()]} for r in results]
    elif backend=='rfdetr':
        import rfdetr
        from PIL import Image
        cls=native.get('model_class','RFDETRBase')
        if cls not in {'RFDETRBase','RFDETRLarge','RFDETRNano','RFDETRSmall','RFDETRMedium'}:raise ValueError('unsupported RF class')
        model=getattr(rfdetr,cls)(pretrain_weights=str(checkpoint),device=device)
        def predict(images):
            rows=[]
            for im in images:
                r=model.predict(Image.fromarray(im),threshold=native.get('threshold',.001))
                rows.append({'boxes':r.xyxy.tolist(),'scores':r.confidence.tolist(),'category_ids':[mapping[int(c)] for c in r.class_id]})
            return rows
    elif backend=='native_torch':
        import torch
        torch.set_num_threads(int(native.get('cpu_threads',1)))
        from cvsubstrate.workers.native_torch import build_selected_model,load_owned_checkpoint
        model=build_selected_model(native.get('config',{}),len(mapping)+1)
        saved=load_owned_checkpoint(checkpoint,native['checkpoint_sha256']);model.load_state_dict(saved['model']);model.to(device).eval()
        def predict(images):
            with torch.inference_mode():
                results=model([torch.from_numpy(im.copy()).permute(2,0,1).float().div(255).to(device) for im in images])
            rows=[]
            for r in results:
                rows.append({'boxes':r['boxes'].cpu().tolist(),'scores':r['scores'].cpu().tolist(),'category_ids':[mapping[int(x)] for x in r['labels'].cpu().tolist()]})
            return rows
    else:raise ValueError('unsupported persistent raster backend')
    return execute_stream(stream,predict,Path(req['output_dir']),resume=resume,max_tiles=req.get('max_tiles'))
if __name__=='__main__':main(run)
