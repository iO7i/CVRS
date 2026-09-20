"""Read immutable historical payload fixtures through named, explicit readers."""
from pathlib import Path
from cvsubstrate.provenance.io import read_json,file_digest,digest
from cvsubstrate.schemas.registry import validate_artifact
from cvsubstrate.errors import SchemaMismatch,ArtifactIntegrityError

def inspect_compatibility(manifest,root):
    definition=read_json(Path(manifest)) if isinstance(manifest,(str,Path)) else manifest
    rows=[]
    from cvsubstrate.provenance.io import safe_join
    for record in definition['artifacts']:
        path=safe_join(Path(root),record['path'])
        if file_digest(path)!=record['sha256']:raise ArtifactIntegrityError('historical compatibility fixture changed')
        result=validate_artifact(read_json(path),record['schema'])
        rows.append({'source_release':definition['source_release'],'path':record['path'],**result})
    return {'historical_readers':rows,'source_digest':digest(definition),'claim':'These exact historical bytes remain readable; not an invented guarantee about unknown future schemas.'}
