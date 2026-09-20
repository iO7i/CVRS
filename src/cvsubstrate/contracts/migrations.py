"""One explicit, loss-audited migration; unknown schema versions are rejected.

Never rewrite a dataset or run in place. A new canonical record has a new digest.
Existing source evidence stays immutable and its original digest is retained.
"""
from pathlib import Path
from cvsubstrate.contracts.models import GenerationMetadata
from cvsubstrate.contracts.research import Quantity,SyntheticRecord
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import digest,file_digest,read_json,write_json
from cvsubstrate.provenance.artifact_set import seal_directory


def migrate_generation(path:Path,output:Path,*,sample_id:str):
    output=Path(output)
    if output.exists():raise CVRSError('OUTPUT_EXISTS','migration creates new output; source is never overwritten')
    value=read_json(path)
    if value.get('schema_version','1.0')!='1.0':raise CVRSError('SCHEMA_VERSION','unsupported source version')
    old=GenerationMetadata.model_validate(value)
    groups={}
    for group in ['planned','observed']:
        quantities={}
        for key,v in getattr(old,group).items():
            quantities[key]=Quantity(status='unknown' if v is None else 'declared',value=v,
                unit=old.units.get(key,'unknown') if isinstance(v,(int,float,list)) else None,
                method='Copied from legacy metadata; measurement provenance was not supplied')
        groups[group]=quantities
    for key in ['occlusion_fraction','truncation_fraction']:
        value=getattr(old,key)
        groups['observed'][key]=Quantity(status='unknown' if value is None else 'declared',value=value,
            unit='fraction',method=old.visibility_definition)
    if old.coordinate_convention is not None:
        groups['observed']['legacy_coordinate_convention']=Quantity(status='declared',value=old.coordinate_convention)
    new=SyntheticRecord(sample_id=sample_id,generator='unknown-legacy-generator',
        simulator=old.simulator,simulator_version=old.simulator_version,engine=old.engine,engine_version=old.engine_version,
        generation_revision=old.generation_revision,scene_id=old.scene_id,asset_ids=old.asset_ids,seed=old.seed,
        annotation_method=old.annotation_method,planned=groups['planned'],observed=groups['observed'],
        raw_sidecar_digest=file_digest(path),notes='Explicit migration. Legacy observations are declared, not retrospectively certified as measured.')
    output.mkdir(parents=True);write_json(output/'source.json',old);write_json(output/'record.json',new)
    audit={'schema_version':'1.0','migration':'GenerationMetadata.v1 -> SyntheticRecord.v1',
        'original_file_sha256':file_digest(path),'source_contract_digest':digest(old),'target_contract_digest':digest(new),
        'source_mutated':False,'unresolved':['generator identity','measurement provenance not recorded in legacy contract'],
        'limits':'Missing units retained as unknown, not inferred. Camera/asset details not fabricated.'}
    write_json(output/'migration.json',audit);seal_directory(output);return audit
