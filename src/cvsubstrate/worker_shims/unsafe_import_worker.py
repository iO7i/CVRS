"""Explicitly trusted legacy serialization -> JSON, isolated from the controller."""
from runtime_common import main,check_file,offline,dependency

def jsonable(v):
    if isinstance(v,dict):return {str(k):jsonable(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [jsonable(x) for x in v]
    if hasattr(v,'detach'):v=v.detach().cpu()
    if hasattr(v,'tolist'):return jsonable(v.tolist())
    if v is None or isinstance(v,(str,int,float,bool)):return v
    if hasattr(v,'pred_instances'):
        p=v.pred_instances
        return {'boxes':jsonable(p.bboxes),'scores':jsonable(p.scores),'labels':jsonable(p.labels)}
    raise RuntimeError('SERIALIZATION_UNSUPPORTED: unknown object '+type(v).__name__)

def run(req):
    offline();p=check_file(req['path'],req['sha256']);kind=req['format']
    if kind=='numpy':
        dependency('numpy');import numpy as np
        v=np.load(p,allow_pickle=False)
    elif kind=='pickle':
        if not req.get('trust_unsafe_pickle'):raise RuntimeError('PICKLE_TRUST: explicit trusted-input approval required')
        import pickle
        with p.open('rb') as f:v=pickle.load(f)
    else:raise RuntimeError('FORMAT_UNSUPPORTED: expected numpy or pickle')
    return {'value':jsonable(v),'source_sha256':req['sha256'],'native_execution_verified':False,'unsafe_pickle_used':kind=='pickle'}
if __name__=='__main__':main(run)
