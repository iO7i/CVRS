"""Windowed raster -> bounded batches -> transactional predictions -> global merge.

No entire image/pyramid or all detections is loaded into Python memory. SQLite
spills detections and the NMS spatial index to disk. Working-image/queue bounds
exclude native model allocations; a process/container limit is still required
for an absolute whole-process RSS guarantee.
"""
from __future__ import annotations
import json, math, sqlite3, time, uuid
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Protocol
from cvsubstrate.provenance.io import digest, file_digest, write_json

@dataclass(frozen=True)
class StreamSpec:
    raster: str
    raster_sha256: str
    tile_width: int = 1024
    tile_height: int = 1024
    overlap: int = 128
    scales: tuple[float,...] = (1.0,)
    bands: tuple[int,...] = (1,2,3)
    batch_size: int = 1
    working_memory_bytes: int = 128*1024*1024
    gdal_cache_bytes: int = 16*1024*1024
    max_detections_per_tile: int = 10000
    max_prediction_bytes_per_tile: int = 8*1024*1024
    nms_iou: float = .5
    pixel_min: float = 0.0
    pixel_max: float = 255.0
    model_identity: str = ''
    sample_id: str = 'scene'
    def validate(self):
        from pydantic import TypeAdapter
        from cvsubstrate.contracts.models import ID
        TypeAdapter(ID).validate_python(self.sample_id)
        if len(self.raster_sha256)!=64 or any(x not in '0123456789abcdef' for x in self.raster_sha256):raise ValueError('raster SHA256 required')
        if any(not isinstance(x,int) or isinstance(x,bool) for x in [self.tile_width,self.tile_height,self.batch_size,self.overlap,*self.bands]):raise ValueError('integer raster dimensions/indices required')
        if not all(math.isfinite(x) for x in [self.pixel_min,self.pixel_max]):raise ValueError('finite radiometric bounds required')
        if min(self.tile_width,self.tile_height,self.batch_size,self.working_memory_bytes,self.gdal_cache_bytes,self.max_detections_per_tile,self.max_prediction_bytes_per_tile) <= 0:raise ValueError('positive size/budget required')
        if not 0 <= self.overlap < min(self.tile_width,self.tile_height):raise ValueError('overlap must be smaller than tiles')
        if not self.scales or any(not math.isfinite(s) or s<=0 for s in self.scales):raise ValueError('positive finite scales required')
        if len(set(self.scales))!=len(self.scales):raise ValueError('duplicate scale')
        if not self.bands or any(b<=0 for b in self.bands) or self.pixel_max<=self.pixel_min:raise ValueError('invalid bands/radiometry')
        if not 0<self.nms_iou<=1 or not self.model_identity:raise ValueError('model identity and valid IoU required')
        # Source float tile, validity masks, scaled uint8 tile, copies/tensor conversion.
        image_bound=self.tile_width*self.tile_height*len(self.bands)*16*self.batch_size
        result_bound=self.max_prediction_bytes_per_tile*self.batch_size
        if image_bound+result_bound+self.gdal_cache_bytes>self.working_memory_bytes:
            raise ValueError('MEMORY_BUDGET: reduce tiles/batch/cache; declared working buffers exceed budget')
        return {'image_working_bound':image_bound,'result_working_bound':result_bound,'gdal_cache_bytes':self.gdal_cache_bytes,
                'scope':'controlled tile buffers, prediction serialization and GDAL cache; excludes model/runtime allocations'}

@dataclass(frozen=True)
class Tile:
    id: str
    scale: float
    x: float
    y: float
    source_width: float
    source_height: float
    width: int
    height: int

