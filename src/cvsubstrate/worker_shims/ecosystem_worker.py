"""Standalone native ecosystem bridge. Python >=3.8; no controller imports.

All SDKs are optional, imported only for the requested operation. Network access
requires explicit permission; local loopback is allowed for local databases.
"""
from pathlib import Path
import os,sys,json,hashlib,socket,importlib,importlib.metadata,math
from runtime_common import main,read,write,sha,check_file,write_lines

def local_only():
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',WANDB_MODE='offline',YOLO_AUTOINSTALL='false')
    original=socket.socket.connect
    def connect(sock,address):
        if not isinstance(address,tuple):return original(sock,address)
        host=address[0]
        if host not in {'localhost','127.0.0.1','::1'}:raise RuntimeError('NETWORK_DISABLED: remote SDK connection denied')
        return original(sock,address)
    socket.socket.connect=connect

def tensor_json(x):
    if hasattr(x,'detach'):return x.detach().cpu().tolist()
    if hasattr(x,'tolist'):return x.tolist()
    if isinstance(x,dict):return {str(k):tensor_json(v) for k,v in x.items()}
    if isinstance(x,(tuple,list)):return [tensor_json(v) for v in x]
    if x is None or isinstance(x,(str,int,float,bool)):return x
    return str(x)

def handle(req):
    p=req['payload'];out=Path(req['output_dir']);out.mkdir(parents=True,exist_ok=True)
    net=req.get('allow_network',False)
    if not net:local_only()
    else:
        for key in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE'):os.environ.pop(key,None)
    name=req['bridge'];op=req['operation']
    if name=='supervision':
        import numpy as np,supervision as sv
        if op=='export':
            b=read(p['bundle']);rows=[]
            for s in b['samples']:
                pred=s.get('prediction')
                if pred is None:continue
                d=sv.Detections(xyxy=np.asarray(pred['boxes'],dtype=float).reshape(-1,4),confidence=np.asarray(pred['scores'],dtype=float),class_id=np.asarray(pred['category_ids'],dtype=int))
                rows.append({'sample_id':s['id'],'width':s['width'],'height':s['height'],'xyxy':d.xyxy.tolist(),'confidence':d.confidence.tolist(),'class_id':d.class_id.tolist()})
            write(out/'supervision.json',{'format':'supervision_arrays_v1','records':rows,'categories':b['categories'],'cvrs_dataset_digest':b['dataset_digest']})
        else:
            b=read(p['input']);rows=[]
            for r in b['records']:
                d=sv.Detections(xyxy=np.asarray(r['xyxy'],dtype=float).reshape(-1,4),confidence=np.asarray(r['confidence'],dtype=float),class_id=np.asarray(r['class_id'],dtype=int))
                rows.append({'schema_version':'1.0','sample_id':r['sample_id'],'width':r['width'],'height':r['height'],
                    'boxes':d.xyxy.tolist(),'scores':d.confidence.tolist(),'category_ids':d.class_id.tolist(),'coordinate_frame':'original_image_xyxy'})
            write_lines(out/'predictions.jsonl',rows)
        return {'status':'CONVERTED','records':len(rows),'losses':[],'task':'hbb_detection','version':importlib.metadata.version('supervision')}
    if name=='fiftyone':
        import fiftyone as fo
        if op=='export':
            b=read(p['bundle']);classes={c['id']:c['name'] for c in b['categories']}
            ds=fo.Dataset(name=p.get('dataset_name'))
            for r in b['samples']:
                check_file(r['image'],r['image_sha256'])
                sample=fo.Sample(filepath=r['image'],metadata=fo.ImageMetadata(width=r['width'],height=r['height']))
                sample['cvrs_sample_id']=r['id'];sample['cvrs_dataset_digest']=b['dataset_digest'];sample['cvrs_metadata']=r.get('metadata',{})
                def label(box,cid,score=None,extra=None):
                    x1,y1,x2,y2=box
                    return fo.Detection(label=classes[cid],bounding_box=[x1/r['width'],y1/r['height'],(x2-x1)/r['width'],(y2-y1)/r['height']],confidence=score,
                                        cvrs_category_id=cid,**(extra or {}))
                sample['ground_truth']=fo.Detections(detections=[label(x['xyxy'],x['category_id'],extra={'iscrowd':x.get('iscrowd',False),'ignore':x.get('ignore',False)}) for x in r['ground_truth']])
                pred=r.get('prediction')
                if pred:sample['predictions']=fo.Detections(detections=[label(box,cid,score) for box,cid,score in zip(pred['boxes'],pred['category_ids'],pred['scores'])])
                ds.add_sample(sample)
            ds.export(export_dir=str(out/'fiftyone'),dataset_type=fo.types.FiftyOneDataset,export_media=False)
            write(out/'source-metadata.json',{'dataset_digest':b['dataset_digest'],'categories':b['categories'],'licenses':b.get('licenses',{})})
            return {'dataset_name':ds.name,'samples':len(ds),'media_copied':False,'losses':[],'note':'native FiftyOne database is local; media remain explicit external references'}
        ds=fo.load_dataset(p['dataset_name']);mapping=p['category_mapping'];rows=[]
        for s in ds:
            width=s.metadata.width;height=s.metadata.height;boxes=[];scores=[];cats=[]
            detections=s[p.get('field','predictions')]
            for d in detections.detections if detections else []:
                if d.label not in mapping:raise ValueError('unmapped class '+d.label)
                x,y,w,h=d.bounding_box;boxes.append([x*width,y*height,(x+w)*width,(y+h)*height]);scores.append(float(d.confidence));cats.append(mapping[d.label])
            rows.append({'schema_version':'1.0','sample_id':s['cvrs_sample_id'],'width':width,'height':height,'boxes':boxes,'scores':scores,'category_ids':cats})
        write_lines(out/'predictions.jsonl',rows);return {'samples':len(rows),'task':'hbb_detection','losses':[]}
    if name=='wandb':
        os.environ['WANDB_CACHE_DIR']=str(out/'wandb-cache');os.environ['WANDB_DATA_DIR']=str(out/'wandb-data')
        os.environ['WANDB_CONFIG_DIR']=str(out/'wandb-config')
        import wandb
        if op=='import':
            if not net:raise RuntimeError('NETWORK_DISABLED: remote W&B artifact import requires opt-in')
            api=wandb.Api();artifact=api.artifact(p['artifact'])
            if not (':' in p['artifact'] and p['artifact'].rsplit(':',1)[1].startswith('v')):raise ValueError('use an immutable vN W&B artifact reference')
            artifact.download(root=str(out/'artifact'));return {'artifact':p['artifact'],'digest':artifact.digest}
        data=read(p['run_metadata'])
        with wandb.init(project=p.get('project','cvrs'),entity=p.get('entity'),dir=str(out),mode='online' if net else 'offline',config=data.get('parameters',{}),tags=['cvrs']) as run:
            run.log(data.get('metrics',{}))
            artifact=wandb.Artifact(p.get('artifact_name','cvrs-evidence'),type='cvrs-evidence',metadata=data.get('identities',{}))
            for path in p.get('approved_files',[]):
                path=Path(path);artifact.add_file(str(path),name=path.name)
            run.log_artifact(artifact)
            result={'run_id':run.id,'mode':'online' if net else 'offline','url':run.url if net else None}
        return result
    if name=='mlflow':
        import mlflow
        uri=p.get('tracking_uri','sqlite:///'+str(out/'mlflow.db'))
        if not net and uri.startswith(('http:','https:','databricks')):raise RuntimeError('NETWORK_DISABLED: remote tracking needs opt-in')
        mlflow.set_tracking_uri(uri)
        if op=='import':
            client=mlflow.tracking.MlflowClient();run=client.get_run(p['run_id'])
            write(out/'mlflow-run.json',{'run_id':run.info.run_id,'metrics':run.data.metrics,'params':run.data.params,'tags':run.data.tags})
            return {'run_id':run.info.run_id,'imported':'metadata_only'}
        data=read(p['run_metadata']);mlflow.set_experiment(p.get('experiment','cvrs'))
        with mlflow.start_run(run_name=p.get('run_name')) as run:
            mlflow.log_params(data.get('parameters',{}));mlflow.log_metrics(data.get('metrics',{}))
            mlflow.set_tags({str(k):str(v) for k,v in data.get('identities',{}).items()})
            for path in p.get('approved_files',[]):mlflow.log_artifact(path,artifact_path='cvrs')
            if p.get('registered_model'):
                if not p.get('model_uri'):raise ValueError('model registration needs an explicit existing MLflow model URI')
                mlflow.register_model(p['model_uri'],p['registered_model'])
            return {'run_id':run.info.run_id,'tracking_uri':uri,'registered_model':p.get('registered_model')}
    if name=='dvc':
        import dvc.api
        if not p.get('rev') or p['rev'] in {'main','master','latest'}:raise ValueError('DVC revision must be pinned')
        if op=='inspect':
            url=dvc.api.get_url(p['path'],repo=p['repo'],rev=p['rev'])
            write(out/'dvc-reference.json',{'repo':p['repo'],'revision':p['rev'],'path':p['path'],'url':url})
            return {'status':'REFERENCE_RESOLVED','data_fetched':False}
        expected=p['sha256'];target=out/'data.bin';total=0
        with dvc.api.open(p['path'],repo=p['repo'],rev=p['rev'],mode='rb') as source,target.open('wb') as dest:
            while True:
                chunk=source.read(1024*1024)
                if not chunk:break
                total+=len(chunk)
                if total>p.get('max_bytes',1024**3):raise ValueError('DVC byte budget exceeded')
                dest.write(chunk)
        check_file(target,expected);return {'sha256':sha(target),'bytes':total}
    if name=='openml':
        if not net:raise RuntimeError('NETWORK_DISABLED: OpenML metadata fetch needs opt-in')
        import openml
        if os.environ.get('OPENML_API_KEY'):openml.config.apikey=os.environ['OPENML_API_KEY']
        if op=='import':
            run=openml.runs.get_run(int(p['run_id']))
            value={'run_id':run.run_id,'task_id':run.task_id,'flow_id':run.flow_id,'evaluations':tensor_json(getattr(run,'evaluations',{})),
                'predictions_url':getattr(run,'predictions_url',None),'imported':'native run metadata; no CV task equivalence assumed'}
            write(out/'openml-run.json',value);return value
        task=openml.tasks.get_task(int(p['task_id']),download_data=False,download_splits=False)
        value={'task_id':task.task_id,'task_type_id':task.task_type_id,'dataset_id':task.dataset_id,
               'evaluation_measure':getattr(task,'evaluation_measure',None),
               'cvrs_mapping':'EXPLICIT_TASK_MAPPING_REQUIRED; no arbitrary CV task is claimed OpenML-compatible'}
        write(out/'openml-task.json',value);return value
    if name=='torchgeo':
        import torchgeo.datasets as datasets
        import numpy as np
        cls=getattr(datasets,p['dataset_class']);kwargs=dict(p.get('kwargs',{}))
        if kwargs.get('download'):raise ValueError('supply local TorchGeo data; no implicit dataset downloads')
        dataset=cls(**kwargs)
        if op=='inspect':return {'class':p['dataset_class'],'length':len(dataset),'crs':str(getattr(dataset,'crs',None)),
                               'bounds':str(getattr(dataset,'bounds',None)),'bands':tensor_json(getattr(dataset,'bands',None))}
        queries=p.get('queries',[])
        if p.get('sampler'):
            import torch
            from torchgeo.samplers import GridGeoSampler,RandomGeoSampler
            torch.manual_seed(p.get('seed',0));sam=p['sampler']
            if sam['kind']=='grid':queries=GridGeoSampler(dataset,size=sam['size'],stride=sam['stride'])
            elif sam['kind']=='random':queries=RandomGeoSampler(dataset,size=sam['size'],length=sam['length'])
            else:raise ValueError('unsupported TorchGeo sampler')
        records=[]
        for i,q in enumerate(queries):
            if i>=p.get('max_samples',1000):break
            if isinstance(q,list):q=datasets.BoundingBox(*q)
            sample=dataset[q];record={'index':i,'query':str(q),'metadata':{k:tensor_json(v) for k,v in sample.items() if k not in {'image','mask'}}}
            for k in ('image','mask'):
                if k in sample:
                    arr=sample[k].detach().cpu().numpy() if hasattr(sample[k],'detach') else np.asarray(sample[k]);fn=str(i)+'-'+k+'.npy';np.save(out/fn,arr,allow_pickle=False)
                    record[k]={'path':fn,'sha256':sha(out/fn),'shape':list(arr.shape),'dtype':str(arr.dtype)}
            records.append(record)
        write(out/'torchgeo-samples.json',{'samples':records,'source':p['dataset_class'],'license':p.get('license','unknown')})
        return {'samples':len(records),'format':'explicit native arrays and geospatial metadata'}
    if name=='terratorch':
        # Load the installed public console entry point rather than guessing internal class names.
        config=check_file(p['config'],p['config_sha256'])
        eps=importlib.metadata.entry_points()
        entries=list(eps.select(group='console_scripts',name='terratorch')) if hasattr(eps,'select') else [e for e in eps.get('console_scripts',[]) if e.name=='terratorch']
        if len(entries)!=1:raise RuntimeError('ENTRYPOINT_UNAVAILABLE: installed TerraTorch has no unambiguous CLI')
        command='fit' if op=='train' else 'predict'
        sys.argv=['terratorch',command,'--config',str(config),'--trainer.default_root_dir',str(out/'native')]
        if p.get('checkpoint'):sys.argv+=['--ckpt_path',str(check_file(p['checkpoint'],p['checkpoint_sha256']))]
        sys.argv+=p.get('extra_args',[])
        try:entries[0].load()()
        except SystemExit as exc:
            if exc.code not in (0,None):raise RuntimeError('native TerraTorch entrypoint failed')
        return {'operation':command,'config_sha256':sha(config),'native_output':'native','output_semantics':'native TerraTorch output, canonical decoder must be declared for the selected task'}
    if name=='timm':
        import timm
        model=timm.create_model(p['model_name'],pretrained=False,features_only=True)
        if p.get('checkpoint'):
            import torch
            ck=check_file(p['checkpoint'],p['checkpoint_sha256']);state=torch.load(ck,map_location='cpu',weights_only=True)
            model.load_state_dict(state,strict=True)
        return {'model_name':p['model_name'],'channels':model.feature_info.channels(),'strides':model.feature_info.reduction(),
                'pretrained_tag':p.get('pretrained_tag'),'weights_sha256':p.get('checkpoint_sha256'),'pretrained_download':False}
    if name=='hf':
        if not net:raise RuntimeError('NETWORK_DISABLED: use local-lock without network')
        from huggingface_hub import HfApi,hf_hub_download
        api=HfApi();info=api.repo_info(p['repo_id'],repo_type=p.get('repo_type','model'),revision=p.get('revision','main'),files_metadata=True)
        result={'repo_id':p['repo_id'],'requested_revision':p.get('revision','main'),'resolved_revision':info.sha,'files':[]}
        if op=='lock' and not p.get('license_acknowledgement'):raise ValueError('record explicit license acknowledgement for the model before downloading')
        if op=='lock' and not p.get('filenames'):raise ValueError('Explicit filename allowlist required for downloads')
        selected=[f for f in info.siblings or [] if not p.get('filenames') or f.rfilename in p['filenames']]
        if op=='lock' and (any(getattr(f,'size',None) is None for f in selected) or sum(f.size for f in selected)>p.get('max_download_bytes',1073741824)):
            raise ValueError('Unknown or excessive download size; explicitly prepare assets through the checksum manager')
        for f in selected:
            if p.get('filenames') and f.rfilename not in p['filenames']:continue
            row={'filename':f.rfilename,'size':getattr(f,'size',None),'git_blob_id':getattr(f,'blob_id',None)}
            if op=='lock':
                if not p.get('acknowledge_download'):raise ValueError('lock downloads selected files and requires acknowledgement')
                path=hf_hub_download(p['repo_id'],f.rfilename,revision=info.sha,repo_type=p.get('repo_type','model'))
                row['sha256']=sha(path)
            result['files'].append(row)
        write(out/'hf-lock.json',result);return result
    raise ValueError('unknown bridge '+name)

if __name__=='__main__':main(handle)
