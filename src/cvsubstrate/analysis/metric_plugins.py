"""Explicit callable registry for dataset diagnostics and immutable slice receipts."""
from typing import Protocol
from cvsubstrate.provenance.io import digest
class DistributionMetric(Protocol):
    def __call__(self,left:list[dict],right:list[dict])->dict:...
class DomainMetricRegistry:
    def __init__(self):self._metrics={}
    def register(self,name,version,fn,*,family):
        if family not in {'metadata','pixels','embeddings','geometry'}:raise ValueError('unknown metric family')
        if name in self._metrics or not callable(fn):raise ValueError('duplicate/non-callable metric')
        self._metrics[name]=(version,fn,family)
    def evaluate(self,name,left,right):
        version,fn,family=self._metrics[name];result=fn(left,right)
        if not isinstance(result,dict):raise ValueError('metric must return a JSON mapping')
        return {'name':name,'version':version,'family':family,'left_sha256':digest(left),'right_sha256':digest(right),'result':result,'result_sha256':digest(result),'official_benchmark_metric':False}

def slice_receipt(records,predicate):
    from cvsubstrate.analysis.slices import validate_expression,_match
    validate_expression(predicate)
    selected=[]
    for r in records:
        if _match(predicate,r) is True:selected.append({'sample_id':r['sample_id'],'object_id':r.get('object_id')})
    return {'predicate':predicate,'predicate_sha256':digest(predicate),'universe_sha256':digest(records),'selected':selected,'selected_sha256':digest(selected),'count':len(selected)}
