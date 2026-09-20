"""Zero-rewrite heritage import, environment recipes, and generated handoff."""
from pathlib import Path
from cvsubstrate.contracts.models import ExperimentSpec,AdapterSpec,CheckpointRef,EvaluationProtocol
from cvsubstrate.heritage.profiles import get_profile
from cvsubstrate.heritage.importer import import_project
from cvsubstrate.heritage.capsule import write_capsule
from cvsubstrate.data.manifest import load_manifest
from cvsubstrate.provenance.io import read_json,write_json,atomic_bytes,digest,file_digest
from cvsubstrate.provenance.artifact_set import seal_directory
from cvsubstrate.errors import CVRSError

def import_wizard(*,config:Path,source_root:Path,checkpoint:Path,dataset:Path,output:Path,profile:str,
                  revision:str,category_map:dict,python_version:str|None=None,packages:dict|None=None,base_image=None):
    out=Path(output)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','wizard requires a new directory')
    p=get_profile(profile);manifest=load_manifest(dataset)
    if not category_map or len(set(category_map.values()))!=len(category_map):raise ValueError('explicit injective category map required')
    if not set(category_map.values())<=set(c.id for c in manifest.categories):raise ValueError('map references unknown categories')
    out.mkdir(parents=True)
    report=import_project(config,source_root,out/'legacy',upstream=p['upstream'],revision=revision,checkpoint=checkpoint,dataset=dataset)
    ref=read_json(out/'legacy'/'reference.json');ref['config']='legacy/'+ref['config'];ref['environment_reference']='environment/capsule.json'
    write_json(out/'heritage.json',ref);write_json(out/'profile.json',p)
    original_config=str((out/ref['config']).resolve())
    adapter=AdapterSpec(name='mmdetection',config={'config_path':original_config,'config_sha256':file_digest(config),
        'category_map':category_map,'upstream':p['upstream'],'revision':revision,'profile':profile,'trust_executable_config':False,'device':'cpu'})
    spec=ExperimentSpec(name='heritage-import',dataset=str(Path(dataset).resolve()),dataset_sha256=digest(manifest),adapter=adapter,
        checkpoint=CheckpointRef(path=str(Path(checkpoint).resolve()),sha256=file_digest(checkpoint),trust='trusted_legacy_pickle'))
    write_json(out/'experiment.json',spec)
    if python_version and packages:
        env=write_capsule(out/'environment',python_version,packages,source={'revision':revision,'upstream':p['upstream']},base_image=base_image)
    else:
        (out/'environment').mkdir();env={'status':'UNRESOLVED','profile':profile,'required_packages':p['packages'],'missing':['exact Python version','exact package versions'],'execution_verified':False}
        write_json(out/'environment'/'capsule.json',env)
    write_json(out/'checkpoint.json',spec.checkpoint)
    write_json(out/'dataset.json',{'path':str(Path(dataset).resolve()),'sha256':digest(manifest),'bytes_bundled':False})
    instructions='# Imported heritage experiment\nOriginal configuration inheritance is preserved under legacy/source. Python config code was NOT executed.\n1. Review config and checkpoint provenance/licensing. Explicitly set trust_executable_config=true only for trusted code.\n2. Supply the exact legacy environment; generated recipes are not installation certificates.\n3. Run `cvrs run experiment.json --worker-python /path/to/legacy/python --evaluator-python /path/to/evaluator/python --out runs`.\n4. Use `cvrs heritage certify heritage.json --run <run>` only after a genuine run.\nThe absolute local dataset/checkpoint/config paths are materialization locations; update them on another machine and retain their hashes. No checkpoint/dataset bytes were copied.\n'
    atomic_bytes(out/'RUNME.md',instructions.encode());write_json(out/'launch.json',{'spec':'experiment.json','worker_python':None,'evaluator_python':None,'status':'REQUIRES_LOCAL_ENVIRONMENTS_AND_TRUST_REVIEW'})
    return {'status':'IMPORTED','output':str(out),'config_files':report['config_files_preserved'],'execution_verified':False,'environment':env['status'] if 'status' in env else env['metadata_status']}
