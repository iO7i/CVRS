"""Explicit user-declared simulator export mappings, not simulator runtime plugins."""
from pathlib import Path
from cvsubstrate.contracts.synthetic import SyntheticSampleManifest,Observation
from cvsubstrate.contracts.research import SyntheticRecord
from cvsubstrate.provenance.io import read_json,write_json,file_digest
from cvsubstrate.errors import CVRSError
PROVIDERS={'generic','unreal_colosseum','blender','isaac','custom'}

def pointer(value,path):
    if path=='':return value
    if not path.startswith('/'):raise ValueError('mapping path must be RFC6901 JSON pointer')
    for key in path[1:].split('/'):
        key=key.replace('~1','/').replace('~0','~')
        try:value=value[int(key)] if isinstance(value,list) else value[key]
        except (KeyError,IndexError,TypeError,ValueError):return None
    return value

def import_export(raw_path:Path,mapping:dict,output:Path):
    provider=mapping['provider']
    if provider not in PROVIDERS:raise ValueError('unknown source provider')
    raw=read_json(raw_path);base=dict(mapping['record']);base['raw_sidecar_digest']=file_digest(raw_path)
    for target,path in mapping.get('record_fields',{}).items():
        if target not in {'sample_id','scene_id','scene_source','seed','generator','generator_version','simulator','simulator_version','engine','engine_version','generation_revision','annotation_method'}:raise ValueError('unsupported identity target')
        value=pointer(raw,path)
        if value is None and target in mapping.get('required_identity_fields',[]):raise ValueError('required identity missing')
        if value is not None:base[target]=value
    record=SyntheticRecord.model_validate(base);payload={'record':record.model_dump(mode='json')}
    allowed={'scene','lens','sensor','rendering','weather','illumination','compression','randomization','annotations','planned'}
    audit=[]
    for row in mapping.get('observations',[]):
        group=row['group']
        if group not in allowed:raise ValueError('unknown observation group')
        if row['name'] in payload.setdefault(group,{}):raise ValueError('duplicate target observation')
        value=pointer(raw,row['pointer']);status=row.get('status','simulator_reported')
        if value is None:
            if row.get('required'):raise ValueError(f"required observation missing: {row['pointer']}")
            obs=Observation()
        else:
            if 'scale' in row or 'offset' in row:
                if not isinstance(value,(int,float)) or isinstance(value,bool):raise ValueError('scaling requires numeric raw value')
                value=value*row.get('scale',1)+row.get('offset',0)
                status='derived'
            obs=Observation(status=status,value=value,unit=row.get('unit'),method=row.get('method','declared export mapping' if status=='derived' else None),
                input_digests=[file_digest(raw_path)] if status=='derived' else [])
        payload[group][row['name']]=obs.model_dump(mode='json');audit.append({'pointer':row['pointer'],'target':group+'.'+row['name'],'status':obs.status})
    m=SyntheticSampleManifest.model_validate(payload);output=Path(output)
    if output.exists():raise CVRSError('OUTPUT_EXISTS','choose new synthetic sidecar')
    write_json(output,m);return {'provider_label':provider,'manifest':str(output),'sha256':file_digest(output),'mapping_audit':audit,
        'native_simulator_executed':False,'format_scope':'only the explicitly supplied export field mapping'}
