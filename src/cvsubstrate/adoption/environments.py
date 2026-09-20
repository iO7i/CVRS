"""Observed-environment helpers and explicit recipe scaffolds, not an installer."""
from pathlib import Path
from typing import Any
import sys,subprocess,json,re,shlex
from cvsubstrate.adoption.common import output_tree,write_text
from cvsubstrate.provenance.io import write_json,digest
from cvsubstrate.errors import CVRSError

PACKS: dict[str, dict[str, Any]]={
 'mmdetection2':{'python':'3.8','modules':['mmdet','mmcv'],'operations':['predict','native_train'],'task':'hbb'},
 'mmdetection3':{'python':'3.10','modules':['mmdet','mmcv','mmengine'],'operations':['predict','native_train'],'task':'hbb'},
 'onedl':{'python':'3.10','modules':['mmdet','mmcv','mmengine'],'operations':['predict','native_train'],'task':'hbb'},
 'mmrotate':{'python':'3.8','modules':['mmrotate','mmdet','mmcv'],'operations':['predict','native_train'],'task':'obb'},
 'mmseg0':{'python':'3.8','modules':['mmseg','mmcv'],'operations':['predict','native_train'],'task':'semantic_labels'},
 'mmseg1':{'python':'3.10','modules':['mmseg','mmcv','mmengine'],'operations':['predict','native_train'],'task':'semantic_labels'},
 'mmyolo':{'python':'3.10','modules':['mmyolo','mmdet','mmengine'],'operations':['predict','native_train'],'task':'hbb'},
 'mmdeploy':{'python':'3.10','modules':['mmdeploy'],'operations':['export'],'task':'hbb'},
 'detectron2':{'python':'3.10','modules':['detectron2'],'operations':['predict','train'],'task':'hbb_masks_semantic'},
 'ultralytics':{'python':'3.11','modules':['ultralytics'],'operations':['predict','train','export'],'task':'hbb_obb_masks'},
 'rfdetr':{'python':'3.11','modules':['rfdetr'],'operations':['predict','train','export'],'task':'hbb'},
 'grounding-dino':{'python':'3.11','modules':['transformers'],'operations':['predict'],'task':'grounding'},
 'sam':{'python':'3.11','modules':['transformers'],'operations':['predict'],'task':'masks'},
 'sam2':{'python':'3.11','modules':['sam2'],'operations':['predict'],'task':'masks'},
 'sam3':{'python':'3.12','modules':['sam3'],'operations':['predict'],'task':'grounded_masks'},
 'torchgeo':{'python':'3.11','modules':['torchgeo'],'operations':['sample'],'task':'geospatial'},
 'terratorch':{'python':'3.11','modules':['terratorch'],'operations':['native_train','predict'],'task':'geospatial'},
 'core':{'python':'3.11','modules':['cvsubstrate'],'operations':['inspect','review'],'task':'metadata'},
}

def list_packs():return {k:{**v,'status':'IMPLEMENTED_ADAPTER_OR_NATIVE_COMMAND','native_certification':'NOT_CLAIMED'} for k,v in PACKS.items()}

def scaffold_environment(pack,destination,*,pins=None,python_version=None,base_image=None):
    if pack not in PACKS:raise ValueError('unknown stack pack')
    pins=pins or {};py=str(python_version or PACKS[pack]['python'])
    if not re.fullmatch(r'3\.\d+(?:\.\d+)?',py):raise ValueError('explicit Python version required')
    from packaging.requirements import Requirement
    reqs=[]
    for k,v in sorted(pins.items()):
        req=Requirement(k+'=='+v)
        if req.url:raise ValueError('use a separately reviewed source checkout for VCS packages')
        reqs.append(str(req))
    unresolved=not reqs
    image=base_image or 'python:'+py+'-slim'
    if '\n' in image or '\r' in image or ' ' in image:raise ValueError('invalid base image')
    with output_tree(destination,seal=False) as out:
        write_text(out/'requirements.txt','\n'.join(reqs)+'\n')
        write_text(out/'environment.yml','name: cvrs-'+pack+'\nchannels: [conda-forge]\ndependencies:\n  - python='+py+'\n  - pip\n  - pip:\n'+''.join('    - '+r+'\n' for r in reqs))
        write_text(out/'Dockerfile','FROM '+image+'\nWORKDIR /workspace\nCOPY requirements.txt /tmp/requirements.txt\nRUN python -m pip install --no-cache-dir -r /tmp/requirements.txt\nCMD ["python", "--version"]\n')
        write_text(out/'Apptainer.def','Bootstrap: docker\nFrom: '+image+'\n\n%files\n    requirements.txt /tmp/requirements.txt\n\n%post\n    python -m pip install --no-cache-dir -r /tmp/requirements.txt\n\n%runscript\n    exec "$@"\n')
        write_json(out/'recipe.json',{'pack':pack,'python':py,'requirements':reqs,'base_image':image,'status':'INCOMPLETE_PINS' if unresolved else 'DECLARED_NOT_SOLVED',
            'container_digest_pinned':'@sha256:' in image,'expected_modules':PACKS[pack]['modules'],
            'note':'Not a transitive lock, installability proof or CUDA wheel recipe. Native source/checkpoint requirements remain explicit.'})
        write_text(out/'README.md','# '+pack+' environment\n\nReview exact Python/Torch/CUDA/MMCV versions for your checkout. Supply pins from a working environment.\n'
            'No installers were run. Empty requirements are intentionally INCOMPLETE, not a working framework environment.\n'
            'Docker/Apptainer files are declarations; pin a base-image digest for reproducibility.\n')
    return {'status':'INCOMPLETE_PINS' if unresolved else 'DECLARED_NOT_SOLVED','destination':str(destination)}

