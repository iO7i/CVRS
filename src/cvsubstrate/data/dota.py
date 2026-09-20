"""DOTA-shaped label ingestion/export; arbitrary quadrilaterals stay polygons.

No dataset is bundled or downloaded. Difficult flags and out-of-image vertices
are retained. Dataset versions/splits and redistribution rights are user-declared.
"""
from __future__ import annotations
from pathlib import Path
import re
from cvsubstrate.contracts.models import Category,LicenseInfo
from cvsubstrate.contracts.research import OrientedAnnotation,OrientedSample,OrientedDataset,OrientedPrediction
from cvsubstrate.data.manifest import image_dimensions
from cvsubstrate.geometry.polygons import canonical_polygon
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import digest,file_digest,safe_join,write_json
from cvsubstrate.provenance.artifact_set import seal_directory


def parse_dota_labels(path:Path, category_map:dict[str,int]):
    annotations=[];metadata={}
    for number,line in enumerate(Path(path).read_text('utf-8-sig').splitlines(),1):
        line=line.strip()
        if not line:continue
        if ':' in line and len(line.split())<9:
            key,value=line.split(':',1);key=key.strip();value=value.strip()
            if key in metadata:raise ValueError('duplicate DOTA metadata field')
            metadata[key]=None if value.lower() in {'none','null','unknown',''} else value
            continue
        fields=line.split()
        if len(fields)!=10:raise ValueError(f'DOTA label line {number}: expected eight coordinates, category, difficulty')
        if fields[8] not in category_map:raise CVRSError('UNKNOWN_CATEGORY',f'DOTA category {fields[8]} not declared')
        if fields[9] not in {'0','1'}:raise ValueError('unsupported difficulty flag; it was not silently mapped')
        coords=list(map(float,fields[:8]));poly=canonical_polygon([coords[i:i+2] for i in range(0,8,2)])
        annotations.append(OrientedAnnotation(polygon=poly,category_id=category_map[fields[8]],difficult=fields[9]=='1',source_line=number))
    metadata['annotation_file_sha256']=file_digest(path)
    return annotations,metadata


def import_dota(image_root:Path,label_root:Path, *, categories:list[Category],name:str,version:str,role:str,
                source_kind='real',purpose='research_dataset',licenses:LicenseInfo|None=None):
    image_root=Path(image_root).resolve();label_root=Path(label_root).resolve();samples=[]
    mapping={c.name:c.id for c in categories}
    if len(mapping)!=len(categories):raise ValueError('duplicate category names')
    labels=sorted(label_root.glob('*.txt'))
    if not labels:raise CVRSError('DOTA_LABELS','no annotation files found; no split inferred')
    for annpath in labels:
        sid=annpath.stem
        matches=[p for p in image_root.glob(sid+'.*') if p.suffix.lower() in {'.png','.jpg','.jpeg'}]
        if len(matches)!=1:raise CVRSError('DOTA_IMAGE_IDENTITY','exactly one PNG/JPEG image required for each label file')
        image=matches[0];w,h=image_dimensions(image)
        ann,meta=parse_dota_labels(annpath,mapping)
        meta['out_of_image_vertices']=sum(not(0<=x<=w and 0<=y<=h) for a in ann for x,y in a.polygon)
        samples.append(OrientedSample(id=sid,image=image.relative_to(image_root).as_posix(),sha256=file_digest(image),
            width=w,height=h,annotations=ann,source_kind=source_kind,metadata=meta))
    return OrientedDataset(name=name,version=version,categories=categories,samples=samples,role=role,
        purpose=purpose,licenses=licenses or LicenseInfo())


def validate_oriented_dataset(m:OrientedDataset,root:Path|None=None):
    outside=0
    for s in m.samples:
        outside+=sum(not(0<=x<=s.width and 0<=y<=s.height) for a in s.annotations for x,y in a.polygon)
        if root is not None:
            p=safe_join(root,s.image)
            if file_digest(p)!=s.sha256 or image_dimensions(p)!=(s.width,s.height):
                raise CVRSError('DOTA_IMAGE_CHANGED','image hash/dimensions differ')
    return {'status':'VALID','dataset_digest':digest(m),'images':len(m.samples),
        'objects':sum(len(s.annotations) for s in m.samples),
        'difficult':sum(a.difficult for s in m.samples for a in s.annotations),
        'out_of_image_vertices_preserved':outside,'files_verified':root is not None,
        'limits':'Single declared split validated; cross-dataset/flight/near-duplicate leakage not automatically ruled out.'}


def validate_oriented_predictions(m:OrientedDataset,rows:list[OrientedPrediction]):
    expected={s.id for s in m.samples};actual=[r.sample_id for r in rows]
    if set(actual)!=expected or len(actual)!=len(expected):raise CVRSError('IMAGE_UNIVERSE','one OBB prediction row per source image required')
    cats={c.id for c in m.categories}
    if any(not set(r.category_ids).issubset(cats) for r in rows):raise CVRSError('UNKNOWN_CATEGORY','unknown oriented output category')


def export_task1(m:OrientedDataset,rows:list[OrientedPrediction],output:Path):
    if m.role!='dev':raise CVRSError('EVAL_ROLE','Task1 export here is dev-only, not a locked-test bypass')
    validate_oriented_predictions(m,rows)
    output=Path(output)
    if output.exists():raise CVRSError('OUTPUT_EXISTS','Task1 export output must be new')
    catnames={c.id:c.name for c in m.categories}
    if any(not re.fullmatch(r'[A-Za-z0-9_-]+',n) for n in catnames.values()):
        raise ValueError('Task1 filenames require explicit safe category names; no silent remapping')
    output.mkdir(parents=True);lines={c:[] for c in catnames}
    for row in rows:
        for p,s,c in zip(row.polygons,row.scores,row.category_ids):
            vals=[row.sample_id,format(s,'.17g')]+[format(v,'.17g') for pt in canonical_polygon(p) for v in pt]
            lines[c].append(' '.join(vals))
    for c,values in lines.items():(output/f'Task1_{catnames[c]}.txt').write_text('\n'.join(values)+('\n' if values else ''),'utf-8')
    result={'status':'DOTA_TASK1_FORMAT_EXPORTED','dataset_digest':digest(m),'detections':sum(map(len,lines.values())),
        'empty_categories':[catnames[c] for c,v in lines.items() if not v],
        'official_evaluator_executed':False,'note':'Empty classes stay empty; never fabricate detections to satisfy a submission server.'}
    write_json(output/'export.json',result);seal_directory(output)
    return result
