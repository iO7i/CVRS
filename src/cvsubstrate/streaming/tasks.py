"""Transactional HBB/quad/mask raster streams with disk-backed spatial merging.

All complete tile records are committed before being reused. Native predictors
remain callables loaded in a worker; no simulator/model is reimplemented here.
Mask union is a declared greedy association policy, not perfect instance tracking.
"""
from __future__ import annotations
import json,math,sqlite3,time
from pathlib import Path
from dataclasses import asdict
from cvsubstrate.streaming.raster import StreamSpec,RasterSource,plan_tiles
from cvsubstrate.provenance.io import digest,file_digest,write_json
from cvsubstrate.contracts.frontier import MaskRLE
from cvsubstrate.vision.sparse_masks import place,bounds,union
from cvsubstrate.vision.masks import mask_iou
from cvsubstrate.geometry.polygons import polygon_iou
from cvsubstrate.foundation.lifecycle import process_lock

class SpatialPredictionIndex:
    def __init__(self,path,identity,*,cache_kib=2048):
        self.db=sqlite3.connect(path);self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA temp_store=FILE')
        self.db.execute(f'PRAGMA cache_size=-{int(cache_kib)}')
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY,v TEXT);
        CREATE TABLE IF NOT EXISTS tiles(id TEXT PRIMARY KEY,payload TEXT,digest TEXT);
        CREATE TABLE IF NOT EXISTS predictions(id INTEGER PRIMARY KEY,tile TEXT,ordinal INTEGER,score REAL,category INTEGER,payload TEXT);
        CREATE INDEX IF NOT EXISTS score_order ON predictions(score DESC,tile,ordinal);
        CREATE TABLE IF NOT EXISTS selected(id INTEGER PRIMARY KEY,score REAL,category INTEGER,payload TEXT);
        CREATE VIRTUAL TABLE IF NOT EXISTS spatial USING rtree(id,minx,maxx,miny,maxy);
        """)
        prior=self.db.execute("SELECT v FROM meta WHERE k='identity'").fetchone()
        if prior and prior[0]!=identity:self.db.close();raise ValueError('STREAM_IDENTITY_MISMATCH')
        with self.db:self.db.execute("INSERT OR IGNORE INTO meta VALUES('identity',?)",(identity,))
    def close(self):self.db.close()
    def done(self,tid):
        row=self.db.execute('SELECT payload,digest FROM tiles WHERE id=?',(tid,)).fetchone()
        if not row:return False
        payload=json.loads(row[0])
        if digest(payload)!=row[1]:raise ValueError('TILE_INTEGRITY_MISMATCH')
        actual=[json.loads(r[0]) for r in self.db.execute('SELECT payload FROM predictions WHERE tile=? ORDER BY ordinal',(tid,))]
        if actual!=payload['predictions']:raise ValueError('TILE_PREDICTIONS_CHANGED')
        return True
    def insert_tile(self,tile,raw,rows,valid_fraction=None):
        payload={'tile':asdict(tile),'raw':raw,'predictions':rows,'valid_pixel_fraction':valid_fraction,'nodata_policy':'masked input filled; outputs retained without implicit annotation filtering'}
        with self.db:
            self.db.execute('INSERT INTO tiles VALUES(?,?,?)',(tile.id,json.dumps(payload,allow_nan=False),digest(payload)))
            for ordinal,row in enumerate(rows):
                self.db.execute('INSERT INTO predictions(tile,ordinal,score,category,payload) VALUES(?,?,?,?,?)',(tile.id,ordinal,row['score'],row['category_id'],json.dumps(row,allow_nan=False)))
    @staticmethod
    def box(row):
        if row['task']=='masks':return bounds(MaskRLE.model_validate(row['mask']))
        if row['task']=='obb':
            p=row['polygon'];return [min(x[0] for x in p),min(x[1] for x in p),max(x[0] for x in p),max(x[1] for x in p)]
        return row['box']
    def _insert_selected(self,i,row):
        b=self.box(row)
        if b is None:return
        self.db.execute('INSERT INTO selected VALUES(?,?,?,?)',(i,row['score'],row['category_id'],json.dumps(row,allow_nan=False)))
        self.db.execute('INSERT INTO spatial VALUES(?,?,?,?,?)',(i,b[0],b[2],b[1],b[3]))
    def query_overlap(self,b,category):
        return self.db.execute('SELECT s.id,s.payload FROM spatial r JOIN selected s ON s.id=r.id WHERE r.maxx>=? AND r.minx<=? AND r.maxy>=? AND r.miny<=? AND s.category=? ORDER BY s.score DESC,s.id',(b[0],b[2],b[1],b[3],category))
    def merge(self,*,threshold,mask_policy='winner',max_mask_runs=1000000):
        if not 0<threshold<=1 or mask_policy not in {'winner','union'}:raise ValueError('invalid merge policy')
        with self.db:
            self.db.execute('DELETE FROM selected');self.db.execute('DELETE FROM spatial')
            cursor=self.db.execute('SELECT id,payload FROM predictions ORDER BY score DESC,tile,ordinal')
            for ident,payload in cursor:
                row=json.loads(payload);b=self.box(row)
                if b is None:continue
                matched=None
                for candidate,other_payload in self.query_overlap(b,row['category_id']):
                    other=json.loads(other_payload)
                    if row['task']=='masks':
                        # Never collapse two distinct instances from the same native tile.
                        if set(row['tiles'])&set(other['tiles']):continue
                        overlap=mask_iou(MaskRLE.model_validate(row['mask']),MaskRLE.model_validate(other['mask']))
                    elif row['task']=='obb':overlap=polygon_iou(row['polygon'],other['polygon'])
                    else:
                        a=other['box'];inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]));total=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter;overlap=inter/total if total else 0
                    if overlap>threshold:matched=(candidate,other);break
                if matched is None:self._insert_selected(ident,row)
                elif row['task']=='masks' and mask_policy=='union':
                    candidate,other=matched
                    other['mask']=union([MaskRLE.model_validate(other['mask']),MaskRLE.model_validate(row['mask'])],max_mask_runs).model_dump(mode='json')
                    other['tiles']=sorted(set(other['tiles'])|set(row['tiles']));other['members']+=row['members']
                    self.db.execute('DELETE FROM spatial WHERE id=?',(candidate,));self.db.execute('DELETE FROM selected WHERE id=?',(candidate,));self._insert_selected(candidate,other)
        return self.db.execute('SELECT count(*) FROM selected').fetchone()[0]
    def export(self,path):
        from cvsubstrate.provenance.io import canonical_bytes
        path=Path(path)
        if path.exists():raise ValueError('export would overwrite evidence')
        with path.open('xb') as f:
            for ident,payload in self.db.execute('SELECT id,payload FROM selected ORDER BY score DESC,id'):
                row=json.loads(payload);row['instance_id']='instance-'+str(ident);f.write(canonical_bytes(row)+b'\n')

    def export_canonical(self,path,*,task,sample_id,width,height,source_digest,merge_policy):
        """Stream one original-image prediction object without collecting the scene."""
        from cvsubstrate.provenance.io import canonical_bytes
        path=Path(path)
        with path.open('xb') as f:
            header={'schema_version':'1.0','sample_id':sample_id}
            if task in {'hbb','masks'}:header.update(width=width,height=height)
            if task=='hbb':header.update(coordinate_frame='original_image_xyxy',score_semantics='native detection confidence; not calibrated probability',transform_provenance={'source_sha256':source_digest,'merge_policy':merge_policy,'instance_lineage':'predictions JSONL plus tiles.sqlite'})
            if task=='obb':header['convention']='continuous_pixel_xy_clockwise_convex_quadrilateral'
            if task=='masks':header.update(prompts=[],selection_policy='single_native_output')
            f.write(canonical_bytes(header)[:-1])
            def array(name,convert):
                f.write(b','+canonical_bytes(name)+b':[');first=True
                for ident,payload in self.db.execute('SELECT id,payload FROM selected ORDER BY score DESC,id'):
                    row=json.loads(payload);value=convert(ident,row)
                    if not first:f.write(b',')
                    f.write(canonical_bytes(value));first=False
                f.write(b']')
            if task=='hbb':array('boxes',lambda i,r:r['box'])
            elif task=='obb':array('polygons',lambda i,r:r['polygon'])
            if task in {'hbb','obb'}:
                array('scores',lambda i,r:r['score']);array('category_ids',lambda i,r:r['category_id'])
            else:
                array('instances',lambda i,r:{'schema_version':'1.0','id':'instance-'+str(i),'mask':r['mask'],'score':r['score'],'score_kind':'detection_confidence','score_semantics':'native detection confidence; not calibrated probability','category_id':r['category_id'],'prompt_id':None})
            f.write(b'}\n')

    def export_world(self,path,transform,crs):
        """GeoJSON features in the declared source CRS; not implicit WGS84."""
        from cvsubstrate.provenance.io import canonical_bytes
        from affine import Affine
        t=Affine(*transform[:6])
        with Path(path).open('xb') as f:
            f.write(b'{"type":"FeatureCollection","cvrs_source_crs":'+canonical_bytes(crs)+b',"features":[');first=True
            for ident,payload in self.db.execute('SELECT id,payload FROM selected ORDER BY score DESC,id'):
                row=json.loads(payload);b=self.box(row)
                if b is None:continue
                if row['task']=='obb':p=row['polygon']
                else:p=[[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]]]
                ring=[list(t*(x,y)) for x,y in p];ring.append(ring[0])
                feature={'type':'Feature','id':'instance-'+str(ident),'geometry':{'type':'Polygon','coordinates':[ring]},'properties':{'category_id':row['category_id'],'score':row['score'],'geometry_semantics':'instance_bounds' if row['task']=='masks' else 'detection_polygon','pixel_prediction_task':row['task']}}
                if not first:f.write(b',')
                f.write(canonical_bytes(feature));first=False
            f.write(b']}\n')

class ResourceBudget:
    def __init__(self,*,max_inflight,max_decoded_pixels,max_prediction_bytes,max_rss_bytes=None):
        if min(max_inflight,max_decoded_pixels,max_prediction_bytes)<=0:raise ValueError('positive resource bounds required')
        self.max_inflight=max_inflight;self.max_decoded_pixels=max_decoded_pixels;self.max_prediction_bytes=max_prediction_bytes;self.max_rss_bytes=max_rss_bytes;self.observations=[]
    def admit(self,pixels,prediction_bytes,count=1):
        if count>self.max_inflight or pixels>self.max_decoded_pixels or prediction_bytes>self.max_prediction_bytes:raise ValueError('RESOURCE_BUDGET_EXCEEDED')
        if self.max_rss_bytes:
            import psutil
            rss=psutil.Process().memory_info().rss;self.observations.append(rss)
            if rss>self.max_rss_bytes:raise ValueError('RSS_ADMISSION_LIMIT: stopped before next tile; not an OS hard limit')

def canonical_rows(task,tile,raw,source_width,source_height,spec,*,max_mask_runs):
    if not isinstance(raw,list) or len(raw)>spec.max_detections_per_tile:raise ValueError('native output must be bounded instance list')
    if len(json.dumps(raw,allow_nan=False).encode())>spec.max_prediction_bytes_per_tile:raise ValueError('native prediction byte limit')
    rows=[];sx=tile.source_width/tile.width;sy=tile.source_height/tile.height
    for i,obj in enumerate(raw):
        score=obj['score'];cat=obj['category_id']
        if isinstance(score,bool) or not isinstance(score,(float,int)) or not math.isfinite(score) or not 0<=score<=1 or type(cat) is not int or cat<0:raise ValueError('invalid native score/category')
        row={'task':task,'score':float(score),'category_id':cat,'tiles':[tile.id],'members':[tile.id+':'+str(i)]}
        if task=='hbb':
            b=obj['box']
            if len(b)!=4 or not all(math.isfinite(x) for x in b) or not(0<=b[0]<b[2]<=tile.width and 0<=b[1]<b[3]<=tile.height):raise ValueError('invalid native box')
            row['box']=[tile.x+b[0]*sx,tile.y+b[1]*sy,tile.x+b[2]*sx,tile.y+b[3]*sy]
        elif task=='obb':
            from cvsubstrate.geometry.polygons import canonical_polygon
            p=canonical_polygon(obj['polygon'])
            if len(p)!=4:raise ValueError('OBB requires four vertices')
            if any(not(0<=x<=tile.width and 0<=y<=tile.height) for x,y in p):raise ValueError('OBB vertices outside tile; clipping must be an explicit polygon policy')
            row['polygon']=[[tile.x+x*sx,tile.y+y*sy] for x,y in p]
        elif task=='masks':
            m=MaskRLE.model_validate(obj['mask'])
            if (m.width,m.height)!=(tile.width,tile.height):raise ValueError('mask not in native tile coordinates')
            row['mask']=place(m,width=source_width,height=source_height,x=tile.x,y=tile.y,scale_x=sx,scale_y=sy,max_runs=max_mask_runs).model_dump(mode='json')
        else:raise ValueError('unsupported stream task')
        rows.append(row)
    if len(json.dumps(rows,allow_nan=False).encode())>spec.max_prediction_bytes_per_tile:raise ValueError('TRANSFORMED_PREDICTION_BYTE_LIMIT')
    return rows

def execute_task_stream(spec:StreamSpec,predictor,out,*,task='hbb',resume=False,max_tiles=None,mask_policy='winner',max_mask_runs=1000000,max_rss_bytes=None,sensor=None):
    spec.validate()
    if max_tiles is not None and (type(max_tiles) is not int or max_tiles<=0):raise ValueError('max_tiles must be positive')
    if task not in {'hbb','obb','masks'}:raise ValueError('unsupported task')
    if file_digest(Path(spec.raster))!=spec.raster_sha256:raise ValueError('raster hash mismatch')
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    from cvsubstrate.provenance.artifact_set import assert_not_inside_sealed
    assert_not_inside_sealed(out)
    identity=digest({'algorithm_revision':'closure-stream-2','spec':asdict(spec),'task':task,'mask_policy':mask_policy,'max_mask_runs':max_mask_runs,'sensor':sensor})
    with process_lock(out/'.writer.lock'):
        if (out/'tiles.sqlite').exists() and not resume:raise ValueError('existing stream needs --resume')
        source=RasterSource(spec);store=SpatialPredictionIndex(out/'tiles.sqlite',identity)
        budget=ResourceBudget(max_inflight=spec.batch_size,max_decoded_pixels=spec.tile_width*spec.tile_height*spec.batch_size,max_prediction_bytes=spec.max_prediction_bytes_per_tile*spec.batch_size,max_rss_bytes=max_rss_bytes)
        processed=reused=0;complete=True
        try:
            # A source with huge unchunked blocks can defeat windowed decoding.
            block_bytes=max(h*w for h,w in source.ds.block_shapes)*source.ds.count*8
            if block_bytes>spec.working_memory_bytes:raise ValueError('RASTER_BLOCK_BUDGET: retile source; minimum decoded block exceeds configured memory')
            for tile in plan_tiles(source.width,source.height,spec):
                if store.done(tile.id):reused+=1;continue
                if max_tiles is not None and processed>=max_tiles:complete=False;break
                budget.admit(tile.width*tile.height,spec.max_prediction_bytes_per_tile)
                if sensor:
                    from rasterio.windows import Window
                    from rasterio.enums import Resampling
                    from cvsubstrate.datasets.sensors import SensorSpec,normalize_bands
                    import numpy as np
                    sensor_spec=SensorSpec.model_validate(sensor)
                    arr=source.ds.read([b.index for b in sensor_spec.bands],window=Window(tile.x,tile.y,tile.source_width,tile.source_height),out_shape=(len(sensor_spec.bands),tile.height,tile.width),out_dtype='float32',masked=True,resampling=Resampling.bilinear)
                    image,valid=normalize_bands(arr.filled(0),~np.ma.getmaskarray(arr).any(axis=0),sensor_spec)
                    # Multi-band models receive float32 C,H,W, not pretend RGB.
                else:image,valid=source.read(tile)
                output=predictor([image])
                if len(output)!=1:raise ValueError('predictor changed batch cardinality')
                rows=canonical_rows(task,tile,output[0],source.width,source.height,spec,max_mask_runs=max_mask_runs)
                store.insert_tile(tile,output[0],rows,float(valid.mean()));processed+=1
            result={'status':'COMPLETE' if complete else 'PAUSED','identity':identity,'task':task,'processed_tiles':processed,'reused_tiles':reused,'source_size':[source.width,source.height],'geospatial':{'crs':source.ds.crs.to_string() if source.ds.crs else None,'affine':list(source.ds.transform)[:6],'nodata':source.ds.nodata,'pixel_coordinates':'continuous_xy_edges'},'resource_scope':'CVRS buffers and per-tile admission; framework/driver allocations require external hard limits','mask_association':mask_policy if task=='masks' else None,'rss_observations':budget.observations}
            if complete:
                result['selected_instances']=store.merge(threshold=spec.nms_iou,mask_policy=mask_policy,max_mask_runs=max_mask_runs)
                output=out/('predictions-'+identity[:16]+'.jsonl')
                candidate=out/(output.name+'.candidate')
                candidate.unlink(missing_ok=True);store.export(candidate)
                if output.exists():
                    if file_digest(candidate)!=file_digest(output):candidate.unlink();raise ValueError('STREAM_OUTPUT_CHANGED: committed output differs from deterministic replay')
                    candidate.unlink()
                else:candidate.replace(output)
                result['predictions']=output.name;result['prediction_sha256']=file_digest(output)
                canonical=out/('canonical-'+identity[:16]+'.jsonl');candidate=out/(canonical.name+'.candidate')
                candidate.unlink(missing_ok=True)
                store.export_canonical(candidate,task=task,sample_id=spec.sample_id,width=source.width,height=source.height,source_digest=spec.raster_sha256,merge_policy={'iou':spec.nms_iou,'mask_policy':mask_policy})
                if canonical.exists():
                    if file_digest(canonical)!=file_digest(candidate):candidate.unlink();raise ValueError('CANONICAL_OUTPUT_CHANGED')
                    candidate.unlink()
                else:candidate.replace(canonical)
                result['canonical_predictions']=canonical.name;result['canonical_sha256']=file_digest(canonical)
                if source.ds.crs:
                    world=out/('world-'+identity[:16]+'.geojson');candidate=out/(world.name+'.candidate');candidate.unlink(missing_ok=True)
                    store.export_world(candidate,list(source.ds.transform),source.ds.crs.to_string())
                    if world.exists():
                        if file_digest(world)!=file_digest(candidate):candidate.unlink();raise ValueError('WORLD_OUTPUT_CHANGED')
                        candidate.unlink()
                    else:candidate.replace(world)
                    result['world_predictions']=world.name;result['world_sha256']=file_digest(world)
                result['source_tile_ledger']='tiles.sqlite'
            write_json(out/'state.json',result);return result
        finally:store.close();source.close()
