"""Binary mask geometry and explicitly named diagnostics.

RLE area/intersection do not decode a whole mask. Image transforms do decode and
therefore require an explicit pixel bound. No diagnostic is called COCO mask AP.
"""
from cvsubstrate.contracts.frontier import MaskRLE,MaskPrediction,MaskAnnotation

def encode_mask(mask):
    import numpy as np
    a=np.asarray(mask)
    if a.ndim!=2 or a.shape[0]==0 or a.shape[1]==0:raise ValueError('nonempty 2D binary mask required')
    if not np.isin(a,[0,1]).all():raise ValueError('mask must be binary, not probabilities/logits')
    flat=a.astype(bool).ravel(order='F');counts=[];last=False;count=0
    for bit in flat:
        if bool(bit)==last:count+=1
        else:counts.append(count);count=1;last=bool(bit)
    counts.append(count)
    return MaskRLE(height=a.shape[0],width=a.shape[1],counts=counts)

def decode_mask(mask,max_pixels=64*1024*1024):
    import numpy as np
    r=mask if isinstance(mask,MaskRLE) else MaskRLE.model_validate(mask)
    if r.height*r.width>max_pixels:raise ValueError('mask decode exceeds pixel budget')
    a=np.zeros(r.height*r.width,dtype=bool);offset=0
    for i,n in enumerate(r.counts):
        if i%2:a[offset:offset+n]=True
        offset+=n
    return a.reshape((r.height,r.width),order='F')

def mask_area(mask):return sum(mask.counts[1::2])

def mask_intersection(a,b):
    if (a.width,a.height)!=(b.width,b.height):raise ValueError('mask coordinate spaces differ')
    ia=ib=0;ra=a.counts[0];rb=b.counts[0];intersection=0
    while ia<len(a.counts) and ib<len(b.counts):
        n=min(ra,rb)
        if ia%2 and ib%2:intersection+=n
        ra-=n;rb-=n
        if ra==0:
            ia+=1
            if ia<len(a.counts):ra=a.counts[ia]
        if rb==0:
            ib+=1
            if ib<len(b.counts):rb=b.counts[ib]
    return intersection

def mask_iou(a,b):
    inter=mask_intersection(a,b);union=mask_area(a)+mask_area(b)-inter
    return inter/union if union else 1.0

def transform_mask(mask,*,crop=None,output_size=None,flip_horizontal=False,max_pixels=64*1024*1024):
    import numpy as np
    a=decode_mask(mask,max_pixels)
    if crop:
        x,y,w,h=crop
        if any(not isinstance(v,int) for v in crop) or min(x,y)<0 or min(w,h)<=0 or x+w>a.shape[1] or y+h>a.shape[0]:raise ValueError('invalid crop')
        a=a[y:y+h,x:x+w]
    if flip_horizontal:a=a[:,::-1]
    if output_size:
        h,w=output_size
        if min(h,w)<=0 or h*w>max_pixels:raise ValueError('resize exceeds pixel budget')
        # Pixel-center nearest neighbor; no bilinear interpolation of binary IDs.
        ys=np.minimum(((np.arange(h)+.5)*a.shape[0]/h).astype(int),a.shape[0]-1)
        xs=np.minimum(((np.arange(w)+.5)*a.shape[1]/w).astype(int),a.shape[1]-1)
        a=a[ys[:,None],xs[None,:]]
    return encode_mask(a)

def paste_mask(mask,*,width,height,x,y,max_pixels=64*1024*1024):
    import numpy as np
    if min(x,y)<0 or x+mask.width>width or y+mask.height>height:raise ValueError('mask tile outside source')
    if width*height>max_pixels:raise ValueError('paste exceeds pixel budget')
    a=np.zeros((height,width),dtype=bool);a[y:y+mask.height,x:x+mask.width]=decode_mask(mask,max_pixels)
    return encode_mask(a)

def merge_mask_tiles(tiles,*,width,height,max_pixels=64*1024*1024):
    """Union only for explicitly same tracked instance ID; do not merge all objects."""
    import numpy as np
    results={}
    for t in tiles:
        ident=t['instance_id'];m=MaskRLE.model_validate(t['mask'])
        placed=decode_mask(paste_mask(m,width=width,height=height,x=t['x'],y=t['y'],max_pixels=max_pixels),max_pixels)
        if ident in results:results[ident]|=placed
        else:results[ident]=placed
        if sum(x.nbytes for x in results.values())>max_pixels:raise ValueError('aggregate mask merge budget exceeded')
    return {k:encode_mask(v) for k,v in results.items()}

def evaluate_prompt_masks(predictions,annotations,pairs):
    """Pairs specify prompt -> target *before* evaluation. Never pick by GT IoU."""
    ps={p.sample_id:p for p in predictions}
    if len(ps)!=len(predictions):raise ValueError('duplicate sample prediction')
    gt={(g.sample_id,g.instance_id):g for g in annotations};rows=[]
    for pair in pairs:
        sid,pid,gid=pair['sample_id'],pair['prompt_id'],pair['instance_id']
        p=ps[sid];g=gt[(sid,gid)]
        if g.ignore or g.iscrowd:raise ValueError('prompt diagnostic does not implement crowd/ignore matching')
        candidates=[x for x in p.instances if x.prompt_id==pid]
        selected=max(candidates,key=lambda x:(x.score,x.id)) if candidates else None
        prompt=next(x for x in p.prompts if x.id==pid)
        rows.append({'sample_id':sid,'prompt_id':pid,'target_id':gid,'selected_id':selected.id if selected else None,
            'iou':mask_iou(selected.mask,g.mask) if selected else 0.0,'oracle_prompt':prompt.source=='ground_truth_oracle'})
    return {'evaluator':'prompt_mask_iou_diagnostic_v1','selection':'highest native mask-quality score, never ground-truth IoU',
        'mean_iou':sum(x['iou'] for x in rows)/len(rows) if rows else None,'support':len(rows),'pairs':rows,
        'oracle_conditioned':any(x['oracle_prompt'] for x in rows),'official_coco_ap':False}
