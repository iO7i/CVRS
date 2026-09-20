"""Actual optional Ultralytics/RF-DETR APIs; no in-core model reimplementation.

Prediction uses native original-image boxes. Native epoch-based training is
available separately from the fixed-update source-preserving CVRS micro-trainer;
these budgets are not silently equated. No pretrained weights are downloaded.
"""
from pathlib import Path
import importlib.util,json,tempfile,shutil,time,math,contextlib
from telemetry_runtime import TrainingLedger,UltralyticsTelemetry,observe_rfdetr
from runtime_common import main,write,write_lines,check_file,dependency,offline,safe_path,sha

def capabilities(backend):
    installed=importlib.util.find_spec(backend) is not None
    return {'schema_version':'1.0','adapter':backend,'protocol_version':'1.0','installed':installed,
        'tasks':['hbb_detection'],'operations':['capabilities','validate','predict','train','export'],
        'input_formats':['cvrs_dataset_v1'],'output_formats':['cvrs_hbb_v1'],'training_contracts':['native_epochs'],
        'execution_verified_in_this_process':False,'environment':{'package':backend,'version':dependency(backend) if installed else None},
        'limitations':['Optional native library execution not certified by package presence','Native epoch training does not promise fixed-update source-preserving campaigns','Weights/configs must be local and trusted','No mask or open-vocabulary semantics are claimed']}

def validate(req,backend):
    exp=req.get('experiment') or {};m=req.get('manifest') or {};cfg=exp.get('adapter',{}).get('config',{})
    if not m.get('samples') or not m.get('splits'):raise RuntimeError('MANIFEST_REQUIRED: real canonical manifest required')
    if exp.get('training') is not None:raise RuntimeError('TRAINING_CONTRACT: native_epochs API does not implement portable fixed-update TrainingSpec; use model train-native with explicit native_training config')
    eval_split=exp.get('eval_split','dev');role=m['splits'][eval_split]['role']
    if role=='locked_test' and not req.get('final_test_authorization'):raise RuntimeError('PROTECTED_SPLIT: locked-test approval required')
    if req['operation']=='train' and role=='locked_test':raise RuntimeError('PROTECTED_SPLIT: native training never accesses locked test')
    checkpoint=req.get('checkpoint')
    if checkpoint:
        path=check_file(checkpoint['path'],checkpoint['sha256'])
        if checkpoint.get('trust')!='trusted_legacy_pickle':raise RuntimeError('CHECKPOINT_TRUST: third-party checkpoint loader requires trusted_legacy_pickle')
    elif backend=='ultralytics' and cfg.get('architecture_path'):
        path=check_file(cfg['architecture_path'],cfg.get('architecture_sha256'))
    else:raise RuntimeError('CHECKPOINT_REQUIRED: supply local hash-identified weights; no download defaults')
    category_map=cfg.get('category_map')
    if not isinstance(category_map,dict) or not category_map:raise RuntimeError('CATEGORY_MAP: explicit native-to-canonical IDs required')
    category_map={int(k):int(v) for k,v in category_map.items()}
    if len(set(category_map.values()))!=len(category_map):raise RuntimeError('CATEGORY_MAP: noninjective mapping')
    if not set(category_map.values())<=set(c['id'] for c in m['categories']):raise RuntimeError('CATEGORY_MAP: unknown canonical categories')
    root=Path(req['data_root']).resolve()
    for sample in m['samples']:check_file(safe_path(root,sample['image']),sample['sha256'])
    return exp,m,cfg,path,category_map,root

def build_model(backend,cfg,path):
    dependency(backend,cfg.get('package_version'));offline()
    if backend=='ultralytics':
        from ultralytics import YOLO
        return YOLO(str(path),task='detect')
    import rfdetr
    cls_name=cfg.get('model_class','RFDETRBase')
    if cls_name not in {'RFDETRBase','RFDETRLarge','RFDETRNano','RFDETRSmall','RFDETRMedium'}:raise RuntimeError('MODEL_CLASS: explicit supported RF-DETR class required')
    cls=getattr(rfdetr,cls_name)
    kwargs=dict(cfg.get('model_kwargs',{}));kwargs['pretrain_weights']=str(path);kwargs['device']=cfg.get('device','cpu')
    return cls(**kwargs)

