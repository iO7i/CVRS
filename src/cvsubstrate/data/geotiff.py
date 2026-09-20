"""Optional GeoTIFF inspection/window export with explicit band/radiometry policy.

Never imports rasterio from the core, never auto-selects bands, and never claims
that 8-bit display scaling preserves scientific sensor radiometry.
"""
from pathlib import Path
from cvsubstrate.contracts.research import GeoReference
from cvsubstrate.geometry.geospatial import tile_reference
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import file_digest,write_json


def inspect_geotiff(path: Path):
    try:import rasterio
    except ImportError as exc:raise CVRSError('GEO_DEPENDENCY','optional rasterio required') from exc
    with rasterio.open(path) as ds:
        if ds.crs is None:raise CVRSError('CRS_MISSING','GeoTIFF has no declared CRS')
        t=ds.transform
        ref=GeoReference(crs=ds.crs.to_string(),affine=[t.a,t.b,t.c,t.d,t.e,t.f])
        return {'schema_version':'1.0','source_sha256':file_digest(path),'width':ds.width,'height':ds.height,
            'bands':ds.count,'dtypes':list(ds.dtypes),'nodata':str(ds.nodata) if ds.nodata is not None else None,
            'band_indexes':list(ds.indexes),'color_interpretation':[str(value) for value in ds.colorinterp],
            'bounds':list(ds.bounds),'resolution':[abs(float(ds.res[0])),abs(float(ds.res[1]))],
            'block_shapes':[list(value) for value in ds.block_shapes],
            'reference':ref.model_dump(mode='json'),'rasterio_version':rasterio.__version__,
            'limits':'Affine metadata inspected; GSD/altitude not inferred and no sensor model certified.'}


def export_raw_window(path: Path, output: Path, *, window: list[int], bands: list[int]):
    """Export an unscaled raster window with explicit original-image lineage."""
    if len(window)!=4 or any(isinstance(x,bool) or not isinstance(x,int) for x in window) or min(window[:2])<0 or min(window[2:])<=0:
        raise ValueError('window requires integer col,row,width,height in bounds')
    if window[2]*window[3] > 16_000_000:
        raise CVRSError('WINDOW_PIXEL_LIMIT','export a smaller window (16 million pixels maximum)')
    if not bands or any(isinstance(b,bool) or not isinstance(b,int) or b<=0 for b in bands):
        raise ValueError('explicit positive 1-based band selections required')
    output=Path(output)
    if output.exists():raise CVRSError('OUTPUT_EXISTS','window output must be new')
    try:
        import rasterio
        import numpy as np
    except ImportError as exc:raise CVRSError('GEO_DEPENDENCY','rasterio and numpy required') from exc
    metadata=inspect_geotiff(path)
    with rasterio.open(path) as ds:
        x,y,w,h=window
        if x+w>ds.width or y+h>ds.height or max(bands)>ds.count:raise ValueError('window or band outside raster')
        raster_window=rasterio.windows.Window(x,y,w,h)
        arr=ds.read(bands,window=raster_window,masked=True)
        output.mkdir(parents=True)
        np.save(output/'data.npy',np.asarray(arr.data),allow_pickle=False)
        np.save(output/'valid_mask.npy',~np.ma.getmaskarray(arr),allow_pickle=False)
        ref=GeoReference.model_validate(metadata['reference'])
        result={**metadata,'window':window,'bands':bands,'shape':list(arr.shape),'dtype':str(arr.dtype),
            'conversion':'NONE; source samples and dtype preserved without scaling, reprojection, clipping, or band reordering',
            'output_reference':tile_reference(ref,x,y).model_dump(mode='json'),
            'window_bounds':list(rasterio.windows.bounds(raster_window,ds.transform)),
            'data_sha256':file_digest(output/'data.npy'),'valid_mask_sha256':file_digest(output/'valid_mask.npy'),
            'valid_values':int((~np.ma.getmaskarray(arr)).sum()),'total_values':int(arr.size)}
        write_json(output/'window.json',result)
        from cvsubstrate.provenance.artifact_set import seal_directory
        seal_directory(output)
        return result


