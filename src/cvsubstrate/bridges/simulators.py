"""Import actual on-disk export formats without installing or launching a simulator.

The importer preserves raw metadata. It never invents camera poses, scene IDs or
asset provenance that a producer omitted. Binary input is non-pickle NumPy only.
"""
from pathlib import Path
from cvsubstrate.adoption.common import output_tree
from cvsubstrate.provenance.io import read_json,write_json,write_jsonl,file_digest,safe_join,digest

def import_simulator(kind,source,destination,*,image_root=None,mapping=None):
    source=Path(source).resolve();records=[];warnings=[]
    if kind in {'blenderproc','coco'}:
        obj=read_json(source);by: dict[object, list[dict]]={};cats={c['id']:c['name'] for c in obj['categories']}
        for a in obj['annotations']:by.setdefault(a['image_id'],[]).append(a)
        for image in obj['images']:
            records.append({'sample_id':str(image['id']),'image':image['file_name'],'width':image['width'],'height':image['height'],
                'annotations':by.get(image['id'],[]),'taxonomy':cats,'generator':kind,'source_kind':'synthetic',
                'provenance':{'annotation_source_sha256':file_digest(source),'camera':None,'scene':None,'seed':None},
                'native_image_metadata':image})
        warnings.append('COCO annotations do not identify camera/scene/seed/asset history; add producer sidecars when available')
    elif kind=='replicator':
        import numpy as np
        if not source.is_dir():raise ValueError('Replicator BasicWriter directory required')
        # BasicWriter bounding_box_2d_tight arrays and semantic label lookup.
        for arrpath in sorted(source.glob('bounding_box_2d_tight_*.npy')):
            suffix=arrpath.stem.removeprefix('bounding_box_2d_tight_')
            a=np.load(arrpath,allow_pickle=False)
            required={'semanticId','x_min','y_min','x_max','y_max'}
            if not a.dtype.names or not required<=set(a.dtype.names):raise ValueError('unsupported Replicator bounding-box dtype')
            labels_path=source/('bounding_box_2d_tight_labels_'+suffix+'.json')
            labels=read_json(labels_path) if labels_path.exists() else {}
            rows=[]
            for row in a:
                sid=int(row['semanticId']);xy=[float(row[k]) for k in ('x_min','y_min','x_max','y_max')]
                if xy[2]<xy[0] or xy[3]<xy[1]:raise ValueError('invalid native box')
                rows.append({'semantic_id':sid,'labels':labels.get(str(sid)), 'xyxy':xy,
                    'occlusion':float(row['occlusionRatio']) if 'occlusionRatio' in a.dtype.names else None})
            records.append({'sample_id':suffix,'source_kind':'synthetic','generator':'replicator_basicwriter',
                'native_boxes':rows,'box_convention':'producer pixel xyxy; verify producer version for boundary convention',
                'provenance':{'annotation_source_sha256':file_digest(arrpath),
                    'label_source_sha256':file_digest(labels_path) if labels_path.exists() else None,'camera':None,'scene':None,'seed':None}})
        if not records:raise ValueError('no supported BasicWriter bounding_box_2d_tight arrays found')
    elif kind in {'colosseum','unreal','isaac','generic'}:
        # Exact field mapping is user-controlled; do not assume an undocumented native schema.
        if mapping is None:raise ValueError('an explicit field map is required for this exporter schema')
        obj=read_json(source);rows=obj if isinstance(obj,list) else obj.get('samples',[obj])
        def pointer(value,path):
            for part in path.strip('/').split('/'):
                if not part:continue
                value=value[int(part)] if isinstance(value,list) else value.get(part)
                if value is None:return None
            return value
        for i,row in enumerate(rows):
            fields={k:pointer(row,v) for k,v in mapping.items()}
            records.append({'sample_id':str(fields.pop('sample_id',i)),'generator':kind,'source_kind':'synthetic',
                'mapped_metadata':fields,'native_metadata':row,'provenance':{'source_sha256':file_digest(source),'mapping_sha256':digest(mapping)}})
        warnings.append('User-mapped producer export; not a live simulator integration or a universal vendor schema')
    else:raise ValueError('unknown synthetic export format')
    with output_tree(destination) as out:
        write_jsonl(out/'samples.jsonl',records)
        write_json(out/'import.json',{'kind':kind,'samples':len(records),'warnings':warnings,
            'missing_is_unknown':True,'simulator_executed':False,'images_copied':False})
    return {'status':'IMPORTED','samples':len(records),'warnings':warnings,'destination':str(destination)}