def native_dataset(m,exp,root,target,backend,category_map):
    """Materialize only approved train/dev split into temporary native layout.
    Ignores/crowds rejected because native YOLO/COCO training semantics differ.
    """
    source_map: dict[str, dict[str, object]] = {}
    selected={c['id']:c['name'] for c in m['categories']};inverse={v:k for k,v in category_map.items()}
    if set(inverse)!=set(selected):raise RuntimeError('TRAINING_TAXONOMY: training requires complete explicit mapping')
    if backend=='ultralytics' and sorted(category_map)!=list(range(len(category_map))):raise RuntimeError('TRAINING_TAXONOMY: YOLO class IDs must be consecutive starting at zero')
    byid={s['id']:s for s in m['samples']};specs=[('train',exp.get('train_split','train')),('valid',exp.get('eval_split','dev'))]
    if m['splits'][specs[0][1]]['role']!='train':raise RuntimeError('TRAIN_ROLE: native training split must be train')
    for native_name,split in specs:
        if m['splits'][split]['role']=='locked_test':raise RuntimeError('PROTECTED_SPLIT: native materialization excludes locked test')
        records: list[dict[str, object]]=[];annotations: list[dict[str, object]]=[]
        image_dir=target/(native_name if backend=='rfdetr' else native_name+'/images');image_dir.mkdir(parents=True)
        if backend=='ultralytics':(target/native_name/'labels').mkdir()
        for i,sid in enumerate(m['splits'][split]['sample_ids'],1):
            s=byid[sid];filename=str(i)+Path(s['image']).suffix.lower();shutil.copyfile(safe_path(root,s['image']),image_dir/filename)
            if native_name=='train':source_map[str((image_dir/filename).resolve()) if backend=='ultralytics' else str(i)]={'sample_id':s['id'],'source':s.get('source_kind','unknown')}
            records.append({'id':i,'file_name':filename,'width':s['width'],'height':s['height']});labels=[]
            for b in s['boxes']:
                if b.get('ignore') or b.get('iscrowd'):raise RuntimeError('IGNORE_UNSUPPORTED: explicit native training policy needed; no silent dropping')
                x1,y1,x2,y2=b['xyxy'];c=inverse[b['category_id']]
                annotations.append({'id':len(annotations)+1,'image_id':i,'category_id':c,'bbox':[x1,y1,x2-x1,y2-y1],'area':(x2-x1)*(y2-y1),'iscrowd':0})
                labels.append('%d %.12g %.12g %.12g %.12g'%(c,(x1+x2)/2/s['width'],(y1+y2)/2/s['height'],(x2-x1)/s['width'],(y2-y1)/s['height']))
            if backend=='ultralytics':(target/native_name/'labels'/(str(i)+'.txt')).write_text('\n'.join(labels)+'\n',encoding='utf-8')
        if backend=='rfdetr':write(target/native_name/'_annotations.coco.json',{'info':{},'images':records,'annotations':annotations,'categories':[{'id':k,'name':selected[v],'supercategory':'object'} for k,v in sorted(category_map.items())]})
    if backend=='ultralytics':
        # JSON is valid YAML; avoids hand-quoting user paths and names.
        write(target/'data.yaml',{'path':str(target),'train':'train/images','val':'valid/images','names':{k:selected[v] for k,v in category_map.items()}})
    else:
        # RF-DETR requires a test directory. This is an explicit DEV alias,
        # never the benchmark locked test and never advertised as independent.
        shutil.copytree(target/'valid',target/'test')
    return source_map

