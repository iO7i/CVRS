"""Affine geospatial transforms. Reprojection is an explicit optional operation."""
from __future__ import annotations
from cvsubstrate.contracts.research import GeoReference
from cvsubstrate.geometry.polygons import transform_polygon


def pixel_to_world(reference: GeoReference, x: float, y: float, *, center=False):
    import math
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError('finite pixel coordinates required')
    if center:
        x,y = x+0.5,y+0.5
    a,b,c,d,e,f = reference.affine
    return [a*x+b*y+c, d*x+e*y+f]


def world_to_pixel(reference: GeoReference, x: float, y: float, *, center=False):
    import math
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError('finite world coordinates required')
    a,b,c,d,e,f = reference.affine
    det=a*e-b*d
    xx,yy=(e*(x-c)-b*(y-f))/det,(-d*(x-c)+a*(y-f))/det
    return [xx-0.5, yy-0.5] if center else [xx,yy]


def tile_reference(reference: GeoReference, x, y, scale_x=1.0, scale_y=1.0, pad_left=0.0, pad_top=0.0):
    import math
    if not all(math.isfinite(v) for v in (x,y,scale_x,scale_y,pad_left,pad_top)) or min(scale_x,scale_y)<=0:
        raise ValueError('invalid crop/resize transform')
    a,b,c,d,e,f=reference.affine
    xx,yy=x-pad_left/scale_x,y-pad_top/scale_y
    return GeoReference(crs=reference.crs, affine=[a/scale_x,b/scale_y,c+a*xx+b*yy,
        d/scale_x,e/scale_y,f+d*xx+e*yy])


def world_polygon(reference: GeoReference, pixel_polygon):
    return {'crs': reference.crs, 'axis_order': 'x_y',
            'polygon': transform_polygon(pixel_polygon, reference.affine),
            'format': 'CRS-tagged geometry, NOT automatically RFC7946 GeoJSON'}


def reproject_points(points, source_crs: str, target_crs: str):
    try:
        from pyproj import Transformer
    except ImportError as exc:
        raise RuntimeError('optional pyproj is required; no CRS guessing or reprojection fallback') from exc
    tr=Transformer.from_crs(source_crs,target_crs,always_xy=True)
    out=[]
    for x,y in points:
        xx,yy=tr.transform(x,y,errcheck=True)
        out.append([float(xx),float(yy)])
    return out
