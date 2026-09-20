"""Schema inventory, envelopes, explicit migration graph, and run derivations.

No downgrade is inferred. Untagged legacy payloads require a caller-specified
schema. Legacy source evidence is always preserved in a separate directory.
"""
from __future__ import annotations
from collections import deque
from pathlib import Path
import shutil
from cvsubstrate.contracts.groundwork import ArtifactEnvelope
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import digest,read_json,write_json,file_digest
from cvsubstrate.provenance.artifact_set import seal_directory,assert_not_inside_sealed

def schema_registry():
    from cvsubstrate.contracts.models import SCHEMAS
    from cvsubstrate.contracts.research import RESEARCH_SCHEMAS
    from cvsubstrate.contracts.groundwork import GROUNDWORK_SCHEMAS
    from cvsubstrate.execution.plugins import WorkerPlugin
    from cvsubstrate.heritage.catalogue import CatalogueEntry
    from cvsubstrate.evaluation.reference_dota import DotaReference
    from cvsubstrate.contracts.synthetic import SYNTHETIC_SCHEMAS
    from cvsubstrate.contracts.frontier import FRONTIER_SCHEMAS
    values=FRONTIER_SCHEMAS+SCHEMAS+RESEARCH_SCHEMAS+GROUNDWORK_SCHEMAS+SYNTHETIC_SCHEMAS+[WorkerPlugin,CatalogueEntry,DotaReference]
    from cvsubstrate.foundation.identity import SCHEMAS as IDENTITY_SCHEMAS
    from cvsubstrate.artifacts.dependencies import SCHEMAS as DEP_SCHEMAS
    from cvsubstrate.datasets.sensors import SCHEMAS as SENSOR_SCHEMAS
    from cvsubstrate.data.asset_lineage import SCHEMAS as ASSET_SCHEMAS
    from cvsubstrate.vision.prompts import SCHEMAS as PROMPT_SCHEMAS
    from cvsubstrate.vision.assets import SCHEMAS as MODEL_SCHEMAS
    from cvsubstrate.vision.ontology import SCHEMAS as ONTOLOGY_SCHEMAS
    from cvsubstrate.research.claims import SCHEMAS as CLAIM_SCHEMAS
    from cvsubstrate.campaigns.native import SCHEMAS as CAMPAIGN_SCHEMAS
    values+=IDENTITY_SCHEMAS+DEP_SCHEMAS+SENSOR_SCHEMAS+ASSET_SCHEMAS+PROMPT_SCHEMAS+MODEL_SCHEMAS+ONTOLOGY_SCHEMAS+CLAIM_SCHEMAS+CAMPAIGN_SCHEMAS
    from cvsubstrate.adoption.contracts import ADOPTION_SCHEMAS
    from cvsubstrate.product.contracts import PRODUCT_SCHEMAS
    from cvsubstrate.product.interchange import SCHEMAS as EXCHANGE_SCHEMAS
    values+=ADOPTION_SCHEMAS+PRODUCT_SCHEMAS+EXCHANGE_SCHEMAS
    if len({c.__name__ for c in values})!=len(values):raise ValueError('duplicate schema class identity')
    return {c.__name__:c for c in values}

def inspect_schema(name):
    try:return schema_registry()[name].model_json_schema()
    except KeyError as exc:raise CVRSError('SCHEMA_UNKNOWN','unknown schema '+name) from exc

def validate_artifact(value,schema_name=None):
    if value.get('schema_name') and 'payload' in value:
        e=ArtifactEnvelope.model_validate(value);name=e.schema_name;payload=e.payload
        if str(payload.get('schema_version','1.0'))!=e.payload_version:raise CVRSError('SCHEMA_MISMATCH','envelope payload version differs from body')
    else:
        if not schema_name:raise CVRSError('SCHEMA_REQUIRED','untagged legacy artifacts need --schema')
        name=schema_name;payload=value
    reg=schema_registry()
    if name not in reg:raise CVRSError('SCHEMA_UNKNOWN',name)
    obj=reg[name].model_validate(payload)
    return {'schema':name,'status':'VALID','payload_digest':digest(obj)}

