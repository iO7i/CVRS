"""Simulator-neutral sidecar mapping with explicit units and missingness."""
from pathlib import Path
from cvsubstrate.contracts.research import Quantity,SidecarMapping,SyntheticRecord
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import digest,file_digest,read_json,write_json

MISSING=object()


def pointer(data,path):
    if path=='':return data
    if not path.startswith('/'):raise ValueError('JSON pointer must start with /')
    value=data
    for raw in path.split('/')[1:]:
        import re
        if re.search(r'~(?![01])',raw):raise ValueError('invalid JSON pointer escape')
        key=raw.replace('~1','/').replace('~0','~')
        if isinstance(value,dict):value=value.get(key,MISSING)
        elif isinstance(value,list) and key.isdigit() and (key=='0' or not key.startswith('0')):
            value=value[int(key)] if int(key)<len(value) else MISSING
        else:value=MISSING
        if value is MISSING:return MISSING
    return value


def map_sidecar(data:dict,mapping:SidecarMapping,*,source_digest=None):
    sid=pointer(data,mapping.sample_id_pointer)
    if sid is MISSING or not isinstance(sid,str):raise CVRSError('SIDECAR_ID','explicit string sample ID missing')
    groups={'planned':{},'observed':{}}
    for rule in mapping.fields:
        value=pointer(data,rule.pointer)
        if value is MISSING or value is None:
            if rule.required:raise CVRSError('SIDECAR_REQUIRED',f'missing required field {rule.pointer}')
            q=Quantity(status='unknown',value=None,unit=rule.unit,method=rule.method)
        else:
            if rule.scale!=1 or rule.offset!=0:
                if isinstance(value,bool) or not isinstance(value,(int,float)):raise ValueError('unit conversion needs numeric source value')
                value=value*rule.scale+rule.offset
            q=Quantity(status=rule.status,value=value,unit=rule.unit,method=rule.method,
                evidence=f'JSON pointer {rule.pointer}; mapping {mapping.name}')
        groups[rule.group][rule.target]=q
    identity={}
    for target,path in mapping.identity_pointers.items():
        if target not in {'generator_version','simulator_version','engine_version','generation_revision',
                          'scene_id','scene_source','asset_ids','seed','camera','annotation_method'}:
            raise ValueError('unsupported identity mapping target; never assign arbitrary attributes')
        value=pointer(data,path)
        if value is not MISSING and value is not None:identity[target]=value
    identity.setdefault('generator_version',mapping.generator_version)
    return SyntheticRecord(sample_id=sid,generator=mapping.generator,
        simulator=mapping.simulator,engine=mapping.engine,
        raw_sidecar_digest=source_digest or digest(data),planned=groups['planned'],observed=groups['observed'],
        notes='User-declared export mapping, not a tested simulator integration. Source digest is raw file bytes when imported through CLI, otherwise canonical JSON.',
        **identity)


def import_sidecar(path:Path,mapping:SidecarMapping,output:Path):
    if Path(output).exists():raise CVRSError('OUTPUT_EXISTS','sidecar output already exists')
    record=map_sidecar(read_json(path),mapping,source_digest=file_digest(path));write_json(output,record)
    return {'status':'SIDECAR_MAPPED','record_digest':digest(record),'output':str(output),
        'raw_source_digest':file_digest(path),'simulator_execution_verified':False}
