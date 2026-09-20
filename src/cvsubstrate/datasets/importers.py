"""Local aerial-format readers with caller-supplied complete image/split indices.

An image index is required so missing annotations never remove negative images
or reconstruct unofficial splits. No datasets are downloaded or redistributed.
"""
from __future__ import annotations
from pathlib import Path
from collections import defaultdict
import csv,xml.etree.ElementTree as ET
from cvsubstrate.contracts.models import DatasetManifest,Sample,Category,Split,Box,LicenseInfo
from cvsubstrate.data.manifest import image_dimensions,validate_manifest
from cvsubstrate.provenance.io import read_json,write_json,file_digest,safe_join,digest
from cvsubstrate.provenance.artifact_set import seal_directory
from cvsubstrate.errors import CVRSError

FORMATS={'dior','xview','visdrone','uavdt','coco','dota'}

def _xml(path):
    raw=Path(path).read_bytes()
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():raise ValueError('DTD/entities are not permitted in annotations')
    return ET.fromstring(raw)

def _rows(path):
    for line,row in enumerate(csv.reader(Path(path).read_text('utf-8-sig').splitlines()),1):
        if row and any(s.strip() for s in row):yield line,[s.strip() for s in row]

def _box(x,y,w,h,category,*,ignored=False,origin=0):
    return Box(xyxy=[float(x)-origin,float(y)-origin,float(x)+float(w)-origin,float(y)+float(h)-origin],category_id=category,ignore=ignored)

