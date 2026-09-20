"""Declared-license policy checks; not legal advice or a permission inference."""
from cvsubstrate.provenance.io import digest

def audit_licenses(value):
    rows=[]
    for item in value.get('artifacts',value.get('assets',[])):
        declared=item.get('license_id',item.get('license','unknown'));rights=item.get('redistribution','unknown')
        status='BLOCK' if rights in {'prohibited','unknown'} or declared in {None,'unknown','UNKNOWN','LicenseRef-Owner-Decision-Pending'} else 'DECLARED_ALLOWED_REVIEW_REQUIRED'
        rows.append({'id':item.get('id',item.get('path','unnamed')),'kind':item.get('kind','unknown'),
                     'license':declared,'redistribution':rights,'status':status})
    return {'status':'BLOCK' if not rows or any(r['status']=='BLOCK' for r in rows) else 'DECLARED_ALLOWED_REVIEW_REQUIRED',
        'artifacts':rows,'input_digest':digest(value),'meaning':'Only supplied metadata is checked; dependencies, weights, data and code have separate rights. No license grant is inferred.'}
