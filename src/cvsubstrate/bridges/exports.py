"""Portable exports for services we do not host. No submission happens here."""
from pathlib import Path
import shlex,shutil
from cvsubstrate.adoption.common import output_tree,write_text
from cvsubstrate.provenance.io import read_json,write_json,file_digest,safe_join
from cvsubstrate.provenance.artifact_set import verify_directory

def export_codeocean(capsule,destination,*,argv,environment=None):
    root=Path(capsule)
    if (root/'integrity.json').is_file() and verify_directory(root)['status']!='VERIFIED':raise ValueError('source capsule integrity failed')
    if not argv or any('\n' in a or '\r' in a for a in argv):raise ValueError('provide an explicit non-shell command')
    with output_tree(destination) as out:
        (out/'code').mkdir();(out/'data').mkdir();(out/'results').mkdir()
        write_text(out/'code'/'run','#!/usr/bin/env bash\nset -euo pipefail\ncd /code\nexec '+shlex.join(argv)+'\n')
        (out/'code'/'run').chmod(0o755)
        write_json(out/'metadata.json',{'title':'CVRS computational artifact export','description':'Review asset permissions and configure the target execution environment before upload',
                                      'source_capsule_digest':file_digest(root/'integrity.json') if (root/'integrity.json').exists() else None})
        for name in ('experiment.json','required-assets.json','evaluation.json'):
            if (root/name).is_file():shutil.copyfile(root/name,out/'code'/name)
        write_json(out/'environment-request.json',environment or {'status':'OWNER_CONFIGURE'})
        write_text(out/'README.md','# Code Ocean handoff\n\nThis is an upload preparation tree, not a submitted or verified Code Ocean capsule.\n'
            'Attach authorized datasets under `/data`, code under `/code`, write outputs under `/results`, and configure the environment in Code Ocean.\n'
            'No restricted model/data bytes were copied automatically. Review the native command and install CVRS with your code.\n')
    return {'status':'EXPORTED_NOT_SUBMITTED','destination':str(destination)}

def export_benchmark(spec,destination):
    with output_tree(destination) as out:
        write_json(out/'benchmark.json',spec)
        write_json(out/'datasets.lock',{'datasets':spec.get('datasets',[]),'bundled_data':False})
        write_json(out/'metrics.json',spec.get('evaluation',{}))
        write_text(out/'README.md','# Benchmark pack\n\nVersioned definitions and references only. No hosted leaderboard or restricted assets.\n')
        write_text(out/'LICENSES.md','# Artifact licensing\n\nInspect each external dataset and checkpoint separately. Unknown rights block redistribution.\n')
    return {'status':'EXPORTED','destination':str(destination)}


def export_reproduction(run,destination):
    """Export exact expected output and an executable, asset-gated rerun project."""
    from cvsubstrate.provenance.bundle import verify_bundle
    from cvsubstrate.provenance.io import digest
    root=Path(run).resolve()
    if (root/'artifacts.json').is_file():
        v=verify_bundle(root)
        if v['status']!='VERIFIED' or v.get('run_state')!='SUCCEEDED':raise ValueError('reproduction source must be a verified successful run')
    elif (root/'integrity.json').is_file():
        if verify_directory(root)['status']!='VERIFIED':raise ValueError('source integrity failed')
    else:raise ValueError('source has no verifiable evidence manifest')
    with output_tree(destination) as out:
        for name in ('experiment.json','environment.json','dataset_manifest.json','metrics.json','artifacts.json','integrity.json','adapter.json'):
            if (root/name).is_file():
                target=out/'source-metadata'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(root/name,target)
        from cvsubstrate.adoption.methodology import reviewer_report
        write_json(out/'review.json',reviewer_report(root))
        required=[];spec=read_json(root/'experiment.json') if (root/'experiment.json').is_file() else None
        if spec and (root/'dataset_manifest.json').is_file():
            dataset=read_json(root/'dataset_manifest.json')
            if digest(dataset)!=spec['dataset_sha256']:raise ValueError('captured dataset identity differs from experiment')
            (out/'inputs').mkdir()
            write_json(out/'inputs/dataset.json',dataset);spec['dataset']='inputs/dataset.json'
            required.append({'kind':'dataset_manifest','path':'inputs/dataset.json','sha256':file_digest(out/'inputs/dataset.json'),'embedded':True})
            for sample in dataset['samples']:
                required.append({'kind':'image','path':'inputs/'+sample['image'],'sha256':sample['sha256'],'embedded':False,'sample_id':sample['id']})
            if spec.get('checkpoint'):
                reference=spec['checkpoint'];reference['path']='inputs/checkpoint.bin'
                required.append({'kind':'checkpoint','path':reference['path'],'sha256':reference['sha256'],'embedded':False,'license':reference.get('license','unknown')})
            write_json(out/'experiment.json',spec)
            write_json(out/'expected-output.json',{'metrics':read_json(root/'metrics.json') if (root/'metrics.json').is_file() else None,
               'origin_predictions_sha256':file_digest(root/'predictions.jsonl') if (root/'predictions.jsonl').is_file() else None,
               'meaning':'Reference observation, not an enforced scientific tolerance or a promised exact rerun'})
            write_text(out/'reproduce.py',
                '"""Run only after supplying authorized matching assets and a native environment."""\n'
                'from pathlib import Path\nimport argparse,json,hashlib,sys\n'
                'p=argparse.ArgumentParser();p.add_argument("--out",required=True);p.add_argument("--worker-python");a=p.parse_args()\n'
                'root=Path(__file__).resolve().parent\n'
                'requirements=json.loads((root/"required-assets.json").read_text())["assets"]\n'
                'missing=[]\n'
                'for ref in requirements:\n'
                '    path=(root/ref["path"]).resolve()\n'
                '    if not path.is_relative_to(root) or not path.is_file():missing.append(ref["path"]);continue\n'
                '    with path.open("rb") as f: actual=hashlib.file_digest(f,"sha256").hexdigest()\n'
                '    if actual!=ref["sha256"]:missing.append(ref["path"]+" (hash mismatch)")\n'
                'if missing:raise SystemExit("Required matching assets: "+", ".join(missing))\n'
                'from cvsubstrate.adoption.api import Experiment\n'
                'result=Experiment(root/"experiment.json").run(Path(a.out),worker_python=a.worker_python)\n'
                'print(json.dumps({"run":str(result.path),"verification":result.verify()},indent=2))\n')
        else:
            required.append({'kind':'native_paper_recipe','embedded':False,'status':'REQUIRES_EXPLICIT_NATIVE_RECIPE'})
        write_json(out/'required-assets.json',{'assets':required,'automatic_downloads':False,'source_run':root.name})
        write_text(out/'REPRODUCE.md','# Reproduce this run\n\n'
            'This pack includes configuration, expected observations and exact asset identities. Images, pretrained weights and third-party environments are not redistributed.\n\n'
            '1. Inspect `required-assets.json`, license terms and `review.json`.\n'
            '2. Supply the matching authorized files at the listed paths.\n'
            '3. Configure the native interpreter described by source metadata. Installed-package inventory is an observation, not automatically a minimal environment lock.\n'
            '4. For a canonical run execute `python reproduce.py --out NEW_OUTPUT --worker-python /path/to/native/python`.\n'
            '5. Record a new attempt; the original result is never overwritten.\n\n'
            'The rerun launcher checks required bytes before starting. Original metrics are observations; scientific tolerances and independence need explicit review.\n')
    return {'status':'EXPORTED_ASSET_GATED_REPRODUCTION','destination':str(destination),'required_assets':len(required),'native_executed':False}
