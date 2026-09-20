"""First-use projects generated independently of the framework source tree."""
from pathlib import Path
import sys
from cvsubstrate.adoption.common import output_tree,write_text
from cvsubstrate.provenance.io import write_json

PROFILES={'detection':'Single native detector with a generated CPU conformance dataset',
 'heritage':'Wrap a trusted existing MMDetection project without rewriting its model',
 'aerial':'Use the existing raster/OBB tools with explicitly configured data and weights',
 'sim2real':'Six-arm software-fixture campaign; not a research result',
 'open-vocabulary':'Grounding model with an explicit prompt-set and model-asset identity',
 'segmentation':'Point/box/mask task with a compatible native model',
 'reproduction':'Inspect and re-evaluate an existing evidence capsule',
 'paper':'Bring an arbitrary trusted paper repository and reviewed argv manifest'}

def init_project(destination,*,profile='detection',name=None):
    if profile not in PROFILES:raise ValueError('unknown starter profile')
    with output_tree(destination,seal=False) as out:
        for directory in ('datasets','experiments','adapters','benchmarks','results'): (out/directory).mkdir()
        write_text(out/'.gitignore','results/\n.env\n.venv/\n__pycache__/\n*.pth\n*.pt\n')
        write_text(out/'cvrs.toml','project_version = "1"\nprofile = '+repr(profile)+'\n')
        info={'name':name or Path(destination).name,'profile':profile,'description':PROFILES[profile],
              'status':'GENERATED_REVIEW_REQUIRED','unresolved':[]}
        if profile=='detection':
            from cvsubstrate.data.fixtures import generate
            generate(out/'datasets'/'fixtures')
            import json
            exp=json.loads((out/'datasets/fixtures/real.json').read_text());exp['dataset']='../datasets/fixtures/dataset.json'
            write_json(out/'experiments'/'baseline.json',exp)
            command='cvrs run experiments/baseline.json --out results/first-run'
            info['requires']=['native worker with torch/torchvision installed'];info['purpose']='software_fixture'
        elif profile=='sim2real':
            from cvsubstrate.data.research_fixtures import generate_research_fixtures as research_generate
            research_generate(out/'datasets'/'fixtures')
            command='cvrs campaign run datasets/fixtures/campaign.json --out results/campaign'
            info['purpose']='software_fixture';info['requires']=['native worker']
        else:
            write_json(out/'experiments'/'requirements.json',{'profile':profile,'required_local_assets':['native_repository_or_model','checkpoint_or_asset_manifest','dataset_or_capsule'],
                'unresolved':['Choose a matching stack or existing recipe; bind source revision, input hashes and exact output semantics'],
                'unsafe_code_trusted':False})
            info['unresolved']=['Native input paths/assets and adapter-specific job specification must be supplied']
            command='cvrs env list\ncvrs recipe list\ncvrs stack list\ncvrs doctor'
        write_json(out/'project.json',info)
        write_text(out/'README.md','# '+(name or Path(destination).name)+'\n\n'+PROFILES[profile]+'\n\n'
            'This is your experiment project, not a fork of the framework. Use a new result directory for every execution.\n\n'
            '```bash\n'+command+'\n```\n\n'
            'CPU fixture data is not real imagery. Unsupported or missing native assets are explicit; nothing downloads automatically.\n'
            'Keep model stacks in separate interpreters; review all executable configurations and checkpoints.\n')
    return {'status':'PROJECT_CREATED','profile':profile,'path':str(destination),'unresolved':info['unresolved']}

def adapter_project(name,destination,*,backend=None):
    from cvsubstrate.adapters.sdk import scaffold
    # The public SDK honestly starts with validation; authors implement model behavior.
    result=scaffold(Path(destination),name,kind='model')
    return result
