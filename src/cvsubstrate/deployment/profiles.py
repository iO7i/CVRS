"""Explicit detector-family preprocessing/decoding contracts, never shape guessing."""
from __future__ import annotations
from dataclasses import dataclass,asdict
import math
from cvsubstrate.provenance.io import digest

@dataclass(frozen=True)
class DetectorProfile:
    family: str  # ultralytics_raw, rfdetr, mmdet_end2end
    class_count: int
    category_map: dict[str,int]
    input_height: int
    input_width: int
    resize: str = 'letterbox'
    resize_library: str = 'pillow'
    channel_order: str = 'RGB'
    scale: float = 1/255
    mean: tuple[float,...] = (0.,0.,0.)
    std: tuple[float,...] = (1.,1.,1.)
    pad_value: int = 114
    pad_anchor: str = 'center'
    pad_after_normalization: bool = False
    normalized_pad_value: float = 0.0
    input_dtype: str = 'float32'
    threshold: float = .001
    nms_iou: float = .7
    max_detections: int = 300
    drop_last_logit: bool = True
    output_names: tuple[str,...] = ()
    def validate(self):
        if self.family not in {'ultralytics_raw','ultralytics_end2end','rfdetr','mmdet_end2end'}:raise ValueError('unknown explicit detector profile')
        if min(self.class_count,self.input_height,self.input_width,self.max_detections)<=0:raise ValueError('positive dimensions/classes required')
        if self.resize not in {'stretch','letterbox'} or self.resize_library not in {'pillow','opencv'}:raise ValueError('unsupported resize contract')
        if self.pad_anchor not in {'center','top_left'} or self.input_dtype not in {'float32','float16'}:raise ValueError('unsupported explicit padding/dtype contract')
        if not 0<=self.pad_value<=255 or not math.isfinite(self.normalized_pad_value):raise ValueError('invalid padding value')
        if self.channel_order not in {'RGB','BGR'}:raise ValueError('channel order must be RGB or BGR')
        if len(self.mean)!=3 or len(self.std)!=3 or any(v<=0 or not math.isfinite(v) for v in self.std):raise ValueError('invalid normalization')
        if not all(math.isfinite(x) for x in [self.scale,*self.mean,self.threshold,self.nms_iou]):raise ValueError('nonfinite profile')
        if not 0<=self.threshold<=1 or not 0<self.nms_iou<=1:raise ValueError('threshold outside range')
        if set(self.category_map)!={str(i) for i in range(self.class_count)}:raise ValueError('complete native class mapping required')
        if len(set(self.category_map.values()))!=self.class_count or any(v<0 for v in self.category_map.values()):raise ValueError('noninjective/invalid mapping')
        return self

def preprocess_image(rgb,profile):
    import numpy as np
    profile.validate();a=np.asarray(rgb)
    if a.ndim!=3 or a.shape[2]!=3 or a.dtype!=np.uint8:raise ValueError('explicit uint8 RGB HWC image required')
    oh,ow=a.shape[:2];nh,nw=profile.input_height,profile.input_width
    if profile.resize=='letterbox':
        gain=min(nh/oh,nw/ow);rh=max(1,round(oh*gain));rw=max(1,round(ow*gain))
    else:rh,rw=nh,nw
    if profile.resize_library=='opencv':
        import cv2
        resized=cv2.resize(a,(rw,rh),interpolation=cv2.INTER_LINEAR)
    else:
        from PIL import Image
        resized=np.asarray(Image.fromarray(a).resize((rw,rh),Image.Resampling.BILINEAR))
    top=(nh-rh)//2 if profile.pad_anchor=='center' else 0;left=(nw-rw)//2 if profile.pad_anchor=='center' else 0
    image=np.full((nh,nw,3),profile.pad_value,dtype=np.uint8);image[top:top+rh,left:left+rw]=resized
    if profile.channel_order=='BGR':image=image[:,:,::-1]
    tensor=image.astype(np.float32)*profile.scale
    tensor=(tensor-np.asarray(profile.mean,dtype=np.float32))/np.asarray(profile.std,dtype=np.float32)
    if profile.pad_after_normalization:
        tensor[:top,:,:]=profile.normalized_pad_value;tensor[top+rh:,:,:]=profile.normalized_pad_value
        tensor[:,:left,:]=profile.normalized_pad_value;tensor[:,left+rw:,:]=profile.normalized_pad_value
    tensor=tensor.astype(profile.input_dtype)
    return tensor.transpose(2,0,1)[None].copy(),{'width':ow,'height':oh,'scale_x':rw/ow,'scale_y':rh/oh,'left':left,'top':top,
        'resized_width':rw,'resized_height':rh,'profile_sha256':digest(asdict(profile))}