def import_dataset(spec:dict,output:Path)->dict:
    fmt=spec['format'].lower()
    if fmt not in FORMATS:raise ValueError(f'unsupported dataset format {fmt}')
    root=Path(spec['image_root']).resolve();output=Path(output)
    if output.exists():raise CVRSError('OUTPUT_EXISTS','dataset import output must be new')
    categories=[Category.model_validate(c) for c in spec['categories']];mapping={str(k):v for k,v in spec.get('category_mapping',{}).items()}
    if not mapping:mapping={c.name:c.id for c in categories}
    known={c.id for c in categories}
    if set(mapping.values())-known:raise ValueError('category mapping references unknown target')
    images=spec.get('images')
    if not images:raise ValueError('complete image index with original split membership is required')
    indexed={str(i['id']):i for i in images}
    if len(indexed)!=len(images):raise ValueError('duplicate indexed image ID')
    boxes=defaultdict(list);metadata=defaultdict(list);annotation_hashes={};polygons=defaultdict(list)
    origin=spec.get('coordinate_origin',0)
    if origin not in {0,1}:raise ValueError('coordinate_origin must be 0 or 1')
    def cat(value):
        if str(value) not in mapping:raise CVRSError('UNKNOWN_CATEGORY',str(value))
        return mapping[str(value)]
    def record(path):annotation_hashes[str(Path(path).resolve())]=file_digest(path)
    if fmt=='coco':
        ann=Path(spec['annotations']);record(ann);c=read_json(ann);cmap={str(i['id']):i for i in c['images']}
        if set(cmap)!=set(indexed):raise ValueError('COCO and supplied image universes differ')
        seen=set()
        for a in c['annotations']:
            if a['id'] in seen:raise ValueError('duplicate annotation identity')
            seen.add(a['id']);sid=str(a['image_id'])
            if sid not in indexed:raise ValueError('annotation outside image universe')
            x,y,w,h=a['bbox'];b=_box(x,y,w,h,cat(a['category_id']));b.iscrowd=bool(a.get('iscrowd',0));b.ignore=bool(a.get('ignore',0));b.area=a.get('area')
            boxes[sid].append(b);metadata[sid].append({'native_annotation':a,'segmentation_imported':False})
    elif fmt=='xview':
        ann=Path(spec['annotations']);record(ann);geo=read_json(ann)
        for f in geo['features']:
            p=f['properties'];sid=str(p['image_id'])
            # Most xView manifests identify source image by filename. Mapping stays explicit.
            sid=spec.get('image_id_mapping',{}).get(sid,sid)
            if sid not in indexed:raise ValueError('xView feature outside image index')
            raw=p.get('bounds_imcoords')
            if isinstance(raw,str):coords=[float(v) for v in raw.strip('[]').split(',') if v.strip()]
            else:coords=raw
            if not coords:metadata[sid].append({'native_feature':p,'unlocalized':True});continue
            if len(coords)!=4:raise ValueError('xView bounds need four pixel coordinates')
            x1,y1,x2,y2=coords;boxes[sid].append(_box(x1,y1,x2-x1,y2-y1,cat(p['type_id']),origin=origin));metadata[sid].append({'native_feature':p})
    elif fmt=='uavdt':
        # Native comma fields: frame,target,x,y,w,h,out-of-view,occlusion,category.
        # Override named column indices for another documented export version.
        cols={'frame':0,'target':1,'x':2,'y':3,'w':4,'h':5,'out_of_view':6,'occlusion':7,'category':8,**spec.get('columns',{})}
        by_frame={(str(i['sequence']),int(i['frame'])):str(i['id']) for i in images}
        if len(by_frame)!=len(images):raise ValueError('duplicate frame within sequence')
        for source in spec['annotation_sources']:
            ann=Path(source['path']);record(ann)
            for line,row in _rows(ann):
                if len(row)<=max(cols.values()):raise ValueError(f'UAVDT line {line}: missing columns')
                key=(str(source['sequence']),int(row[cols['frame']]))
                if key not in by_frame:raise ValueError('UAVDT annotation outside declared source/split')
                sid=by_frame[key];boxes[sid].append(_box(*(row[cols[k]] for k in ['x','y','w','h']),cat(row[cols['category']]),origin=origin))
                metadata[sid].append({'target_id':row[cols['target']],'out_of_view_code':row[cols['out_of_view']],
                    'occlusion_code':row[cols['occlusion']],'codes_are_native_not_fractions':True,'source_line':line})
    else:
        for i in images:
            sid=str(i['id']);ann=Path(i['annotation'])
            if not ann.is_file():
                if i.get('verified_empty_annotation') is True:continue
                raise CVRSError('ANNOTATION_MISSING',f'{sid}: missing is not negative; explicit verified_empty_annotation required')
            record(ann)
            if fmt=='dior':
                tree=_xml(ann)
                # VOC minimum coordinates and inclusive maxima must be declared, not guessed.
                inclusive=spec.get('inclusive_maximum')
                if not isinstance(inclusive,bool):raise ValueError('DIOR/VOC inclusive_maximum must be explicitly true/false')
                for obj in tree.findall('object'):
                    bb=obj.find('bndbox')
                    if bb is None:raise ValueError('DIOR HBB importer needs bndbox; oriented variant requires polygon importer')
                    x1,y1,x2,y2=[float(bb.findtext(k)) for k in ('xmin','ymin','xmax','ymax')]
                    difficult=obj.findtext('difficult','0')=='1';truncated=obj.findtext('truncated','0')=='1'
                    b=Box(xyxy=[x1-origin,y1-origin,x2-origin+int(inclusive),y2-origin+int(inclusive)],category_id=cat(obj.findtext('name')),ignore=difficult)
                    boxes[sid].append(b);metadata[sid].append({'difficult':difficult,'truncated':truncated,'native_ignore_preserved':True})
            elif fmt=='visdrone':
                for line,row in _rows(ann):
                    if len(row)!=8:raise ValueError(f'VisDrone detection line {line}: expected eight columns')
                    x,y,w,h,score,c,trunc,occ=row;ignored=float(score)==0 or int(c)==0
                    # Ignored regions require an explicit target category, never disappear.
                    boxes[sid].append(_box(x,y,w,h,cat(c),ignored=ignored,origin=origin))
                    metadata[sid].append({'native_score':float(score),'truncation_code':int(trunc),'occlusion_code':int(occ),
                        'native_ignore_preserved':ignored,'source_line':line})
            elif fmt=='dota':
                from cvsubstrate.data.dota import parse_dota_labels
                anns,meta=parse_dota_labels(ann,{str(k):v for k,v in mapping.items()});polygons[sid]=anns;metadata[sid].append(meta)
    output.mkdir(parents=True);samples=[];split_ids=defaultdict(list);split_roles=spec['split_roles']
    for i in images:
        sid=str(i['id']);path=safe_join(root,i['path']);w,h=image_dimensions(path)
        if i.get('width',w)!=w or i.get('height',h)!=h:raise ValueError('declared image dimensions differ')
        sn=i['split']
        if sn not in split_roles:raise ValueError('undeclared split')
        split_ids[sn].append(sid)
        if fmt=='dota':continue
        samples.append(Sample(id=sid,image=i['path'],sha256=file_digest(path),width=w,height=h,
            source_kind=i.get('source_kind',spec.get('source_kind','real')),domain=i.get('domain','unknown'),
            lineage_group=i.get('lineage_group',i.get('sequence')),boxes=boxes[sid]))
    licenses=LicenseInfo.model_validate(spec.get('licenses',{}))
    if fmt=='dota':
        from cvsubstrate.contracts.research import OrientedDataset,OrientedSample
        if len(split_ids)!=1:raise ValueError('DOTA imports preserve one explicitly selected original split per artifact')
        sn=next(iter(split_ids));os=[]
        for i in images:
            p=safe_join(root,i['path']);w,h=image_dimensions(p);sid=str(i['id'])
            os.append(OrientedSample(id=sid,image=i['path'],sha256=file_digest(p),width=w,height=h,
                annotations=polygons[sid],source_kind=i.get('source_kind','real'),lineage_group=i.get('lineage_group',i.get('sequence')),metadata={'lineage_group':i.get('lineage_group'), 'native_metadata':metadata[sid]}))
        m=OrientedDataset(name=spec['name'],version=spec['version'],categories=categories,samples=os,role=split_roles[sn],licenses=licenses,purpose=spec.get('purpose','research_dataset'))
    else:
        m=DatasetManifest(name=spec['name'],version=spec['version'],categories=categories,samples=samples,
            splits={k:Split(role=split_roles[k],sample_ids=v) for k,v in split_ids.items()},licenses=licenses,
            purpose=spec.get('purpose','research_dataset'),notes='Imported native semantics; non-crowd ignore requires a matching evaluator, never automatically COCO-equivalent.')
        validate_manifest(m,root,allow_noncrowd_ignore=True)
    write_json(output/'dataset.json',m);write_json(output/'native-metadata.json',dict(metadata))
    report={'format':fmt,'dataset_digest':digest(m),'image_root':str(root),'images':len(images),
        'annotations':sum(len(x) for x in (polygons if fmt=='dota' else boxes).values()),'original_splits':{k:len(v) for k,v in split_ids.items()},
        'annotation_hashes':annotation_hashes,'files_copied':False,'execution_certified_on_real_dataset':False,
        'materialization':'dataset image paths are relative to image_root, not this bundle; use explicit data-root binding or materialize before execution'}
    write_json(output/'import.json',report);write_json(output/'input-spec.json',spec);seal_directory(output);return report