class RasterSource:
    def __init__(self,spec:StreamSpec):
        import rasterio
        self.spec=spec
        self.env=rasterio.Env(GDAL_CACHEMAX=spec.gdal_cache_bytes);self.env.__enter__()
        try:self.ds=rasterio.open(spec.raster)
        except Exception:self.env.__exit__(None,None,None);raise
        if max(spec.bands)>self.ds.count:self.close();raise ValueError('raster lacks requested bands')
    @property
    def width(self):return self.ds.width
    @property
    def height(self):return self.ds.height
    def read(self,tile):
        import numpy as np
        from rasterio.windows import Window
        from rasterio.enums import Resampling
        a=self.ds.read(self.spec.bands,window=Window(tile.x,tile.y,tile.source_width,tile.source_height),
            out_shape=(len(self.spec.bands),tile.height,tile.width),resampling=Resampling.bilinear,out_dtype='float32',masked=True)
        valid=~np.ma.getmaskarray(a).any(axis=0)
        a=np.asarray(a.filled(self.spec.pixel_min),dtype=np.float32)
        a-=self.spec.pixel_min;a*=255.0/(self.spec.pixel_max-self.spec.pixel_min);np.clip(a,0,255,out=a)
        return a.astype(np.uint8).transpose(1,2,0),valid
    def close(self):self.ds.close();self.env.__exit__(None,None,None)

class Predictor(Protocol):
    def __call__(self,images:list)->list[dict]:...

def plan_tiles(width,height,spec):
    """Lazy multiscale windows: fractional source offsets preserve exact inversion."""
    if width<=0 or height<=0:raise ValueError('positive source dimensions required')
    for si,scale in enumerate(spec.scales):
        width_scaled=math.ceil(width*scale);height_scaled=math.ceil(height*scale)
        for y in range(0,height_scaled,spec.tile_height-spec.overlap):
            for x in range(0,width_scaled,spec.tile_width-spec.overlap):
                w=min(spec.tile_width,width_scaled-x);h=min(spec.tile_height,height_scaled-y)
                sw=min(w/scale,width-x/scale);sh=min(h/scale,height-y/scale)
                yield Tile(f'{si}:{x}:{y}',scale,x/scale,y/scale,sw,sh,w,h)

