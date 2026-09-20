"""Sparse column-major binary masks. Translation, resampling and union avoid a scene bitmap.

A mask is represented by disjoint half-open foreground intervals in F-order.
Per-instance run budgets are explicit; highly fragmented masks can exceed them.
Dense/polygon interchange is a separately bounded optional operation.
"""
from __future__ import annotations
import math
from cvsubstrate.contracts.frontier import MaskRLE

def foreground(mask:MaskRLE):
    offset=0
    for i,n in enumerate(mask.counts):
        if i%2:yield (offset,offset+n)
        offset+=n

def coalesce(intervals,max_runs=1000000):
    result=[]
    for a,b in sorted(intervals):
        if not isinstance(a,int) or not isinstance(b,int) or a<0 or b<=a:raise ValueError('invalid foreground interval')
        if result and a<=result[-1][1]:result[-1]=(result[-1][0],max(b,result[-1][1]))
        else:result.append((a,b))
        if len(result)>max_runs:raise ValueError('MASK_RUN_BUDGET: fragmented mask exceeds run budget')
    return result

def from_intervals(intervals,*,width,height,max_runs=1000000):
    if width<=0 or height<=0:raise ValueError('positive mask dimensions required')
    merged=coalesce(intervals,max_runs);counts=[];offset=0
    for a,b in merged:
        if b>width*height:raise ValueError('interval outside image')
        counts.extend([a-offset,b-a]);offset=b
    if not merged:return MaskRLE(width=width,height=height,counts=[width*height])
    if offset<width*height:counts.append(width*height-offset)
    return MaskRLE(width=width,height=height,counts=counts)

def union(masks,max_runs=1000000):
    if not masks:raise ValueError('at least one mask required')
    w,h=masks[0].width,masks[0].height
    if any((m.width,m.height)!=(w,h) for m in masks):raise ValueError('different mask coordinate frames')
    return from_intervals((r for m in masks for r in foreground(m)),width=w,height=h,max_runs=max_runs)

def columns(mask):
    for a,b in foreground(mask):
        col=a//mask.height
        while a<b:
            end=min(b,(col+1)*mask.height)
            yield col,a-col*mask.height,end-col*mask.height
            col+=1;a=end

def bounds(mask):
    minx=mask.width;miny=mask.height;maxx=maxy=0
    for x,a,b in columns(mask):minx=min(minx,x);maxx=max(maxx,x+1);miny=min(miny,a);maxy=max(maxy,b)
    return [minx,miny,maxx,maxy] if maxx>minx else None

def place(mask,*,width,height,x,y,scale_x=1.0,scale_y=1.0,max_runs=1000000):
    if min(width,height)<=0 or not all(math.isfinite(v) for v in [x,y,scale_x,scale_y]) or min(scale_x,scale_y)<=0:raise ValueError('invalid mask transform')
    intervals=[]
    for col,lo,hi in columns(mask):
        x0=max(0,math.ceil(x+col*scale_x-.5));x1=min(width,math.ceil(x+(col+1)*scale_x-.5))
        y0=max(0,math.ceil(y+lo*scale_y-.5));y1=min(height,math.ceil(y+hi*scale_y-.5))
        if y1<=y0:continue
        if len(intervals)+max(0,x1-x0)>max_runs:raise ValueError('MASK_RUN_BUDGET: placement exceeds declared run budget')
        for xx in range(x0,x1):intervals.append((xx*height+y0,xx*height+y1))
    return from_intervals(intervals,width=width,height=height,max_runs=max_runs)

def crop(mask,*,x,y,width,height,max_runs=1000000):
    if min(x,y)<0 or min(width,height)<=0 or x+width>mask.width or y+height>mask.height:raise ValueError('crop outside mask')
    return place(mask,width=width,height=height,x=-x,y=-y,max_runs=max_runs)

def polygon_to_mask(polygons,*,width,height,max_pixels=16777216):
    if width*height>max_pixels:raise ValueError('polygon rasterization exceeds explicit bitmap bound')
    import numpy as np
    from rasterio.features import rasterize
    from cvsubstrate.vision.masks import encode_mask
    shapes=[]
    for rings in polygons:
        if not rings or len(rings[0])<3:raise ValueError('polygon must contain exterior ring and optional holes')
        shapes.append(({'type':'Polygon','coordinates':rings},1))
    a=rasterize(shapes,out_shape=(height,width),fill=0,dtype='uint8') if shapes else np.zeros((height,width),dtype='uint8')
    return encode_mask(a)

def mask_to_polygons(mask,*,max_pixels=16777216):
    from rasterio.features import shapes
    from cvsubstrate.vision.masks import decode_mask
    a=decode_mask(mask,max_pixels).astype('uint8')
    return [g['coordinates'] for g,v in shapes(a,mask=a.astype(bool),connectivity=4) if v==1]
