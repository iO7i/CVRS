"""Explicit native-result converters with count/coordinate provenance.

Only representation conversion is established; source model execution is unknown.
Ignored or unmapped classes are NEVER silently removed.
"""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
from cvsubstrate.contracts.models import DatasetManifest,DetectionPrediction
from cvsubstrate.contracts.research import OrientedPrediction
from cvsubstrate.geometry.polygons import rbox_to_polygon,canonical_polygon
from cvsubstrate.evaluation.metrics import validate_predictions
from cvsubstrate.provenance.io import digest,write_json,write_jsonl
from cvsubstrate.provenance.artifact_set import seal_directory
from cvsubstrate.errors import CVRSError

class PredictionConverterRegistry:
    def __init__(self):self.entries={}
    def register(self,name,fn):
        if name in self.entries:raise ValueError('duplicate converter')
        self.entries[name]=fn
    def convert(self,name,value,context):
        if name not in self.entries:raise CVRSError('CONVERTER_UNKNOWN',name)
        return self.entries[name](value,context)

def _hbb_rows(value,ctx):
    kind=ctx['format'];manifest=ctx['manifest'];split=ctx['split'];mapping=ctx['category_map'];byid={s.id:s for s in manifest.samples}
    groups=[]
    if kind=='coco':
        ids=ctx.get('image_id_map') or {};items=defaultdict(list)
        for r in value:
            native=str(r['image_id'])
            if native not in ids:raise CVRSError('IMAGE_ID_MAP','COCO image ID requires explicit mapping')
            if ids[native] not in manifest.splits[split].sample_ids:raise CVRSError('IMAGE_UNIVERSE','prediction outside selected split')
            items[ids[native]].append(r)
        for sid in manifest.splits[split].sample_ids:
            boxes=[];scores=[];labels=[]
            for r in items[sid]:
                x,y,w,h=r['bbox'];boxes.append([float(x),float(y),float(x+w),float(y+h)]);scores.append(float(r['score']));labels.append(r['category_id'])
            groups.append({'sample_id':sid,'boxes':boxes,'scores':scores,'labels':labels})
    elif kind=='mmdet2':
        for r in value:
            b=[];s=[];l=[]
            for cls,rows in enumerate(r['result']):
                for row in rows:
                    if len(row)!=5:raise ValueError('MM2 HBB row needs five values')
                    b.append(row[:4]);s.append(row[4]);l.append(cls)
            groups.append({'sample_id':r['sample_id'],'boxes':b,'scores':s,'labels':l})
    else:
        for r in value:
            data=r.get('pred_instances',r)
            groups.append({'sample_id':r['sample_id'],'boxes':data.get('bboxes',data.get('boxes',data.get('xyxy'))),'scores':data.get('scores',data.get('confidence')),'labels':data.get('labels',data.get('cls',data.get('class_id')))})
    rows=[];count=0
    for g in groups:
        sid=g['sample_id']
        if sid not in byid:raise CVRSError('SAMPLE_UNKNOWN',sid)
        if any(str(c) not in mapping for c in g['labels']):raise CVRSError('CATEGORY_MAP','unmapped native class')
        sample=byid[sid];count+=len(g['boxes'])
        rows.append(DetectionPrediction(sample_id=sid,width=sample.width,height=sample.height,boxes=g['boxes'],scores=g['scores'],
            category_ids=[mapping[str(c)] for c in g['labels']],transform_provenance={'source_format':kind,'native_execution_verified':False}))
    validate_predictions(manifest,split,rows)
    return rows,{'native_count':count,'canonical_count':sum(len(p.boxes) for p in rows),'geometry':'xywh_to_xyxy' if kind=='coco' else 'identity','class_map':mapping}

def _obb_rows(value,ctx):
    mapping=ctx['category_map'];rows=[];count=0
    for r in value:
        polys=[]
        if ctx['format']=='ultralytics_obb':polys=[canonical_polygon(p) for p in r['xyxyxyxy']]
        elif ctx['format']=='dota':polys=[canonical_polygon(p) for p in r['polygons']]
        else:
            convention=ctx.get('angle_convention')
            if not convention:raise ValueError('explicit MMRotate angle convention required')
            for b in r['boxes']:
                if len(b)!=5:raise ValueError('rbox needs cx cy w h angle')
                polys.append(rbox_to_polygon(*b,**convention))
        labels=r.get('labels',r.get('cls',r.get('category_ids')))
        if any(str(c) not in mapping for c in labels):raise ValueError('unmapped oriented class')
        rows.append(OrientedPrediction(sample_id=r['sample_id'],polygons=polys,scores=r['scores'],category_ids=[mapping[str(c)] for c in labels]));count+=len(polys)
    if len({r.sample_id for r in rows})!=len(rows):raise ValueError('duplicate oriented image')
    return rows,{'native_count':count,'canonical_count':count,'geometry':'explicit_convention_to_polygon','class_map':mapping}

def registry():
    r=PredictionConverterRegistry()
    for name in ['mmdet2','mmdet3','coco','ultralytics_hbb','rfdetr']:r.register(name,_hbb_rows)
    for name in ['mmrotate','ultralytics_obb','dota']:r.register(name,_obb_rows)
    return r

def convert_results(value,*,format,category_map,output:Path,manifest=None,split='dev',image_id_map=None,angle_convention=None):
    out=Path(output)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','new conversion output required')
    if len(set(category_map.values()))!=len(category_map):raise ValueError('category mapping must be injective')
    m=DatasetManifest.model_validate(manifest) if isinstance(manifest,dict) else manifest
    if m and m.splits[split].role=='locked_test':raise CVRSError('PROTECTED_SPLIT','use governed final evaluation, not offline import')
    rows,audit=registry().convert(format,value,{'format':format,'category_map':category_map,'manifest':m,'split':split,'image_id_map':image_id_map,'angle_convention':angle_convention})
    out.mkdir(parents=True);write_json(out/'native.json',value);write_jsonl(out/'predictions.jsonl',rows)
    audit.update(status='CONVERTED',native_digest=digest(value),execution_verified=False)
    write_json(out/'audit.json',audit);seal_directory(out);return audit
