"""Conservative declared-constraint analysis, NOT a pip/conda/CUDA solver."""
from collections import defaultdict
from packaging.requirements import Requirement,InvalidRequirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version,InvalidVersion
from cvsubstrate.adoption.inspect import inspect_repository

def _bounds(spec):
    low=None;high=None;exact=[];unknown=[]
    for s in spec:
        try:v=Version(s.version.rstrip('.*'))
        except InvalidVersion:unknown.append(str(s));continue
        op=s.operator
        if op=='==' and not s.version.endswith('.*'):exact.append(v)
        elif op in {'>','>='}:
            b=(v,op=='>=')
            if low is None or v>low[0] or v==low[0] and not b[1]:low=b
        elif op in {'<','<='}:
            b=(v,op=='<=')
            if high is None or v<high[0] or v==high[0] and not b[1]:high=b
        elif op=='==' and s.version.endswith('.*'):
            parts=list(v.release);up=parts[:-1]+[parts[-1]+1]
            lo=(v,True);hi=(Version('.'.join(map(str,up))),False)
            if low is None or lo[0]>low[0]:low=lo
            if high is None or hi[0]<high[0]:high=hi
        elif op=='~=':
            parts=list(v.release);up=parts[:-1] if len(parts)>1 else parts
            up[-1]+=1;lo=(v,True);hi=(Version('.'.join(map(str,up))),False)
            if low is None or lo[0]>low[0]:low=lo
            if high is None or hi[0]<high[0]:high=hi
        elif op not in {'!='}:unknown.append(str(s))
    if exact:
        # PEP 440 public-version equality can intersect an explicit local build.
        if not any(spec.contains(x,prereleases=True) for x in exact):return 'CONFLICT',unknown
    if low and high and (low[0]>high[0] or low[0]==high[0] and not(low[1] and high[1])):return 'CONFLICT',unknown
    if low and high and low[0]==high[0] and not spec.contains(low[0],prereleases=True):return 'CONFLICT',unknown
    return 'NO_DECLARED_CONFLICT' if not unknown else 'UNKNOWN',unknown

def explain_constraints(reports,marker_environment=None):
    groups=defaultdict(list);unresolved=[]
    for report in reports:
        report=report.model_dump(mode='json') if hasattr(report,'model_dump') else report
        for obs in report['observations']:
            if obs['kind'] not in {'requirement','python_constraint'}:continue
            raw=('python'+obs['value']) if obs['kind']=='python_constraint' else obs['value']
            try:req=Requirement(raw)
            except InvalidRequirement:
                unresolved.append({'value':raw,'reason':'not a supported PEP 508 declaration'});continue
            if req.url:
                unresolved.append({'value':raw,'reason':'VCS/direct URL dependencies need explicit revision review'});continue
            if req.marker:
                if marker_environment is None:
                    unresolved.append({'value':raw,'reason':'environment marker unresolved; specify a target'});continue
                if not req.marker.evaluate(marker_environment):continue
            groups[req.name.lower().replace('_','-')].append({'specifier':str(req.specifier),'repo':report['repository_name'],
                'source':obs['path'],'line':obs['line']})
    checks=[]
    for name,items in sorted(groups.items()):
        combined=SpecifierSet(','.join(x['specifier'] for x in items if x['specifier']))
        status,unknown=_bounds(combined)
        checks.append({'package':name,'status':status,'combined':str(combined),'evidence':items,'unknown':unknown})
    conflicts=[c for c in checks if c['status']=='CONFLICT']
    return {'status':'DECLARED_CONFLICTS' if conflicts else 'NO_PROVEN_CONFLICTS',
        'checks':checks,'unresolved':unresolved,'installability_proven':False,
        'boundary_warning':'Process separation works only across explicit materialized stage boundaries. It does not repair imports inside a shared model or preserve cross-process gradients.',
        'next_action':'Preserve whole native environments. Supply an explicit stage map before splitting a composite research system.',
        'limits':['No transitive dependency resolution','No CUDA wheel/ABI/compiler proof','README declarations are candidates, not authoritative requirements']}

def explain_repositories(roots,marker_environment=None):
    return explain_constraints([inspect_repository(p) for p in roots],marker_environment)
