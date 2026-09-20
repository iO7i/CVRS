"""Lossless PNG crops, explicit optional resizing/padding and auditable HBB merge."""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
from cvsubstrate.contracts.models import DatasetManifest, Sample, Split, DetectionPrediction
from cvsubstrate.contracts.research import TilingPolicy, GeoReference
from cvsubstrate.data.tiling import TileTransform, iou
from cvsubstrate.geometry.geospatial import tile_reference
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import digest, file_digest, safe_join, write_json


def axis_offsets(n: int, tile: int, overlap: int):
    if min(n,tile)<=0 or not 0<=overlap<tile:raise ValueError('invalid tile geometry')
    if n<=tile:return [0]
    v=list(range(0,n-tile+1,tile-overlap))
    if v[-1]!=n-tile:v.append(n-tile)
    return v


def plan_tiles(m: DatasetManifest, split: str, policy: TilingPolicy):
    if split not in m.splits:raise CVRSError('UNKNOWN_SPLIT','tiling split not found')
    byid={s.id:s for s in m.samples};rows=[]
    for sid in m.splits[split].sample_ids:
        s=byid[sid]
        if s.width*s.height>policy.max_source_pixels:
            raise CVRSError('SOURCE_PIXEL_LIMIT','source exceeds explicitly configured pixel/memory guard')
        index = 0
        for y in axis_offsets(s.height,policy.height,policy.overlap_y):
            for x in axis_offsets(s.width,policy.width,policy.overlap_x):
                if len(rows)>=policy.max_tiles:raise CVRSError('TILE_LIMIT','tile plan exceeds configured maximum')
                width,height=min(policy.width,s.width-x),min(policy.height,s.height-y)
                basew,baseh=(policy.width,policy.height) if policy.pad_to_tile else (width,height)
                outw,outh=policy.resize_width or basew,policy.resize_height or baseh
                tileid='tile-'+digest({'sample':sid,'index':index})[:24]
                transform=TileTransform(s.width,s.height,x,y,width,height,outw/basew,outh/baseh)
                row={'tile_id':tileid,'source_id':sid,'source_sha256':s.sha256,'index':index,
                    'crop':[x,y,width,height],'canvas_size':[basew,baseh],'output_size':[outw,outh],
                    'scale':[transform.scale_x,transform.scale_y],'padding_left_top':[0.0,0.0],
                    'valid_region':[0.0,0.0,width*transform.scale_x,height*transform.scale_y]}
                if s.geospatial is not None:
                    try:
                        geo=GeoReference.model_validate(s.geospatial)
                    except ValueError as exc:
                        raise CVRSError('GEO_CONVENTION','source geospatial metadata needs explicit GeoReference schema') from exc
                    row['geospatial']=tile_reference(geo,x,y,transform.scale_x,transform.scale_y).model_dump(mode='json')
                rows.append(row)
                index += 1
    return {'schema_version':'1.0','dataset_digest':digest(m),'split':split,'policy':policy.model_dump(mode='json'),
        'tiles':rows,'source_images':len(m.splits[split].sample_ids),
        'coordinate_semantics':'tile canvas -> inverse scale/crop -> original-image continuous xyxy'}


def materialize_tiles(m: DatasetManifest, split: str, root: Path, output: Path, policy: TilingPolicy):
    try:from PIL import Image
    except ImportError as exc:raise CVRSError('IMAGE_DEPENDENCY','Pillow needed for tile rendering') from exc
    output=Path(output)
    if output.exists():raise CVRSError('OUTPUT_EXISTS','tile output must be new')
    plan=plan_tiles(m,split,policy);output.mkdir(parents=True)
    byid={s.id:s for s in m.samples};grouped=defaultdict(list)
    for row in plan['tiles']:grouped[row['source_id']].append(row)
    samples=[]
    for sid,rows in grouped.items():
        source=byid[sid]
        with Image.open(safe_join(root,source.image)) as image:
            if image.size!=(source.width,source.height):raise CVRSError('IMAGE_DIMENSIONS','source changed dimensions')
            if image.getexif().get(274,1)!=1:raise CVRSError('EXIF_ORIENTATION','normalize orientation and labels first')
            # This path is explicitly RGB PNG/JPEG. Multispectral/radiometric data
            # require the separately configured GeoTIFF adapter, not silent RGB casting.
            if image.mode not in {'RGB','L','RGBA'}:raise CVRSError('IMAGE_MODE','explicit RGB conversion/radiometry required')
            im=image.convert('RGB')
            for row in rows:
                x,y,w,h=row['crop'];bw,bh=row['canvas_size'];ow,oh=row['output_size']
                crop=im.crop((x,y,x+w,y+h))
                if (bw,bh)!=(w,h):
                    canvas=Image.new('RGB',(bw,bh),tuple(policy.padding_rgb));canvas.paste(crop,(0,0));crop=canvas
                if (ow,oh)!=(bw,bh):crop=crop.resize((ow,oh),Image.Resampling.BILINEAR)
                rel='images/'+row['tile_id']+'.png';path=safe_join(output,rel);path.parent.mkdir(exist_ok=True)
                crop.save(path,format='PNG')
                samples.append(Sample(id=row['tile_id'],image=rel,sha256=file_digest(path),width=ow,height=oh,
                    source_kind=source.source_kind,domain=source.domain,sensor=source.sensor,
                    lineage_group=source.lineage_group or sid,parent_ids=[sid],boxes=[],geospatial=row.get('geospatial')))
    manifest=DatasetManifest(name='inference-tiles',version='1',categories=m.categories,samples=samples,
        splits={'tiles':Split(role='dev',sample_ids=[r['tile_id'] for r in plan['tiles']])},licenses=m.licenses,
        purpose=m.purpose,notes='Inference-only derived images. Ground truth remains in source manifest; do not train/evaluate quality against empty tile labels.')
    write_json(output/'dataset.json',manifest);write_json(output/'tiling_plan.json',plan)
    return manifest,plan


