"""Hierarchical source assets and auditable protected-split contamination checks."""
from pydantic import Field,model_validator
from cvsubstrate.contracts.models import Contract,ID,SHA256
from cvsubstrate.provenance.io import digest
class SourceAsset(Contract):
    id: ID
    kind: str
    sha256: SHA256|None=None
    parents: list[ID]=Field(default_factory=list)
    license: str='UNKNOWN'
class SampleLineage(Contract):
    sample_id: ID
    split: str
    asset_ids: list[ID]=Field(default_factory=list)
class AssetLineage(Contract):
    assets: list[SourceAsset]
    samples: list[SampleLineage]
    @model_validator(mode='after')
    def valid(self):
        by={a.id:a for a in self.assets}
        if len(by)!=len(self.assets) or len({s.sample_id for s in self.samples})!=len(self.samples):raise ValueError('duplicate asset/sample')
        if any(p not in by for a in self.assets for p in a.parents) or any(p not in by for s in self.samples for p in s.asset_ids):raise ValueError('unknown lineage parent')
        visiting=set();done=set()
        def walk(i):
            if i in visiting:raise ValueError('asset lineage cycle')
            if i in done:return
            visiting.add(i)
            for p in by[i].parents:walk(p)
            visiting.remove(i);done.add(i)
        for i in by:walk(i)
        return self

def check_asset_leakage(graph:AssetLineage,*,protected=('locked_test',),against=('train','dev','selection'),kinds=None,allowed_asset_ids=()):
    by={a.id:a for a in graph.assets};memo={};allowed=set(allowed_asset_ids)
    def closure(i):
        if i not in memo:memo[i]={i}|set().union(*(closure(p) for p in by[i].parents))
        return memo[i]
    ownership={}
    for s in graph.samples:
        for i in set().union(*(closure(p) for p in s.asset_ids)):
            if i in allowed or kinds is not None and by[i].kind not in kinds:continue
            key='sha256:'+by[i].sha256 if by[i].sha256 else 'id:'+i
            ownership.setdefault(key,[]).append({'sample_id':s.sample_id,'split':s.split,'asset_id':i})
    conflicts=[]
    for key,refs in sorted(ownership.items()):
        if any(r['split'] in protected for r in refs) and any(r['split'] in against for r in refs):conflicts.append({'asset_identity':key,'references':refs})
    return {'policy':{'protected':list(protected),'against':list(against),'kinds':kinds,'allowed':sorted(allowed)},'lineage_sha256':digest(graph),'conflicts':conflicts,'status':'CONFLICT' if conflicts else 'NO_DECLARED_LINEAGE_CONFLICT','near_duplicate_detection':False}
SCHEMAS=[SourceAsset,SampleLineage,AssetLineage]
