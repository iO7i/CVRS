"""Object-scale, density and provenance-aware domain comparison without models."""
from __future__ import annotations
from collections import Counter,defaultdict
import math
import statistics
from cvsubstrate.contracts.models import DatasetManifest
from cvsubstrate.contracts.research import SyntheticRecord
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import digest


def distribution(values):
    v=sorted(float(x) for x in values)
    if any(not math.isfinite(x) for x in v):raise ValueError('nonfinite measured value')
    if not v:return {'count':0,'min':None,'max':None,'mean':None,'std_population':None,'p10':None,'median':None,'p90':None,'reason':'no observations'}
    def q(p):
        idx=(len(v)-1)*p;i=int(idx);f=idx-i
        return v[i]*(1-f)+v[min(i+1,len(v)-1)]*f
    return {'count':len(v),'min':v[0],'max':v[-1],'mean':statistics.fmean(v),
        'std_population':statistics.pstdev(v),'p10':q(.1),'median':q(.5),'p90':q(.9),'reason':None}


def describe_dataset(m:DatasetManifest,split:str,sidecars:list[SyntheticRecord]|None=None):
    if split not in m.splits:raise CVRSError('UNKNOWN_SPLIT','diagnostic split not present')
    if m.splits[split].role=='locked_test':raise CVRSError('LOCKED_TEST','exploratory domain diagnostics cannot inspect locked test')
    ids=set(m.splits[split].sample_ids);samples=[s for s in m.samples if s.id in ids]
    width=[];height=[];area=[];aspect=[];border=[];density=[];cats=Counter();domains=Counter();sources=Counter()
    ignored=0
    for s in samples:
        domains[s.domain]+=1;sources[s.source_kind]+=1;count=0
        for b in s.boxes:
            if b.ignore or b.iscrowd:ignored+=1;continue
            x1,y1,x2,y2=b.xyxy;w,h=x2-x1,y2-y1
            width.append(w);height.append(h);area.append(w*h);aspect.append(w/h)
            border.append(min(x1,y1,s.width-x2,s.height-y2));cats[str(b.category_id)]+=1;count+=1
        density.append(count/(s.width*s.height/1e6))
    observed=defaultdict(list);missing=Counter();statuses=Counter();known_ids=set()
    for record in sidecars or []:
        if record.sample_id not in ids:continue
        if record.sample_id in known_ids:raise ValueError('duplicate sidecar record for selected sample')
        known_ids.add(record.sample_id)
        for key,q in record.observed.items():
            statuses[f'{key}:{q.status}']+=1
            if q.status=='unknown':missing[key]+=1
            elif isinstance(q.value,(int,float)) and not isinstance(q.value,bool):
                # Preserve units and evidence status: never average metres and feet
                # or human ratings and sensor measurements together.
                observed[f'{key}|unit={q.unit}|status={q.status}'].append(q.value)
    return {'schema_version':'1.0','kind':'DESCRIPTIVE_DATASET_DIAGNOSTICS','dataset_digest':digest(m),'split':split,
        'images':len(samples),'positive_objects':len(area),'ignored_annotations':ignored,
        'taxonomy':[c.model_dump(mode='json') for c in sorted(m.categories,key=lambda c:c.id)],'category_counts':dict(cats),'domain_counts':dict(domains),'source_counts':dict(sources),
        'geometry':{'bbox_width_px':distribution(width),'bbox_height_px':distribution(height),
            'bbox_area_px2':distribution(area),'sqrt_bbox_area_px':distribution([math.sqrt(x) for x in area]),
            'width_over_height':distribution(aspect),'nearest_border_px':distribution(border),
            'objects_per_megapixel':distribution(density)},
        'observations':{key:distribution(v) for key,v in observed.items()},
        'unknown_observations':dict(missing),'observation_status_counts':dict(statuses),
        'sidecar_coverage':{'present':len(known_ids),'missing':len(ids-known_ids)},
        'limits':'Descriptive marginal distributions, not a causal domain-gap score; no inferred realism, desert label, altitude, or GSD.'}


def compare_domains(left:dict,right:dict):
    if left.get('kind')!='DESCRIPTIVE_DATASET_DIAGNOSTICS' or right.get('kind')!='DESCRIPTIVE_DATASET_DIAGNOSTICS':
        raise ValueError('domain comparison requires two explicit dataset diagnostic reports')
    metrics={}
    for key in sorted(set(left['geometry'])&set(right['geometry'])):
        a,b=left['geometry'][key],right['geometry'][key]
        metrics[key]={'left':a,'right':b,'right_minus_left_mean':b['mean']-a['mean'] if a['mean'] is not None and b['mean'] is not None else None}
    return {'kind':'DESCRIPTIVE_DOMAIN_COMPARISON','left_dataset':left['dataset_digest'],'right_dataset':right['dataset_digest'],
        'left_split':left['split'],'right_split':right['split'],'geometry':metrics,
        'taxonomy_counts_comparable':left.get('taxonomy')==right.get('taxonomy') and left.get('taxonomy') is not None,
        'limits':'Differences in marginals identify possible distribution mismatches; they do not measure transfer benefit or realism.'}