def merge_tile_predictions(m: DatasetManifest, split: str, plan: dict,
                           predictions: list[DetectionPrediction], policy: TilingPolicy):
    if plan['dataset_digest']!=digest(m) or plan['split']!=split or plan['policy']!=policy.model_dump(mode='json'):
        raise CVRSError('TILE_PLAN_IDENTITY','tile plan does not belong to this source data/policy')
    tiles={t['tile_id']:t for t in plan['tiles']}
    if len(tiles)!=len(plan['tiles']):raise CVRSError('DUPLICATE_TILE','tile plan has duplicate IDs')
    if len(predictions)!=len(tiles) or {p.sample_id for p in predictions}!=set(tiles):
        raise CVRSError('TILE_UNIVERSE','one prediction row is required for every planned tile, including empty output')
    byid={s.id:s for s in m.samples};grouped=defaultdict(list);events=[];validcats={c.id for c in m.categories}
    # Deterministic tile order, independent of worker response ordering.
    predmap={p.sample_id:p for p in predictions}
    for row in plan['tiles']:
        p=predmap[row['tile_id']]
        if (p.width,p.height)!=tuple(row['output_size']):raise CVRSError('TILE_DIMENSIONS','worker tile dimensions differ')
        source=byid[row['source_id']];x,y,w,h=row['crop'];sx,sy=row['scale'];pl,pt=row['padding_left_top']
        transform=TileTransform(source.width,source.height,x,y,w,h,sx,sy,pl,pt)
        vx1,vy1,vx2,vy2=row['valid_region']
        for i,(box,score,cat) in enumerate(zip(p.boxes,p.scores,p.category_ids)):
            if cat not in validcats:raise CVRSError('UNKNOWN_CATEGORY','worker output taxonomy mismatch')
            event={'source_id':source.id,'tile_id':p.sample_id,'native_index':i,'score':score,'category_id':cat,
                'original_tile_box':box}
            clipped=[max(box[0],vx1),max(box[1],vy1),min(box[2],vx2),min(box[3],vy2)]
            if clipped!=box and policy.padding_prediction_policy=='reject':
                raise CVRSError('PADDING_PREDICTION','prediction intersects invalid tile padding')
            if clipped[2]<=clipped[0] or clipped[3]<=clipped[1]:
                event['decision']='DROPPED_PADDING_ONLY';events.append(event);continue
            mapped=transform.to_source(clipped)
            mapped=[min(max(v,0.0),source.width if j%2==0 else source.height) for j,v in enumerate(mapped)]
            event.update(source_box=mapped,clipped_to_valid_region=clipped!=box,decision='CANDIDATE')
            events.append(event);grouped[source.id].append((mapped,score,cat,len(events)-1))
    result=[]
    for sid in m.splits[split].sample_ids:
        candidates=grouped[sid];kept=[]
        for i in sorted(range(len(candidates)),key=lambda j:(-candidates[j][1],j)):
            b,score,cat,event_idx=candidates[i]
            parent=next((j for j in kept if candidates[j][2]==cat and iou(b,candidates[j][0])>policy.merge_iou),None)
            if parent is None:
                kept.append(i);events[event_idx]['decision']='KEPT'
            else:
                events[event_idx].update(decision='SUPPRESSED_OVERLAP',suppressed_by_event=candidates[parent][3])
        s=byid[sid]
        result.append(DetectionPrediction(sample_id=sid,width=s.width,height=s.height,
            boxes=[candidates[k][0] for k in kept],scores=[candidates[k][1] for k in kept],category_ids=[candidates[k][2] for k in kept],
            transform_provenance={'tiling_policy_digest':digest(policy),'source_sha256':s.sha256,
                'kept_event_indices':[candidates[k][3] for k in kept],'merge':'class-aware greedy NMS; stable tile/detection tie-break'}))
    counts={key:sum(e['decision']==key for e in events) for key in ['KEPT','SUPPRESSED_OVERLAP','DROPPED_PADDING_ONLY']}
    return result,{'schema_version':'1.0','input_detections':len(events),'counts':counts,'events':events,
        'policy_digest':digest(policy),'reconciled':sum(counts.values())==len(events)}