class MigrationRegistry:
    def __init__(self):self.edges={}
    def register(self,schema,source,target,fn):
        key=(schema,source,target)
        if key in self.edges:raise ValueError('duplicate migration edge')
        if source==target:raise ValueError('self migration')
        self.edges[key]=fn
    def migrate(self,value,*,schema,source,target):
        queue=deque([(source,[])]);visited={source};route=None
        while queue:
            v,steps=queue.popleft()
            if v==target:route=steps;break
            for (s,a,b),fn in self.edges.items():
                if s==schema and a==v and b not in visited:visited.add(b);queue.append((b,steps+[(a,b,fn)]))
        if route is None:raise CVRSError('MIGRATION_UNSUPPORTED','no explicit forward migration path; downgrades are not synthesized')
        current=value;history=[]
        for a,b,fn in route:
            before=digest(current);current=fn(current)
            history.append({'from':a,'to':b,'source_digest':before,'target_digest':digest(current)})
        return current,history

def registry():
    r=MigrationRegistry()
    # Supported legacy envelope input 1.0 is {schema_name,payload_version,body}; 1.1 standardizes payload.
    def envelope_v1(v):
        allowed={'schema_version','schema_name','payload_version','body','source_digest','migration_history'}
        if set(v)-allowed or 'body' not in v:raise ValueError('not a supported envelope-1.0 record')
        out=dict(v);out['payload']=out.pop('body');out['schema_version']='1.1';return out
    r.register('ArtifactEnvelope','1.0','1.1',envelope_v1)
    return r

def migrate_artifact(source:Path,destination:Path,*,schema_name=None):
    source=Path(source);destination=Path(destination)
    assert_not_inside_sealed(destination)
    if destination.exists():raise CVRSError('OUTPUT_EXISTS','migration never overwrites')
    value=read_json(source);history=[]
    if 'body' in value and value.get('schema_name'):
        value,history=registry().migrate(value,schema='ArtifactEnvelope',source=value.get('schema_version','1.0'),target='1.1')
        result=ArtifactEnvelope.model_validate(value)
    elif 'payload' in value and value.get('schema_name'):
        result=ArtifactEnvelope.model_validate(value)
    else:
        if not schema_name:raise CVRSError('SCHEMA_REQUIRED','name the legacy payload schema')
        validate_artifact(value,schema_name)
        result=ArtifactEnvelope(schema_name=schema_name,payload_version=value.get('schema_version','1.0'),payload=value,source_digest=file_digest(source))
        history=[{'operation':'wrap_without_semantic_conversion','source_file_sha256':file_digest(source),'payload_digest':digest(value)}]
    result.migration_history.extend(history);validate_artifact(result.model_dump(mode='json'))
    write_json(destination,result)
    return {'status':'MIGRATED','output':str(destination),'source_sha256':file_digest(source),'target_sha256':file_digest(destination),'steps':history}

def migrate_run(source:Path,destination:Path):
    from cvsubstrate.provenance.bundle import verify_bundle
    from cvsubstrate.provenance.artifact_set import verify_directory
    source=Path(source).resolve();destination=Path(destination).resolve()
    if destination==source or destination.is_relative_to(source):raise CVRSError('MIGRATION_LOCATION','new run derivation must be outside source')
    assert_not_inside_sealed(destination)
    if destination.exists():raise CVRSError('OUTPUT_EXISTS','new derivation required')
    verification=verify_bundle(source) if (source/'artifacts.json').exists() else verify_directory(source)
    if verification['status']!='VERIFIED':raise CVRSError('ARTIFACT_INTEGRITY','source run must verify first')
    destination.mkdir(parents=True);shutil.copytree(source,destination/'original')
    known={'experiment.json':'ExperimentSpec','dataset_manifest.json':'DatasetManifest','run.json':'RunManifest'};reports=[]
    for filename,kind in known.items():
        if (source/filename).exists():reports.append(migrate_artifact(source/filename,destination/'canonical'/(filename),schema_name=kind))
    write_json(destination/'migration_report.json',{'source_verification':verification,'reports':reports,'semantics':'Original run unchanged; canonical envelopes are derived evidence, not a new model execution.'})
    seal_directory(destination);return {'status':'MIGRATED','output':str(destination),'converted':len(reports)}

def export_schemas(destination:Path):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    reg=schema_registry()
    for name,cls in reg.items():write_json(destination/(name+'.schema.json'),cls.model_json_schema())
    return {'schemas':len(reg),'destination':str(destination)}