def run(req):
    backend=req.get('service') or req.get('experiment',{}).get('adapter',{}).get('name')
    if backend not in {'ultralytics','rfdetr'}:raise RuntimeError('BACKEND_UNKNOWN: '+str(backend))
    op=req['operation']
    if op=='capabilities':return capabilities(backend)
    exp,m,cfg,path,mapping,root=validate(req,backend)
    if op=='validate':return {'status':'INPUTS_VALID','backend':backend,'weights_sha256':sha(path),'execution_verified':False}
    model=build_model(backend,cfg,path);out=Path(req['output_dir']);out.mkdir(parents=True,exist_ok=True)
    training_report=None
    if op=='train':
        native=dict(cfg.get('native_training') or {})
        if not isinstance(native.get('epochs'),int) or native['epochs']<=0:raise RuntimeError('TRAIN_BUDGET: positive native epochs required')
        forbidden={'data','dataset_dir','output_dir','project','name','exist_ok','resume','pretrained','device'}
        if forbidden&set(native):raise RuntimeError('TRAIN_ARGUMENT: native path/identity parameters are controller-owned')
        start=time.perf_counter()
        with tempfile.TemporaryDirectory(prefix='cvrs-native-dataset-') as td:
            data=Path(td);source_map=native_dataset(m,exp,root,data,backend,mapping)
            telemetry_cfg=cfg.get('telemetry',{})
            mixing=telemetry_cfg.get('mixing_policy','unobserved')
            if mixing=='disabled_or_fully_traced' and backend=='ultralytics':
                if any(native.get(k)!=0 for k in ['mosaic','mixup','copy_paste','cutmix']):raise RuntimeError('TELEMETRY_MIXING: exact recipe requires explicitly zero mosaic/mixup/copy_paste/cutmix; no silent training changes')
            ledger=TrainingLedger(out/'telemetry.sqlite',run_id=exp.get('name','native-training'),source_map=source_map,mixing_policy=mixing)
            observer=None
            if backend=='ultralytics':
                observer=UltralyticsTelemetry(ledger);observer.attach(model)
                try:model.train(data=str(data/'data.yaml'),project=str(out),name='training',exist_ok=False,pretrained=False,device=cfg.get('device','cpu'),seed=exp.get('seed',0),**native)
                finally:observer.close();telemetry_result=ledger.export(out/'telemetry');ledger.close()
                last=Path(model.trainer.last)
            else:
                try:
                    with observe_rfdetr(ledger):model.train(dataset_dir=str(data),output_dir=str(out/'training'),**native)
                finally:telemetry_result=ledger.export(out/'telemetry');ledger.close()
                candidates=[out/'training'/'checkpoint.pth',out/'training'/'checkpoint_best_total.pth']
                selected=next((p for p in candidates if p.exists()),None)
                if selected is None:raise RuntimeError('CHECKPOINT_MISSING: RF-DETR did not emit expected checkpoint')
                last=selected
        training_report={'budget_contract':'native_epochs','declared':native,'actual_wall_seconds':time.perf_counter()-start,
            'optimizer_updates':telemetry_result['optimizer_step_calls'],'source_exposures':telemetry_result['source_exposures'],'telemetry':telemetry_result,'portable_fixed_update_fairness':'NOT_CLAIMED','selected_checkpoint':str(last.relative_to(out)),'checkpoint_sha256':sha(last),
            'rf_detr_test_alias':'development validation only' if backend=='rfdetr' else None}
        write(out/'native_training.json',training_report)
        # Reload the selected emitted checkpoint rather than accidentally using
        # different EMA/in-memory weights without recording that choice.
        model=build_model(backend,cfg,last)
    elif op=='export':
        # Native libraries often write adjacent to weights: never point export at
        # the caller's original checkpoint. Operate on a private owned copy.
        copied=out/'export-input'/path.name;copied.parent.mkdir();shutil.copyfile(path,copied)
        model=build_model(backend,cfg,copied)
        options=dict(cfg.get('export',{}))
        if any(k in options for k in ['output_dir','project','name','path']):raise RuntimeError('EXPORT_PATH: destination is owned by this run')
        if backend=='ultralytics':artifact=model.export(**({'format':'onnx',**options}))
        else:artifact=model.export(output_dir=str(out/'exported'),**options)
        artifacts=[{'path':p.relative_to(out).as_posix(),'sha256':sha(p)} for p in sorted(out.rglob('*')) if p.is_file()]
        report={'status':'EXPORTED','native_result':str(artifact),'artifacts':artifacts,'accuracy_parity':'NOT_EXECUTED'}
        write(out/'export_result.json',report);return report
    elif op!='predict':raise RuntimeError('OPERATION_UNSUPPORTED: '+op)
    byid={s['id']:s for s in m['samples']};raw=[];canonical=[];start=time.perf_counter()
    for sid in m['splits'][exp.get('eval_split','dev')]['sample_ids']:
        sample=byid[sid];image=safe_path(root,sample['image'])
        if backend=='ultralytics':
            result=model.predict(source=str(image),device=cfg.get('device','cpu'),verbose=False,conf=cfg.get('score_threshold',0.001),**cfg.get('predict_kwargs',{}))[0]
            boxes=result.boxes.xyxy.detach().cpu().tolist();scores=result.boxes.conf.detach().cpu().tolist();labels=[int(x) for x in result.boxes.cls.detach().cpu().tolist()]
        else:
            detections=model.predict(str(image),threshold=cfg.get('score_threshold',0.001),**cfg.get('predict_kwargs',{}))
            boxes=detections.xyxy.tolist();scores=detections.confidence.tolist();labels=[int(x) for x in detections.class_id.tolist()]
        if any(x not in mapping for x in labels):raise RuntimeError('CATEGORY_MAP: native model emitted unmapped class')
        raw.append({'sample_id':sid,'boxes':boxes,'scores':scores,'labels':labels})
        canonical.append({'schema_version':'1.0','sample_id':sid,'width':sample['width'],'height':sample['height'],'boxes':boxes,'scores':scores,
            'category_ids':[mapping[x] for x in labels],'coordinate_frame':'original_image_xyxy','score_semantics':'native confidence, not calibrated probability',
            'transform_provenance':{'backend':backend,'native_original_image_coordinates':True}})
    write_lines(out/'upstream_predictions.jsonl',raw);write_lines(out/'predictions.jsonl',canonical)
    result={'status':'EXECUTED','backend':backend,'environment':{'package_version':dependency(backend)},'inference_seconds':time.perf_counter()-start,
        'weights_sha256':sha(last) if training_report else sha(path),'images':len(canonical),'native_detections':sum(len(r['boxes']) for r in raw),
        'canonical_detections':sum(len(r['boxes']) for r in canonical),'training':training_report,'source_exposure_accounting':telemetry_result['source_accounting'] if training_report else 'NOT_APPLICABLE',
        'evidence_artifacts':['upstream_predictions.jsonl','predictions.jsonl','execution.json']}
    write(out/'execution.json',result);return result
if __name__=='__main__':main(run)
