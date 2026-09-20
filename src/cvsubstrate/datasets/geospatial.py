"""Optional raster readers and explicit pixel/world exports.

GeoJSON RFC7946 output is longitude/latitude WGS84; another CRS is reprojected,
not mislabeled as GeoJSON. Generic world JSON/CSV keeps its declared CRS.
"""
from pathlib import Path
import csv
from cvsubstrate.contracts.groundwork import GeoDatasetManifest
from cvsubstrate.contracts.research import GeoReference
from cvsubstrate.geometry.geospatial import pixel_to_world,world_to_pixel
from cvsubstrate.provenance.io import read_json,write_json,file_digest
from cvsubstrate.errors import CVRSError

def inspect_raster(path:Path,*,sidecar:Path|None=None):
    path=Path(path)
    if sidecar:
        from cvsubstrate.data.manifest import image_dimensions
        width,height=image_dimensions(path);geo=GeoReference.model_validate(read_json(sidecar))
        return {'path':str(path.resolve()),'sha256':file_digest(path),'width':width,'height':height,'georeference':geo.model_dump(mode='json'),'metadata_source':'explicit_sidecar','sidecar_sha256':file_digest(sidecar),'layout':'ordinary_raster'}
    try:import rasterio
    except ImportError as e:raise CVRSError('DEPENDENCY_UNAVAILABLE','rasterio required for GeoTIFF/COG') from e
    with rasterio.open(path) as src:
        if src.crs is None:raise CVRSError('CRS_UNKNOWN','raster lacks CRS; supply an explicit sidecar')
        t=src.transform;geo=GeoReference(crs=src.crs.to_string(),affine=[t.a,t.b,t.c,t.d,t.e,t.f])
        return {'path':str(path.resolve()),'sha256':file_digest(path),'width':src.width,'height':src.height,
            'bands':src.count,'dtypes':list(src.dtypes),'nodata':None if src.nodata is None else str(src.nodata),
            'bounds':list(src.bounds),'georeference':geo.model_dump(mode='json'),'block_shapes':[list(x) for x in src.block_shapes],
            'overviews':{str(i):src.overviews(i) for i in src.indexes},'layout':src.tags(ns='IMAGE_STRUCTURE').get('LAYOUT','unknown'),
            'is_tiled':src.is_tiled,'note':'COG layout tag is metadata, not a complete COG compliance validation; local files only'}

def build_geo_manifest(name,version,assets,license='unknown'):
    return GeoDatasetManifest(name=name,version=version,raster_assets=[inspect_raster(Path(a['path']),sidecar=Path(a['sidecar']) if a.get('sidecar') else None) for a in assets],license=license)

def export_world_predictions(predictions,georeferences,output:Path,*,format='geojson'):
    if format not in {'geojson','json','csv'}:raise ValueError('unsupported export format')
    features=[]
    for row in predictions:
        sid=row['sample_id']
        if sid not in georeferences:raise CVRSError('CRS_UNKNOWN',sid)
        geo=GeoReference.model_validate(georeferences[sid]);crs=geo.crs
        polygons=row.get('polygons')
        if polygons is None:polygons=[[[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]]] for b in row['boxes']]
        if not(len(polygons)==len(row['scores'])==len(row['category_ids'])):raise ValueError('prediction lengths differ')
        for i,(poly,score,cat) in enumerate(zip(polygons,row['scores'],row['category_ids'])):
            points=[list(pixel_to_world(geo,x,y)) for x,y in poly]
            if format=='geojson':
                try:from pyproj import Transformer
                except ImportError as e:raise CVRSError('DEPENDENCY_UNAVAILABLE','pyproj required for RFC7946 export') from e
                transformer=Transformer.from_crs(crs,'EPSG:4326',always_xy=True);points=[list(transformer.transform(x,y,errcheck=True)) for x,y in points]
                if any(not(-180<=x<=180 and -90<=y<=90) for x,y in points):raise ValueError('invalid longitude/latitude after reprojection')
            ring=points+[points[0]];features.append({'type':'Feature','id':f'{sid}:{i}',
                'geometry':{'type':'Polygon','coordinates':[ring]},'properties':{'sample_id':sid,'score':score,'category_id':cat,
                    'source_crs':crs,'coordinate_crs':'EPSG:4326' if format=='geojson' else crs,'source_pixel_polygon':poly}})
    output=Path(output)
    if output.exists():raise CVRSError('OUTPUT_EXISTS','export destination already exists')
    output.parent.mkdir(parents=True,exist_ok=True)
    if format=='csv':
        import json
        with output.open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=['id','sample_id','category_id','score','crs','polygon']);writer.writeheader()
            for row in features:writer.writerow({'id':row['id'],**{k:row['properties'][k] for k in ['sample_id','category_id','score']},'crs':row['properties']['coordinate_crs'],'polygon':json.dumps(row['geometry']['coordinates'][0])})
    else:write_json(output,{'type':'FeatureCollection','features':features} if format=='geojson' else {'format':'cvrs-world-predictions-1','features':features})
    return {'path':str(output),'sha256':file_digest(output),'features':len(features),'format':format}
