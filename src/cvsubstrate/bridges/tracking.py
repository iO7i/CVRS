"""Prepare minimal tracking metadata from a verified run; no implicit data transfer."""
from pathlib import Path
from cvsubstrate.provenance.bundle import verify_bundle
from cvsubstrate.provenance.io import read_json,write_json,file_digest,digest
from cvsubstrate.adoption.common import output_tree
from cvsubstrate.security import sanitize

def prepare_tracking(run,destination,*,bridge='wandb',project='cvrs'):
    if bridge not in {'wandb','mlflow'}:raise ValueError('tracking preparation supports W&B and MLflow')
    run=Path(run).resolve();verification=verify_bundle(run)
    if verification['status']!='VERIFIED':raise ValueError('run integrity failed')
    spec=read_json(run/'experiment.json')
    from cvsubstrate.research.metrics import scalar_observations
    metrics=scalar_observations(read_json(run/'metrics.json'))
    metadata={'metrics':metrics,'parameters':{'adapter':spec.get('adapter',{}).get('name'),'experiment_name':spec.get('name')},
        'identities':{'cvrs_dataset_sha256':spec.get('dataset_sha256'),'cvrs_experiment_file_sha256':file_digest(run/'experiment.json'),
                      'cvrs_predictions_sha256':file_digest(run/'predictions.jsonl'),'cvrs_evidence_sha256':file_digest(run/'artifacts.json')}}
    destination=Path(destination).resolve()
    with output_tree(destination,seal=False) as out:
        write_json(out/'run-metadata.json',sanitize(metadata))
        write_json(out/'bridge-job.json',{'bridge':bridge,'operation':'export','payload':{'run_metadata':str(destination/'run-metadata.json'),
           'project':project,'experiment':project,'approved_files':[],'acknowledge_external_transfer':False},
           'output_dir':str(destination.parent/(destination.name+'-export')),'trust_code':False,'allow_network':False})
    return {'status':'PREPARED_OFFLINE','destination':str(destination),'metrics':len(metrics),'data_images_or_weights_included':False}
