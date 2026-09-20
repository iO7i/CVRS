"""Bind canonical manifests to a finite native CocoDataset training recipe.

Images are not copied or modified. Their hashes are checked and canonical labels
are exported with explicit native image-ID/source maps. Composite/mixed-image
native datasets need their own recipe rather than being silently flattened.
"""
from pathlib import Path
from cvsubstrate.contracts.models import DatasetManifest
from cvsubstrate.provenance.io import read_json,write_json,file_digest,digest,safe_join


def bind_coco_training(config,job,output,backend):
    manifest_path=Path(job['dataset_manifest']).resolve()
    manifest=DatasetManifest.model_validate(read_json(manifest_path))
    if digest(manifest)!=job['dataset_sha256']:
        raise ValueError('native stage dataset digest does not match canonical manifest')
    root=Path(job.get('data_root',manifest_path.parent)).resolve()
    train=job.get('train_split','train');dev=job.get('eval_split','dev')
    if train not in manifest.splits or dev not in manifest.splits:raise ValueError('native stage split missing')
    if manifest.splits[train].role!='train' or manifest.splits[dev].role not in {'dev','selection'}:
        raise ValueError('native training only consumes train and dev/selection roles')
    native_map={int(k):int(v) for k,v in job['category_map'].items()}
    categories={c.id:c.name for c in manifest.categories}
    if sorted(native_map)!=list(range(len(categories))) or set(native_map.values())!=set(categories):
        raise ValueError('MM training recipe requires consecutive native labels and a complete category bijection')
    names=tuple(categories[native_map[i]] for i in sorted(native_map));samples={s.id:s for s in manifest.samples}
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    exports={};source_map={}
    for label,split in [('train',train),('validation',dev)]:
        images=[];annotations=[]
        original_ids=manifest.splits[split].sample_ids
        selected_ids=[sid for sid in original_ids if label!='train' or job.get('source') not in {'real','synthetic'} or samples[sid].source_kind==job['source']]
        if not selected_ids:raise ValueError('native stage source/split has no selected samples')
        for image_id,sid in enumerate(selected_ids,1):
            sample=samples[sid];image=safe_join(root,sample.image)
            if file_digest(image)!=sample.sha256:raise ValueError('native image hash mismatch: '+sid)
            if label=='train' and job.get('source') in {'real','synthetic'} and sample.source_kind!=job['source']:
                raise ValueError('stage source declaration differs from actual sample: '+sid)
            images.append({'id':image_id,'file_name':sample.image,'width':sample.width,'height':sample.height})
            for box in sample.boxes:
                x1,y1,x2,y2=box.xyxy
                annotations.append({'id':len(annotations)+1,'image_id':image_id,'category_id':box.category_id,
                    'bbox':[x1,y1,x2-x1,y2-y1],'area':(x2-x1)*(y2-y1),'iscrowd':int(box.iscrowd),'ignore':int(box.ignore)})
            if label=='train':
                member={'sample_id':sid,'source':sample.source_kind}
                for native_id in [str(image_id),sample.image,str(image),image.as_posix()]:source_map[native_id]=member
        path=output/(label+'.coco.json')
        write_json(path,{'info':{'cvrs_dataset_sha256':digest(manifest),'split':split},'images':images,'annotations':annotations,
                         'categories':[{'id':c.id,'name':c.name} for c in manifest.categories]})
        exports[label]={'path':str(path.resolve()),'sha256':file_digest(path),'split':split,'sample_ids':selected_ids,'excluded_by_explicit_source':[sid for sid in original_ids if sid not in selected_ids]}
    def patch_dataset(original,label):
        if not isinstance(original,dict) or original.get('type') not in {'CocoDataset','mmdet.CocoDataset'}:
            raise ValueError('finite native training recipe supports a direct CocoDataset; supply an explicit composite-dataset recipe')
        node=dict(original)
        if 'seg_prefix' in node or 'seg_map_suffix' in node:raise ValueError('this stage recipe is HBB detection, not semantic-mask training')
        node['ann_file']=exports[label]['path']
        if backend=='mmdet2':node['img_prefix']=str(root)+ '/';node['classes']=names
        else:node['data_root']=str(root);node['data_prefix']={'img':''};node['metainfo']={**node.get('metainfo',{}),'classes':names}
        return node
    if backend=='mmdet2':
        config.data.train=patch_dataset(config.data.train,'train')
        config.data.val=patch_dataset(config.data.val,'validation')
        if config.data.get('test'):config.data.test=patch_dataset(config.data.test,'validation')
    else:
        config.train_dataloader.dataset=patch_dataset(config.train_dataloader.dataset,'train')
        config.val_dataloader.dataset=patch_dataset(config.val_dataloader.dataset,'validation')
        if config.get('test_dataloader'):
            config.test_dataloader.dataset=patch_dataset(config.test_dataloader.dataset,'validation')
        for key in ['val_evaluator','test_evaluator']:
            evaluator=config.get(key)
            if evaluator is None:continue
            values=evaluator if isinstance(evaluator,list) else [evaluator]
            for entry in values:
                if entry.get('type') not in {'CocoMetric','mmdet.CocoMetric'}:raise ValueError('native evaluator needs explicit dataset-binding recipe')
                entry['ann_file']=exports['validation']['path']
    receipt={'dataset_sha256':digest(manifest),'native_category_map':{str(k):v for k,v in native_map.items()},'classes':names,'exports':exports,
             'source_map':source_map,'sampling_semantics':'native loader owns filtering/shuffling; measured telemetry, not inferred equal exposures'}
    write_json(output/'binding.json',receipt)
    return receipt