def _iou(a,b):
    i=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    u=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-i
    return i/u if u>0 else 0.

def decode_outputs(outputs,profile,transforms):
    import numpy as np
    profile.validate();names=profile.output_names
    if not names:names=('output0',) if profile.family in {'ultralytics_raw','ultralytics_end2end'} else ('pred_logits','pred_boxes') if profile.family=='rfdetr' else ('dets','labels')
    if set(names)!=set(outputs):raise ValueError('output names differ; specify explicit output contract')
    values=[np.asarray(outputs[n]) for n in names]
    if any(not np.isfinite(a).all() for a in values):raise ValueError('nonfinite model output')
    if any(a.ndim<2 or len(a)!=len(transforms) for a in values):raise ValueError('output batch dimensions differ from preprocessing transforms')
    results=[]
    for bi,t in enumerate(transforms):
        padded=0
        if profile.family=='ultralytics_raw':
            raw=values[0][bi]
            if raw.ndim!=2 or raw.shape[0]!=profile.class_count+4:raise ValueError('profile expects B x (4+C) x N, no objectness; not YOLO end-to-end format')
            raw=raw.T;box=raw[:,:4];probs=raw[:,4:];labels=probs.argmax(axis=1);scores=probs[np.arange(len(raw)),labels]
            x,y,w,h=box.T;boxes=np.stack([x-w/2,y-h/2,x+w/2,y+h/2],axis=1)
        elif profile.family=='ultralytics_end2end':
            dets=values[0][bi]
            if dets.ndim!=2 or dets.shape[1]!=6:raise ValueError('UL end-to-end contract expects B,N,6 xyxy/score/class')
            boxes=dets[:,:4];scores=dets[:,4];labels=dets[:,5]
        elif profile.family=='rfdetr':
            logits=values[0][bi];box=values[1][bi]
            if profile.drop_last_logit:logits=logits[:,:-1]
            if logits.ndim!=2 or logits.shape[1]!=profile.class_count or box.shape!=(len(logits),4):raise ValueError('RF query/class/box contract mismatch')
            probs=1/(1+np.exp(-np.clip(logits,-80,80)))
            # All query/class pairs; per-query argmax would discard valid results.
            flat=probs.reshape(-1);order=np.lexsort((np.arange(len(flat)),-flat))[:profile.max_detections]
            queries=order//profile.class_count;labels=order%profile.class_count;scores=flat[order]
            x,y,w,h=box[queries].T
            boxes=np.stack([x-w/2,y-h/2,x+w/2,y+h/2],axis=1)*np.asarray([profile.input_width,profile.input_height]*2)
        else:
            dets=values[0][bi];labels=values[1][bi]
            if dets.ndim!=2 or dets.shape[1]!=5 or labels.shape!=(len(dets),):raise ValueError('MMDeploy contract expects B,N,5 dets plus B,N labels')
            boxes=dets[:,:4];scores=dets[:,4]
        candidates=[];clipped=degenerate=0
        for index,(b,score,cat) in enumerate(zip(boxes,scores,labels)):
            if score<profile.threshold:continue
            if profile.family in {'mmdet_end2end','ultralytics_end2end'} and score==0 and (b[2]<=b[0] or b[3]<=b[1] or cat<0):padded+=1;continue
            if float(cat)!=int(cat) or not 0<=int(cat)<profile.class_count or not 0<=score<=1:raise ValueError('bad score/label')
            original=[(float(b[0])-t['left'])/t['scale_x'],(float(b[1])-t['top'])/t['scale_y'],
                (float(b[2])-t['left'])/t['scale_x'],(float(b[3])-t['top'])/t['scale_y']]
            box=[min(max(original[j],0),t['width'] if j%2==0 else t['height']) for j in range(4)]
            clipped+=int(box!=original)
            if box[2]<=box[0] or box[3]<=box[1]:degenerate+=1;continue
            candidates.append((float(score),index,box,int(cat)))
        candidates.sort(key=lambda x:(-x[0],x[1]));selected=[]
        for c in candidates:
            # RF and MM end-to-end profiles own selection upstream; no second NMS.
            if profile.family=='ultralytics_raw' and any(s[3]==c[3] and _iou(s[2],c[2])>profile.nms_iou for s in selected):continue
            selected.append(c)
            if len(selected)>=profile.max_detections:break
        results.append({'boxes':[x[2] for x in selected],'scores':[x[0] for x in selected],
            'category_ids':[profile.category_map[str(x[3])] for x in selected],
            'audit':{'clipped_to_original_image':clipped,'degenerate_after_clip':degenerate,'padding_removed':padded,
            'postprocess_nms':profile.family=='ultralytics_raw','profile_sha256':digest(asdict(profile))}})
    return results
