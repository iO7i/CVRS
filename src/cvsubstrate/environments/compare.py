"""Recipe-versus-observation comparison; declarations never become observations."""
from cvsubstrate.provenance.io import digest

def compare_environment(recipe:dict,observed:dict):
    requested=recipe.get('packages',{});actual=observed.get('packages',{})
    if isinstance(actual,list):actual={x['name']:x['version'] for x in actual}
    rows=[]
    for key in sorted(set(requested)|set(actual)):
        a=requested.get(key);b=actual.get(key)
        rows.append({'package':key,'requested':a,'observed':b,'status':'MATCH' if a==b else 'EXTRA' if a is None else 'MISSING' if b is None else 'DIFFERENT'})
    for k in ['python','cuda','driver','source_revision','container_digest']:
        if k in recipe or k in observed:rows.append({'field':k,'requested':recipe.get(k),'observed':observed.get(k),'status':'MATCH' if recipe.get(k)==observed.get(k) else 'DIFFERENT'})
    return {'recipe_digest':digest(recipe),'observation_digest':digest(observed),'differences':rows,
            'exact_declared_match':all(x['status'] in {'MATCH','EXTRA'} for x in rows),'execution_certified':False}
