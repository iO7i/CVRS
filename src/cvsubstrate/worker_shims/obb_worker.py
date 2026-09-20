"""Optional Ultralytics oriented inference/native training. Returns original-image corners.
No angle convention inferred from xywhr. Requires explicit local trusted weights.
"""
from pathlib import Path
import shutil,tempfile,time
from runtime_common import main,dependency,check_file,offline,write,write_lines,safe_path,sha

def native_layout(m,root,out,name,mapping):
    (out/name/'images').mkdir(parents=True);(out/name/'labels').mkdir()
    inverse={v:k for k,v in mapping.items()}
    for i,s in enumerate(m['samples']):
        filename=str(i)+Path(s['image']).suffix
        shutil.copyfile(safe_path(root,s['image']),out/name/'images'/filename)
        rows=[]
        for a in s['annotations']:
            if a.get('difficult'):raise ValueError('difficult objects require an explicit training policy; no silent dropping')
            coords=[]
            for x,y in a['polygon']:
                if not 0<=x<=s['width'] or not 0<=y<=s['height']:raise ValueError('out-of-image polygons need an explicit clipping policy before YOLO labels')
                coords.extend([x/s['width'],y/s['height']])
            rows.append(' '.join([str(inverse[a['category_id']])]+[format(v,'.17g') for v in coords]))
        (out/name/'labels'/(str(i)+'.txt')).write_text('\n'.join(rows)+'\n','utf-8')

def run(req):
    if req['operation']=='capabilities':
        return {'tasks':['obb_detection'],'operations':['predict','train'],'geometry':'original image convex quadrilateral corners','execution_verified':False,'training_contract':'native_epochs'}
    op=req['operation'];spec=req['spec'];m=req['dataset'];out=Path(req['output_dir']);out.mkdir(parents=True,exist_ok=True)
    if op not in {'predict','train'}:raise ValueError('unsupported OBB operation')
    if m['role']!='dev':raise ValueError('OBB native path requires declared dev data; it cannot bypass locked-test policy')
    if not spec.get('trust_checkpoint'):raise ValueError('native checkpoint loaders require explicit trust')
    weights=check_file(spec['checkpoint'],spec['checkpoint_sha256']);mapping={int(k):int(v) for k,v in spec['category_map'].items()}
    if len(set(mapping.values()))!=len(mapping) or not set(mapping.values())<=set(c['id'] for c in m['categories']):raise ValueError('invalid class mapping')
    for data,root in [(m,req['data_root'])]+([(req['training_dataset'],req['training_root'])] if op=='train' else []):
        for sample in data['samples']:check_file(safe_path(root,sample['image']),sample['sha256'])
    version=dependency('ultralytics',spec.get('package_version'));offline()
    from ultralytics import YOLO
    model=YOLO(str(weights),task='obb');training=None
    if op=='train':
        tm=req['training_dataset']
        if tm['role']!='train' or tm['categories']!=m['categories']:raise ValueError('explicit train role and identical taxonomy required')
        if set(mapping.values())!=set(c['id'] for c in tm['categories']) or sorted(mapping)!=list(range(len(mapping))):raise ValueError('complete contiguous native class mapping required for training')
        options=dict(spec.get('native_training',{}))
        if not isinstance(options.get('epochs'),int) or options['epochs']<=0:raise ValueError('positive native epochs required')
        if {'data','project','name','exist_ok','resume','pretrained','device','seed'}&set(options):raise ValueError('reserved native training option')
        start=time.perf_counter()
        with tempfile.TemporaryDirectory(prefix='cvrs-obb-native-') as td:
            td=Path(td);native_layout(tm,req['training_root'],td,'train',mapping);native_layout(m,req['data_root'],td,'val',mapping)
            names={c['id']:c['name'] for c in m['categories']}
            write(td/'data.yaml',{'path':str(td),'train':'train/images','val':'val/images','names':{k:names[v] for k,v in mapping.items()}})
            model.train(data=str(td/'data.yaml'),project=str(out),name='training',exist_ok=False,pretrained=False,device=spec.get('device','cpu'),seed=spec.get('seed',0),**options)
        weights=Path(model.trainer.last);model=YOLO(str(weights),task='obb')
        training={'native_epochs':options['epochs'],'wall_seconds':time.perf_counter()-start,'checkpoint':str(weights.relative_to(out)),'checkpoint_sha256':sha(weights),'source_exposures':'NOT_OBSERVED'}
    raw=[]
    for sample in m['samples']:
        result=model.predict(source=str(safe_path(req['data_root'],sample['image'])),device=spec.get('device','cpu'),conf=spec.get('confidence',.001),iou=spec.get('nms_iou',.7),imgsz=spec.get('image_size',1024),max_det=spec.get('max_detections',1000),verbose=False)[0]
        if list(result.orig_shape)!=[sample['height'],sample['width']]:raise ValueError('model original-image dimensions differ')
        if result.obb is None:raise ValueError('native model did not return oriented detections')
        labels=[int(x) for x in result.obb.cls.detach().cpu().tolist()]
        if any(x not in mapping for x in labels):raise ValueError('unmapped native class')
        raw.append({'sample_id':sample['id'],'polygons':result.obb.xyxyxyxy.detach().cpu().tolist(),'scores':result.obb.conf.detach().cpu().tolist(),'native_labels':labels,'category_ids':[mapping[x] for x in labels]})
    write_lines(out/'native-predictions.jsonl',raw)
    return {'status':'SUCCEEDED','backend':'ultralytics_obb','package_version':version,'checkpoint_sha256':sha(weights),'training':training,'predictions':'native-predictions.jsonl','scientific_certification':'NOT_ESTABLISHED'}
if __name__=='__main__':main(run)