def export_native_window_artifact(
    data,
    output: Path,
    *,
    source_sha256: str,
    source_reference: GeoReference,
    output_reference: GeoReference,
    window: list[int],
    bands: list[int],
    nodata: float | int | None,
):
    """Seal an already-produced native geospatial window without conversion."""
    if len(source_sha256)!=64 or any(c not in '0123456789abcdef' for c in source_sha256):
        raise ValueError('source_sha256 must be lowercase hexadecimal')
    if len(window)!=4 or any(isinstance(x,bool) or not isinstance(x,int) for x in window) or min(window[:2])<0 or min(window[2:])<=0:
        raise ValueError('window requires integer col,row,width,height in bounds')
    if not bands or any(isinstance(b,bool) or not isinstance(b,int) or b<=0 for b in bands):
        raise ValueError('explicit positive 1-based band selections required')
    output=Path(output)
    if output.exists():raise CVRSError('OUTPUT_EXISTS','window output must be new')
    try:import numpy as np
    except ImportError as exc:raise CVRSError('GEO_DEPENDENCY','numpy required') from exc
    array=np.asarray(data)
    if array.dtype.hasobject:raise ValueError('object arrays cannot be sealed as raster windows')
    if array.ndim!=3 or array.shape!=(len(bands),window[3],window[2]):
        raise ValueError('data must have shape bands,height,width matching the declared window')
    if array.size>64_000_000:raise CVRSError('WINDOW_VALUE_LIMIT','export a smaller native window')
    if nodata is None:
        valid=np.ones(array.shape,dtype=bool)
    elif isinstance(nodata,float) and np.isnan(nodata):
        valid=~np.isnan(array)
    else:
        valid=array!=nodata
    output.mkdir(parents=True)
    np.save(output/'data.npy',array,allow_pickle=False)
    np.save(output/'valid_mask.npy',valid,allow_pickle=False)
    result={'schema_version':'1.0','source_sha256':source_sha256,
        'source_reference':source_reference.model_dump(mode='json'),
        'output_reference':output_reference.model_dump(mode='json'),'window':window,'bands':bands,
        'shape':list(array.shape),'dtype':str(array.dtype),'nodata':nodata,
        'conversion':'NONE; native array values, shape, dtype, band order, nodata mask, and supplied georeference preserved',
        'data_sha256':file_digest(output/'data.npy'),'valid_mask_sha256':file_digest(output/'valid_mask.npy'),
        'valid_values':int(valid.sum()),'total_values':int(array.size)}
    write_json(output/'window.json',result)
    from cvsubstrate.provenance.artifact_set import seal_directory
    seal_directory(output)
    return result


def export_window(path: Path, output: Path, *, window: list[int], bands: list[int], value_range: list[float]):
    import math
    if len(window)!=4 or any(isinstance(x,bool) or not isinstance(x,int) for x in window) or min(window[:2])<0 or min(window[2:])<=0:
        raise ValueError('window requires integer col,row,width,height in bounds')
    if window[2]*window[3] > 16_000_000:
        raise CVRSError('WINDOW_PIXEL_LIMIT','export a smaller window (16 million pixels maximum)')
    if len(bands)!=3 or any(isinstance(b,bool) or not isinstance(b,int) or b<=0 for b in bands):
        raise ValueError('explicit three 1-based RGB band selections required (duplicates allowed intentionally)')
    if len(value_range)!=2 or not all(math.isfinite(x) for x in value_range) or value_range[1]<=value_range[0]:
        raise ValueError('explicit fixed radiometric min/max required; no automatic stretching')
    output=Path(output)
    if output.exists():raise CVRSError('OUTPUT_EXISTS','window output must be new')
    try:
        import rasterio
        import numpy as np
        from PIL import Image
    except ImportError as exc:raise CVRSError('GEO_DEPENDENCY','rasterio, numpy and Pillow required') from exc
    metadata=inspect_geotiff(path)
    with rasterio.open(path) as ds:
        x,y,w,h=window
        if x+w>ds.width or y+h>ds.height or max(bands)>ds.count:raise ValueError('window or band outside raster')
        arr=ds.read(bands,window=rasterio.windows.Window(x,y,w,h),masked=True)
        if not np.isfinite(arr.compressed()).all():raise ValueError('nonfinite valid raster values need explicit remediation')
        mask=np.ma.getmaskarray(arr).any(axis=0)
        values=arr.astype('float64').filled(value_range[0])
        values=np.rint(np.clip((values-value_range[0])/(value_range[1]-value_range[0]),0,1)*255).astype('uint8')
        values[:,mask]=0
        output.mkdir(parents=True)
        Image.fromarray(values.transpose(1,2,0)).save(output/'image.png')
        Image.fromarray((~mask).astype('uint8')*255).save(output/'valid_mask.png')
        ref=GeoReference.model_validate(metadata['reference'])
        result={**metadata,'window':window,'bands':bands,'value_range':value_range,
            'conversion':'fixed linear scaling to RGB uint8, clamped; masked pixels filled with zero',
            'valid_pixels':int((~mask).sum()),'output_reference':tile_reference(ref,x,y).model_dump(mode='json'),
            'image_sha256':file_digest(output/'image.png'),'valid_mask_sha256':file_digest(output/'valid_mask.png')}
        write_json(output/'window.json',result)
        from cvsubstrate.provenance.artifact_set import seal_directory
        seal_directory(output)
        return result