def doctor(python=None):
    modules=sorted({m for v in PACKS.values() for m in v['modules']}|{'torch','numpy','pycocotools','rasterio','onnxruntime','openvino','tensorrt','fiftyone','supervision','wandb','mlflow','dvc','huggingface_hub'})
    code="""import sys,json,importlib.util,importlib.metadata as md
names="""+repr(modules)+"""
mapping=md.packages_distributions()
result={}
for n in names:
    distributions=mapping.get(n,[])
    versions={}
    for distribution in distributions:
        try: versions[distribution]=md.version(distribution)
        except md.PackageNotFoundError: pass
    result[n]={'installed':importlib.util.find_spec(n) is not None,'distributions':versions,'execution_verified':False}
print(json.dumps({'python':sys.version,'executable':sys.executable,'modules':result}))
"""
    from cvsubstrate.execution.process import run_command
    # Only Python's own metadata library executes; model modules are not imported.
    r=subprocess.run([python or sys.executable,'-c',code],capture_output=True,text=True,timeout=30)
    if r.returncode:raise CVRSError('ENVIRONMENT_PROBE','cannot inspect configured interpreter')
    result=json.loads(r.stdout);result['limits']='Presence is not compatibility or native execution proof. No package installation or model download.'
    result['suggestions']=['cvrs env scaffold '+k+' NEW_DIRECTORY' for k,v in PACKS.items() if any(not result['modules'][m]['installed'] for m in v['modules'])]
    return result

def hpc_script(spec_path,destination,*,scheduler='slurm',cpus=4,memory_gb=16,gpus=0,walltime='01:00:00',python='python',container=None):
    if scheduler not in {'slurm','pbs','lsf'}:raise ValueError('unsupported scheduler')
    if not(1<=cpus<=4096 and 1<=memory_gb<=100000 and 0<=gpus<=128):raise ValueError('resource request outside bounds')
    if not re.fullmatch(r'\d{1,3}:\d{2}:\d{2}',walltime):raise ValueError('walltime must be HH:MM:SS')
    hours,minutes,seconds=map(int,walltime.split(':'))
    if minutes>=60 or seconds>=60:raise ValueError('walltime minutes/seconds must be below 60')
    lsf_minutes=hours*60+minutes+(1 if seconds else 0)
    argv=[python,'-m','cvsubstrate','paper','run',str(Path(spec_path).resolve()),'--operation','predict','--out','${CVRS_OUTPUT}','--trust']
    if container:argv=['apptainer','exec',str(container),*argv]
    head={'slurm':['#SBATCH --cpus-per-task='+str(cpus),'#SBATCH --mem='+str(memory_gb)+'G','#SBATCH --time='+walltime]+(['#SBATCH --gpus='+str(gpus)] if gpus else []),
          'pbs':['#PBS -l select=1:ncpus='+str(cpus)+':mem='+str(memory_gb)+'gb'+(':ngpus='+str(gpus) if gpus else ''),'#PBS -l walltime='+walltime],
          'lsf':['#BSUB -n '+str(cpus),'#BSUB -M '+str(memory_gb*1024),'#BSUB -W '+str(lsf_minutes)]+(['#BSUB -gpu "num='+str(gpus)+'"'] if gpus else [])}[scheduler]
    command=' '.join('"${CVRS_OUTPUT}"' if a=='${CVRS_OUTPUT}' else shlex.quote(a) for a in argv)
    text='#!/usr/bin/env bash\n'+'\n'.join(head)+'\nset -euo pipefail\n: "${CVRS_OUTPUT:?Set a new shared-filesystem output directory}"\n'+command+'\n'
    p=Path(destination)
    if p.exists():raise CVRSError('OUTPUT_EXISTS','job script exists')
    write_text(p,text);return {'status':'SCRIPT_GENERATED','scheduler':scheduler,'submitted':False,'path':str(p)}
