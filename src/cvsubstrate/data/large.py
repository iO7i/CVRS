"""Serializable multi-scale tiling plans. Memory is a lower-bound hint, not a GPU guarantee."""
from __future__ import annotations
import math
from cvsubstrate.contracts.groundwork import LargeImagePlan
from cvsubstrate.data.tiled import axis_offsets
from cvsubstrate.provenance.io import digest

def plan_large_image(spec:LargeImagePlan|dict)->dict:
    s=spec if isinstance(spec,LargeImagePlan) else LargeImagePlan.model_validate(spec)
    tiles=[]
    for level,scale in enumerate(s.scales):
        sw=max(1,round(s.source_width*scale));sh=max(1,round(s.source_height*scale))
        for yi,y in enumerate(axis_offsets(sh,s.tile_height,s.overlap_y)):
            for xi,x in enumerate(axis_offsets(sw,s.tile_width,s.overlap_x)):
                width=min(s.tile_width,sw-x);height=min(s.tile_height,sh-y)
                ow=s.tile_width if s.pad_edges else width;oh=s.tile_height if s.pad_edges else height
                tiles.append({'id':f'{s.source_id}.s{level}.y{yi}.x{xi}','source_id':s.source_id,'level':level,
                    'requested_scale':scale,'scaled_size':[sw,sh],'actual_scale':[sw/s.source_width,sh/s.source_height],
                    'crop_scaled_xyxy':[x,y,x+width,y+height],'output_size':[ow,oh],
                    'valid_region_xyxy':[0,0,width,height],'padding':[0,0,ow-width,oh-height],
                    'inverse_affine':[s.source_width/sw,0,x*s.source_width/sw,0,s.source_height/sh,y*s.source_height/sh]})
                if len(tiles)>100000:raise ValueError('tile safety limit exceeded; split the source workload')
    max_input_bytes=max(t['output_size'][0]*t['output_size'][1]*s.channels*s.bytes_per_value for t in tiles)
    batch=s.batch_size
    if s.memory_budget_bytes is not None:
        batch=min(batch,s.memory_budget_bytes//max_input_bytes)
        if batch<1:raise ValueError('memory hint smaller than one input tensor, before model activations')
    plan={'schema_version':'1.0','policy':s.model_dump(mode='json'),'tiles':tiles,
        'batches':[[t['id'] for t in tiles[i:i+batch]] for i in range(0,len(tiles),batch)],
        'memory_hint':{'input_tensor_bytes_per_max_tile':max_input_bytes,'batch':batch,
            'excludes':['model','activations','decoder','runtime workspaces','image decode','CPU cache']}}
    return {**plan,'plan_digest':digest(plan)}

def map_box_to_source(box,tile):
    x1,y1,x2,y2=box;v=tile['valid_region_xyxy']
    x1=max(x1,v[0]);y1=max(y1,v[1]);x2=min(x2,v[2]);y2=min(y2,v[3])
    if x2<=x1 or y2<=y1:return None
    a,b,c,d,e,f=tile['inverse_affine']
    return [a*x1+b*y1+c,d*x1+e*y1+f,a*x2+b*y2+c,d*x2+e*y2+f]
