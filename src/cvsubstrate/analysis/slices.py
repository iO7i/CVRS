"""Bounded, declarative three-valued filters. Never Python eval or attribute access."""
from __future__ import annotations
from cvsubstrate.contracts.groundwork import SliceExpression
from cvsubstrate.contracts.models import DatasetManifest
from cvsubstrate.provenance.io import digest
MISSING=object()
OPS={'eq','ne','lt','le','gt','ge','in','not_in','exists'}

def lookup(record,field):
    if not isinstance(field,str) or not field or len(field)>256:raise ValueError('invalid field')
    value=record
    for part in field.split('.'):
        if not part or part.startswith('_'):raise ValueError('private/empty field not permitted')
        if not isinstance(value,dict) or part not in value:return MISSING
        value=value[part]
    return MISSING if value is None else value

def validate_expression(expr,depth=0,counter=None):
    counter=[0] if counter is None else counter;counter[0]+=1
    if depth>16 or counter[0]>256:raise ValueError('slice expression safety limits exceeded')
    if not isinstance(expr,dict):raise ValueError('expression node must be object')
    if set(expr)=={'all'} or set(expr)=={'any'}:
        children=expr[next(iter(expr))]
        if not isinstance(children,list) or not children:raise ValueError('all/any needs nonempty children')
        for child in children:validate_expression(child,depth+1,counter)
    elif set(expr)=={'not'}:validate_expression(expr['not'],depth+1,counter)
    else:
        if set(expr)-{'field','op','value'} or not {'field','op'}<=set(expr):raise ValueError('invalid comparison shape')
        if expr['op'] not in OPS:raise ValueError('unsupported operator')
        lookup({},expr['field'])
        if expr['op']!='exists' and 'value' not in expr:raise ValueError('comparison missing value')
        if expr['op'] in {'in','not_in'} and (not isinstance(expr['value'],list) or len(expr['value'])>10000):raise ValueError('membership requires bounded list')
    return True

def _match(expr,record):
    if 'all' in expr:
        vals=[_match(x,record) for x in expr['all']]
        return False if False in vals else None if None in vals else True
    if 'any' in expr:
        vals=[_match(x,record) for x in expr['any']]
        return True if True in vals else None if None in vals else False
    if 'not' in expr:
        v=_match(expr['not'],record);return None if v is None else not v
    v=lookup(record,expr['field']);op=expr['op']
    if op=='exists':return v is not MISSING
    if v is MISSING:return None
    target=expr['value']
    if op=='eq':return v==target
    if op=='ne':return v!=target
    if op=='in':return v in target
    if op=='not_in':return v not in target
    if isinstance(v,bool) or isinstance(target,bool):raise ValueError('boolean cannot be used as numeric bound')
    if not (isinstance(v,(int,float)) and isinstance(target,(int,float))) and not(type(v) is str and type(target) is str):raise ValueError('ordered comparison types differ')
    return {'lt':lambda:v<target,'le':lambda:v<=target,'gt':lambda:v>target,'ge':lambda:v>=target}[op]()

def matches(record,policy:SliceExpression|dict):
    p=policy if isinstance(policy,SliceExpression) else SliceExpression.model_validate(policy)
    validate_expression(p.expression);result=_match(p.expression,record)
    if result is None and p.missing_policy=='error':raise ValueError('slice requires metadata that is unknown')
    return result

def select_slice(m:DatasetManifest,split:str,policy:SliceExpression|dict,*,metadata=None):
    p=policy if isinstance(policy,SliceExpression) else SliceExpression.model_validate(policy);validate_expression(p.expression)
    ids=set(m.splits[split].sample_ids);selected=[];unknown=[];objects=[];metadata=metadata or {}
    for s in m.samples:
        if s.id not in ids:continue
        base={**s.model_dump(mode='json'),'metadata':metadata.get(s.id,{})}
        if p.level=='image':
            verdict=matches(base,p)
            if verdict is True:selected.append(s.id)
            elif verdict is None:unknown.append(s.id)
        else:
            for j,b in enumerate(s.boxes):
                x1,y1,x2,y2=b.xyxy;row={**base,'object':{**b.model_dump(mode='json'),'index':j,'width_px':x2-x1,'height_px':y2-y1,'area_px2':(x2-x1)*(y2-y1)}}
                verdict=matches(row,p)
                if verdict is True:objects.append({'sample_id':s.id,'object_index':j})
                elif verdict is None:unknown.append({'sample_id':s.id,'object_index':j})
            if any(x['sample_id']==s.id for x in objects):selected.append(s.id)
    return {'schema_version':'1.0','dataset_digest':digest(m),'split':split,'policy':p.model_dump(mode='json'),
        'sample_ids':selected,'objects':objects,'unknown_excluded':unknown,
        'evaluation_semantics':'Object selections are diagnostic targets, not permission to remove other annotations from official evaluation.'}
