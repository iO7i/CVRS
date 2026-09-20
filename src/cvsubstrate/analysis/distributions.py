"""Descriptive real/synthetic dataset and optional image/embedding distributions."""
from collections import Counter,defaultdict
from pathlib import Path
import math,statistics
from cvsubstrate.provenance.io import digest,safe_join,file_digest
from cvsubstrate.errors import CVRSError

def summary(values):
    v=sorted(float(x) for x in values if x is not None)
    if any(not math.isfinite(x) for x in v):raise ValueError('nonfinite observation')
    if not v:return {'n':0,'mean':None,'std':None,'min':None,'median':None,'max':None}
    def q(p):
        k=(len(v)-1)*p;i=int(k);return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(k-i)
    return {'n':len(v),'mean':statistics.mean(v),'std':statistics.stdev(v) if len(v)>1 else 0.0,
        'min':v[0],'q10':q(.1),'median':q(.5),'q90':q(.9),'max':v[-1]}

def distribution_report(m,split,*,root=None,metadata=None,image_stats=False,max_image_pixels=4000000):
    ids=set(m.splits[split].sample_ids)
    if m.splits[split].role=='locked_test':raise CVRSError('PROTECTED_SPLIT','development distribution analysis cannot inspect locked test')
    numeric=defaultdict(list);counts=defaultdict(Counter);unknown=Counter();metadata=metadata or {};image_methods={}
    for s in m.samples:
        if s.id not in ids:continue
        numeric['image_width_px'].append(s.width);numeric['image_height_px'].append(s.height);numeric['objects_per_image'].append(len(s.boxes));counts['domain'][s.domain]+=1;counts['source_kind'][s.source_kind]+=1
        for b in s.boxes:
            x1,y1,x2,y2=b.xyxy;w=x2-x1;h=y2-y1
            for k,v in {'object_width_px':w,'object_height_px':h,'object_area_px2':w*h,'object_aspect_ratio':w/h,
                'normalized_center_x':(x1+x2)/(2*s.width),'normalized_center_y':(y1+y2)/(2*s.height),
                'border_distance_px':min(x1,y1,s.width-x2,s.height-y2)}.items():numeric[k].append(v)
            counts['category'][str(b.category_id)]+=1
        def walk(value,prefix):
            if isinstance(value,dict) and 'status' in value and 'value' in value:
                status=value['status'];counts[prefix+'.status'][status]+=1;v=value['value']
                if status=='unknown' or v is None:unknown[prefix]+=1
                elif isinstance(v,(int,float)) and not isinstance(v,bool):numeric[prefix+' ['+str(value.get('unit','unknown'))+']'].append(v)
                elif isinstance(v,str):counts[prefix][v]+=1
            elif isinstance(value,dict):
                for k,v in value.items():walk(v,prefix+'.'+k if prefix else k)
        walk(metadata.get(s.id,{}),'metadata')
        if image_stats:
            if root is None:raise ValueError('image stats require an explicit dataset root')
            try:from PIL import Image,ImageStat
            except ImportError as e:raise CVRSError('DEPENDENCY_UNAVAILABLE','Pillow needed for image statistics') from e
            path=safe_join(Path(root),s.image)
            if file_digest(path)!=s.sha256:raise CVRSError('DATA_INTEGRITY','image changed')
            with Image.open(path) as im:
                im=im.convert('RGB');scale=min(1.0,(max_image_pixels/(im.width*im.height))**.5)
                if scale<1:im=im.resize((max(1,int(im.width*scale)),max(1,int(im.height*scale))))
                stat=ImageStat.Stat(im);gray=ImageStat.Stat(im.convert('L'))
                for i,c in enumerate('RGB'):numeric['mean_'+c].append(stat.mean[i]);numeric['std_'+c].append(stat.stddev[i])
                numeric['mean_luminance_8bit'].append(gray.mean[0]);numeric['luminance_std_8bit'].append(gray.stddev[0]);image_methods[s.id]={'rescale':scale,'color':'Pillow RGB/L uint8','no_sensor_radiometry_claim':True}
    return {'kind':'DESCRIPTIVE_DISTRIBUTIONS','dataset_digest':digest(m),'split':split,'taxonomy_digest':digest(m.categories),
        'images':len(ids),'numeric':{k:summary(v) for k,v in sorted(numeric.items())},'categorical':{k:dict(v) for k,v in counts.items()},
        'unknown_observations':dict(unknown),'image_methods':image_methods,
        'limits':'Marginals and pixel statistics are not a scalar domain gap, realism rating, causal effect, or evidence of transfer.'}

def compare_distributions(left,right):
    if left['kind']!='DESCRIPTIVE_DISTRIBUTIONS' or right['kind']!='DESCRIPTIVE_DISTRIBUTIONS':raise ValueError('requires distribution reports')
    comparisons={}
    for k in sorted(set(left['numeric'])|set(right['numeric'])):
        a=left['numeric'].get(k);b=right['numeric'].get(k)
        comparisons[k]={'left':a,'right':b,'right_minus_left_mean':b['mean']-a['mean'] if a and b and a['mean'] is not None and b['mean'] is not None else None}
    return {'kind':'DESCRIPTIVE_DISTRIBUTION_COMPARISON','left':left['dataset_digest'],'right':right['dataset_digest'],
        'numeric':comparisons,'category_comparable':left['taxonomy_digest']==right['taxonomy_digest'],'missing_fields_preserved':True}

def compare_embeddings(left_path,right_path,*,left_descriptor,right_descriptor,normalize=True):
    try:import numpy as np
    except ImportError as e:raise CVRSError('DEPENDENCY_UNAVAILABLE','NumPy required') from e
    if left_descriptor!=right_descriptor:raise CVRSError('INCOMPARABLE','embedding providers/preprocessing/weights differ')
    a=np.load(left_path,allow_pickle=False);b=np.load(right_path,allow_pickle=False)
    if a.ndim!=2 or b.ndim!=2 or a.shape[1]!=b.shape[1] or not len(a) or not len(b) or not(np.isfinite(a).all() and np.isfinite(b).all()):raise ValueError('finite nonempty N x D embedding matrices required')
    if normalize:
        for x in (a,b):
            if (np.linalg.norm(x,axis=1)==0).any():raise ValueError('zero embeddings cannot be normalized')
        a=a/np.linalg.norm(a,axis=1,keepdims=True);b=b/np.linalg.norm(b,axis=1,keepdims=True)
    delta=a.mean(0)-b.mean(0)
    return {'kind':'DESCRIPTIVE_EMBEDDING_COMPARISON','left_sha256':file_digest(left_path),'right_sha256':file_digest(right_path),
        'provider_digest':digest(left_descriptor),'left_n':len(a),'right_n':len(b),'dimensions':a.shape[1],'normalized':normalize,
        'mean_embedding_L2':float(np.linalg.norm(delta)),'linear_MMD_squared_biased':float(delta@delta),
        'diagonal_variance_L1':float(np.abs(a.var(0)-b.var(0)).sum()),
        'limits':'Descriptive biased moment distances, not Fréchet distance, calibrated domain-gap score, or proof of synthetic-data quality.'}