class PredictionDatabase:
    def __init__(self,path,identity,cache_kib=2048):
        self.db=sqlite3.connect(path);self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA temp_store=FILE');self.db.execute(f'PRAGMA cache_size=-{int(cache_kib)}')
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY,v TEXT);
          CREATE TABLE IF NOT EXISTS tiles(id TEXT PRIMARY KEY,spec TEXT,raw TEXT,seconds REAL);
          CREATE TABLE IF NOT EXISTS predictions(id INTEGER PRIMARY KEY,tile TEXT,ordinal INTEGER,x1 REAL,y1 REAL,x2 REAL,y2 REAL,score REAL,category INTEGER);
          CREATE INDEX IF NOT EXISTS prediction_score ON predictions(score DESC,tile,ordinal);
          CREATE TABLE IF NOT EXISTS selected(id INTEGER PRIMARY KEY,x1 REAL,y1 REAL,x2 REAL,y2 REAL,score REAL,category INTEGER);
          CREATE VIRTUAL TABLE IF NOT EXISTS spatial USING rtree(id,minx,maxx,miny,maxy);
        """)
        columns={row[1] for row in self.db.execute('PRAGMA table_info(predictions)')}
        if 'ordinal' not in columns:self.db.close();raise ValueError('STREAM_SCHEMA: legacy development database requires a new stream')
        old=self.db.execute("SELECT v FROM meta WHERE k='identity'").fetchone()
        if old and old[0]!=identity:self.db.close();raise ValueError('STREAM_IDENTITY: raster/model/plan changed; cannot resume')
        with self.db:self.db.execute("INSERT OR IGNORE INTO meta VALUES('identity',?)",(identity,))
    def done(self,tid):return self.db.execute('SELECT 1 FROM tiles WHERE id=?',(tid,)).fetchone() is not None
    def write(self,tile,raw,seconds,spec):
        boxes=raw.get('boxes');scores=raw.get('scores');cats=raw.get('category_ids')
        if not isinstance(boxes,list) or not isinstance(scores,list) or not isinstance(cats,list) or not len(boxes)==len(scores)==len(cats):raise ValueError('prediction arrays mismatch')
        if len(boxes)>spec.max_detections_per_tile:raise ValueError('prediction count exceeds configured bound')
        payload=json.dumps(raw,allow_nan=False,separators=(',',':'))
        if len(payload.encode())>spec.max_prediction_bytes_per_tile:raise ValueError('prediction byte bound exceeded')
        with self.db:
            # The entire tile commits atomically, including raw native output.
            self.db.execute('INSERT INTO tiles VALUES(?,?,?,?)',(tile.id,json.dumps(asdict(tile)),payload,seconds))
            for ordinal,(box,score,cat) in enumerate(zip(boxes,scores,cats)):
                if len(box)!=4 or not all(isinstance(x,(float,int)) and math.isfinite(x) for x in [*box,score]):raise ValueError('non-finite/invalid prediction')
                x1,y1,x2,y2=box
                if x1<0 or y1<0 or x2<=x1 or y2<=y1 or x2>tile.width or y2>tile.height or not 0<=score<=1:raise ValueError('prediction outside tile')
                if not isinstance(cat,int) or isinstance(cat,bool) or cat<0:raise ValueError('category must be nonnegative integer')
                sx=tile.source_width/tile.width;sy=tile.source_height/tile.height
                self.db.execute('INSERT INTO predictions(tile,ordinal,x1,y1,x2,y2,score,category) VALUES(?,?,?,?,?,?,?,?)',
                    (tile.id,ordinal,tile.x+x1*sx,tile.y+y1*sy,tile.x+x2*sx,tile.y+y2*sy,score,cat))
    def merge(self,threshold):
        """Exact global greedy HBB NMS, disk-backed score order and spatial index.
        Never finalize tiles early: a later tile may contain a higher score.
        """
        with self.db:
            self.db.execute('DELETE FROM selected');self.db.execute('DELETE FROM spatial')
        cursor=self.db.execute('SELECT id,x1,y1,x2,y2,score,category FROM predictions ORDER BY score DESC,tile,ordinal')
        with self.db:
            for row in cursor:
                ident,x1,y1,x2,y2,score,cat=row;keep=True
                candidates=self.db.execute('SELECT s.x1,s.y1,s.x2,s.y2 FROM spatial r JOIN selected s ON s.id=r.id WHERE r.maxx>=? AND r.minx<=? AND r.maxy>=? AND r.miny<=? AND s.category=?',(x1,x2,y1,y2,cat))
                for a,b,c,d in candidates:
                    inter=max(0,min(c,x2)-max(a,x1))*max(0,min(d,y2)-max(b,y1))
                    union=(x2-x1)*(y2-y1)+(c-a)*(d-b)-inter
                    if union>0 and inter/union>threshold:keep=False;break
                if keep:
                    self.db.execute('INSERT INTO selected VALUES(?,?,?,?,?,?,?)',row)
                    self.db.execute('INSERT INTO spatial VALUES(?,?,?,?,?)',(ident,x1,x2,y1,y2))
        return self.db.execute('SELECT COUNT(*) FROM selected').fetchone()[0]
    def export(self,path):
        with Path(path).open('w',encoding='utf-8') as f:
            for tid,ordinal,x1,y1,x2,y2,score,cat in self.db.execute('SELECT p.tile,p.ordinal,s.x1,s.y1,s.x2,s.y2,s.score,s.category FROM selected s JOIN predictions p ON p.id=s.id ORDER BY s.score DESC,p.tile,p.ordinal'):
                f.write(json.dumps({'id':tid+':prediction:'+str(ordinal),'box':[x1,y1,x2,y2],'score':score,'category_id':cat},allow_nan=False)+'\n')
    def export_canonical(self,path,sample_id,width,height,provenance):
        # Three streaming SQL passes avoid assembling a gigapixel scene's entire
        # detection list in Python. Standard COCO evaluation can still need RAM.
        order=' FROM selected s JOIN predictions p ON p.id=s.id ORDER BY s.score DESC,p.tile,p.ordinal'
        with Path(path).open('w',encoding='utf-8') as f:
            head={'schema_version':'1.0','sample_id':sample_id,'width':width,'height':height,'coordinate_frame':'original_image_xyxy',
                'score_semantics':'native confidence, not calibrated probability','transform_provenance':provenance}
            prefix=json.dumps(head,allow_nan=False)[:-1];f.write(prefix)
            for key,columns,convert in [('boxes','s.x1,s.y1,s.x2,s.y2',lambda row:list(row)),('scores','s.score',lambda row:row[0]),('category_ids','s.category',lambda row:row[0])]:
                f.write(','+json.dumps(key)+':[');first=True
                for row in self.db.execute('SELECT '+columns+order):
                    if not first:f.write(',')
                    f.write(json.dumps(convert(row),allow_nan=False));first=False
                f.write(']')
            f.write('}\n')
    def close(self):self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');self.db.close()

def execute_stream(spec:StreamSpec,predictor:Predictor,output,*,resume=False,max_tiles=None):
    from cvsubstrate.provenance.artifact_set import assert_not_inside_sealed
    if max_tiles is not None and (not isinstance(max_tiles,int) or max_tiles<=0):raise ValueError('stop-after-tiles must be positive')
    budget=spec.validate();out=Path(output);assert_not_inside_sealed(out)
    if out.exists() and any(out.iterdir()) and not resume:raise ValueError('new stream destination or explicit resume required')
    out.mkdir(parents=True,exist_ok=True)
    if (out/'stream.sqlite').exists() and not resume:raise ValueError('stream exists; explicit resume required')
    if file_digest(Path(spec.raster))!=spec.raster_sha256:raise ValueError('raster content identity mismatch')
    canonical=asdict(spec);canonical.pop('raster');identity=digest(canonical)
    store=PredictionDatabase(out/'stream.sqlite',identity)
    try:source=RasterSource(spec)
    except Exception:store.close();raise
    processed=0;resumed=0;peak_batch=0;status='RUNNING';attempt=uuid.uuid4().hex
    write_json(out/'attempts'/(attempt+'.json'),{'status':'RUNNING','resumed':resume,'identity':identity,'started_at':time.time()})
    write_json(out/'stream-spec.json',asdict(spec))
    try:
        batch=[];images=[];masks=[]
        def flush():
            nonlocal processed,peak_batch
            if not batch:return
            peak_batch=max(peak_batch,sum(a.nbytes+m.nbytes for a,m in zip(images,masks)))
            start=time.perf_counter();results=predictor(images)
            if len(results)!=len(batch):raise ValueError('predictor did not return one result per tile')
            for t,result,valid in zip(batch,results,masks):
                # Mark nodata overlap in evidence. No arbitrary centroid filtering.
                result={**result,'valid_pixel_fraction':float(valid.mean()),'nodata_policy':'preserve predictions; explicit downstream policy required'}
                store.write(t,result,(time.perf_counter()-start)/len(batch),spec);processed+=1
            batch.clear();images.clear();masks.clear()
        for tile in plan_tiles(source.width,source.height,spec):
            if store.done(tile.id):resumed+=1;continue
            if max_tiles is not None and processed+len(batch)>=max_tiles:break
            image,valid=source.read(tile);batch.append(tile);images.append(image);masks.append(valid)
            if len(batch)==spec.batch_size:flush()
        flush()
        pending=any(not store.done(t.id) for t in plan_tiles(source.width,source.height,spec))
        count=None
        if not pending:
            count=store.merge(spec.nms_iou);store.export(out/'scene-predictions.jsonl')
            store.export_canonical(out/'canonical-predictions.jsonl',spec.sample_id,source.width,source.height,{'stream_identity':identity,'merge':'global_disk_nms','iou':spec.nms_iou})
        status='PARTIAL' if pending else 'SUCCEEDED'
        result={'status':status,'identity':identity,'processed_this_session':processed,'reused_tiles':resumed,
            'committed_tiles':store.db.execute('SELECT count(*) FROM tiles').fetchone()[0],
            'raw_detections':store.db.execute('SELECT count(*) FROM predictions').fetchone()[0],
            'merged_detections':count,'width':source.width,'height':source.height,'peak_batch_array_bytes':peak_batch,
            'memory_contract':budget,'merge_policy':{'name':'disk_global_greedy_nms','iou':spec.nms_iou,'class_aware':True},
            'model_identity':spec.model_identity,'geospatial':{'crs':str(source.ds.crs) if source.ds.crs else None,'affine':list(source.ds.transform)[:6]}}
        write_json(out/'stream-result.json',result);write_json(out/'attempts'/(attempt+'.json'),{**result,'attempt_id':attempt,'finished_at':time.time()});return result
    except Exception as exc:
        failure={'status':'FAILED','message':str(exc),'processed_tiles':processed,'resumable':True,'attempt_id':attempt,'finished_at':time.time()}
        write_json(out/'failure.json',failure);write_json(out/'attempts'/(attempt+'.json'),failure);raise
    finally:source.close();store.close()
