"""Built-in, explicitly registered local actions. No arbitrary shell execution."""
from pathlib import Path
import shutil
from cvsubstrate.provenance.io import read_json,write_json,file_digest

def install_actions():
    from cvsubstrate.experiments.dag import ACTIONS,register_action
    if 'json.validate' in ACTIONS:return
    def validate(inputs,params,out):
        from cvsubstrate.schemas.registry import validate_artifact
        return validate_artifact(read_json(inputs['artifact']),params['schema'])
    def copy(inputs,params,out):
        dst=out/'artifact';shutil.copyfile(inputs['artifact'],dst);return {'artifact':'artifact','sha256':file_digest(dst)}
    def emit(inputs,params,out):write_json(out/'value.json',params['value']);return {'artifact':'value.json'}
    def run(inputs,params,out):
        from cvsubstrate.execution.runner import run_experiment
        path=run_experiment(inputs['experiment'],out/'runs',params.get('worker_python'),params.get('timeout',180.0))
        outputs={name:(path/name).relative_to(out).as_posix() for name in ['experiment.json','predictions.jsonl','metrics.json'] if (path/name).is_file()}
        if (path/'worker/checkpoint.pt').is_file():outputs['checkpoint']=(path/'worker/checkpoint.pt').relative_to(out).as_posix()
        return {'run':path.relative_to(out).as_posix(),'outputs':outputs}
    def evaluate(inputs,params,out):
        from cvsubstrate.evaluation.service import evaluate_files
        result=evaluate_files(inputs['dataset'],params['split'],inputs['predictions'],inputs['protocol'],worker_python=params.get('worker_python'))
        write_json(out/'metrics.json',result);return {'metrics':'metrics.json'}
    def campaign(inputs,params,out):
        from cvsubstrate.campaigns.engine import execute_campaign
        return execute_campaign(inputs['campaign'],out/'campaign')
    def report(inputs,params,out):
        from cvsubstrate.reporting.formal import create_report
        return create_report(params['kind'],[read_json(p) for p in inputs.values()],out/'report',title=params.get('title'))
    def checkpoint(inputs,params,out):
        from cvsubstrate.checkpoints import convert_checkpoint
        spec=read_json(inputs['spec']);return convert_checkpoint(spec,out/'converted',worker_python=params.get('worker_python'))
    def deploy(inputs,params,out):
        from cvsubstrate.deployment.service import execute_deployment
        return execute_deployment(read_json(inputs['spec']),out/'deployment',worker_python=params.get('worker_python'))
    def extract(inputs,params,out):
        from cvsubstrate.backbones.service import extract_features
        return extract_features(read_json(inputs['spec']),out/'features',worker_python=params.get('worker_python'))
    def bind_checkpoint(inputs,params,out):
        from cvsubstrate.contracts.models import ExperimentSpec
        value=read_json(inputs['experiment'])
        base=inputs['experiment'].parent
        value['dataset']=str((base/value['dataset']).resolve())
        value['checkpoint']={'path':str(inputs['checkpoint'].resolve()),'sha256':file_digest(inputs['checkpoint']),'trust':params.get('trust','owned_weights_only'),'license':params.get('license','unknown')}
        validated=ExperimentSpec.model_validate(value)
        write_json(out/'experiment.json',validated)
        return {'outputs':{'experiment':'experiment.json'}}
    register_action('experiment.bind-checkpoint',bind_checkpoint,retry_safe=True)
    register_action('json.validate',validate,cacheable=True,retry_safe=True)
    register_action('artifact.copy',copy,cacheable=True,retry_safe=True)
    register_action('json.emit',emit,cacheable=True,retry_safe=True)
    register_action('experiment.run',run)
    register_action('evaluate',evaluate)  # protocol may govern test access; not cacheable
    register_action('campaign.run',campaign)
    register_action('report.create',report,cacheable=True,retry_safe=True)
    register_action('checkpoint.convert',checkpoint)
    register_action('deployment.run',deploy)
    register_action('backbone.extract',extract)
    def vision(inputs,params,out):
        from cvsubstrate.vision.service import vision_job
        return vision_job(inputs['spec'],out/'vision',worker_python=params.get('worker_python'),timeout=params.get('timeout',600))
    def stream(inputs,params,out):
        from cvsubstrate.streaming.service import stream_job
        return stream_job(inputs['spec'],out/'stream',worker_python=params.get('worker_python'),timeout=params.get('timeout',600))
    def quantize(inputs,params,out):
        from cvsubstrate.deployment.quantization import quantize
        return quantize(inputs['spec'],out/'quantized',worker_python=params.get('worker_python'),timeout=params.get('timeout',600))
    def reevaluate(inputs,params,out):
        from cvsubstrate.research.reevaluate import reevaluate
        return reevaluate(inputs['dataset'],params['split'],inputs['predictions'],inputs['protocol'],out/'analysis',worker_python=params.get('worker_python'),origin=params.get('origin'))
    register_action('vision.run',vision)
    register_action('stream.run',stream)
    register_action('quantization.run',quantize)
    register_action('research.reevaluate',reevaluate)


    def closure_stream(inputs,params,out):
        from cvsubstrate.execution.services import invoke_service
        value=invoke_service('task_stream',{'spec':read_json(inputs['spec']),'output_dir':str(out/'stream')},worker_python=params.get('worker_python'),timeout=params.get('timeout',600))
        return {'result':value,'outputs':{'state':'stream/state.json','predictions':'stream/'+value['canonical_predictions']}}
    def closure_eval(inputs,params,out):
        from cvsubstrate.research.evaluators import reevaluate_task
        spec=read_json(inputs['spec']) if 'spec' in inputs else dict(params['spec'])
        for name in ['dataset','predictions','protocol']:
            if name in inputs:spec[name]=str(inputs[name])
        value=reevaluate_task(spec,out/'evaluation',worker_python=params.get('worker_python'))
        return {'result':value,'outputs':{'evaluation':'evaluation/evaluation.json'}}
    def closure_native(inputs,params,out):
        from cvsubstrate.campaigns.native import run_native_campaign
        value=run_native_campaign(read_json(inputs['spec']),out/'campaign',worker_pythons=params.get('worker_pythons',{}),timeout=params.get('timeout',3600))
        return {'result':value,'outputs':{'state':'campaign/campaign-state.json'}}
    def registry_capture(inputs,params,out):
        from cvsubstrate.research.federated import FederatedRegistry
        from cvsubstrate.research.capture_v2 import capture_comparison
        spec=read_json(inputs['spec'])
        with FederatedRegistry(out/'registry') as reg:
            cid=reg.add('claim',spec.pop('claim'))
            value=capture_comparison(reg,cid,**spec)
            reg.exchange(out/'exchange');reg.export_site(out/'site')
        return {'result':value,'outputs':{'exchange':'exchange/exchange.json','site':'site/index.html'}}
    register_action('closure.stream',closure_stream)
    register_action('closure.evaluate',closure_eval)
    register_action('closure.native-campaign',closure_native)
    register_action('closure.capture-comparison',registry_capture)
