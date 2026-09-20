"""Finite adapter recipes. Availability is not execution certification."""
from pathlib import Path
from cvsubstrate.provenance.io import write_json

RECIPES={
 'mmdet2':{'family':'mmdetection','task':'hbb_detection','operations':['predict','train_native'],'environment':'isolated legacy Python/MMCV','telemetry':'MM runner model.train_step + optimizer post-step hook','training_semantics':'native; measurement required before source-exposure equivalence'},
 'mmdet3':{'family':'mmdetection','task':'hbb_detection','operations':['predict','train_native'],'environment':'isolated MMEngine/MMCV','telemetry':'MMEngine model.train_step + optimizer post-step hook','training_semantics':'native; measurement required before source-exposure equivalence'},
 'ultralytics':{'family':'ultralytics','task':'hbb_detection','operations':['predict','train_native','export'],'telemetry':'metadata captured at preprocess; consumed batches observed at model forward + optimizer posthook','training_semantics':'explicitly disable untraced mosaic/mixup/copy-paste/cutmix for exact source attribution'},
 'rfdetr':{'family':'rfdetr','task':'hbb_detection','operations':['predict','train_native','export'],'telemetry':'train_one_epoch model microbatch forward + optimizer posthook','training_semantics':'native epoch semantics; feature-checked method signature'},
 'grounding_dino_hf':{'family':'transformers','task':'grounded_detection','operations':['predict'],'backend':'hf_grounding_dino','asset_requirements':['local processor/config/tokenizer','local safetensors weights'],'prompt':'exact UTF-8 text, no implicit class synonym mapping'},
 'sam_hf':{'family':'transformers','task':'instance_masks','operations':['predict'],'backend':'sam_hf','asset_requirements':['local processor/config','local safetensors weights'],'prompt':'original-image points or boxes'},
 'sam2':{'family':'sam2','task':'instance_masks','operations':['predict'],'backend':'sam2','asset_requirements':['local trusted Hydra config','local trusted checkpoint'],'prompt':'original-image points or boxes'},
 'yolo_world':{'family':'ultralytics','task':'grounded_detection','operations':['predict'],'backend':'yolo_world','asset_requirements':['local YOLO-World weights','local text-encoder cache'],'prompt':'exact ordered phrase list; no remote fallback'},
 'ultralytics_seg':{'family':'ultralytics','task':'instance_masks','operations':['predict'],'backend':'ultralytics_seg','asset_requirements':['local segmenter checkpoint'],'prompt':'none'},
 'dinov2':{'family':'DINO local source','task':'feature_maps','operations':['extract','detector_backbone'],'asset_requirements':['trusted local repo and source-tree hash','checkpoint hash'],'geometry':'explicit feature indices/channels/patch stride; no invented pyramid'},
 'dinov3':{'family':'DINO local source','task':'feature_maps','operations':['extract','detector_backbone'],'asset_requirements':['trusted local repo and source-tree hash','checkpoint hash'],'geometry':'requires get_intermediate_layers feature recipe and actual shape receipts'},
 'timm':{'family':'timm','task':'feature_maps','operations':['extract','detector_backbone'],'asset_requirements':['local matching features_only state dict'],'geometry':'explicit out_indices and declared channel dimensions'},
 'hf_backbone':{'family':'transformers','task':'feature_maps','operations':['extract','detector_backbone'],'asset_requirements':['local model folder and file hashes'],'geometry':'AutoBackbone recipe with explicit out_indices'}
}

def recipes():return [{'name':k,**v,'native_execution_in_this_release':'NOT_CERTIFIED'} for k,v in RECIPES.items()]
def recipe(name):
    if name not in RECIPES:raise ValueError('unknown adapter recipe')
    return {'name':name,**RECIPES[name],'native_execution_in_this_release':'NOT_CERTIFIED'}

def scaffold_vision_adapter(destination):
    """External plugin delegates to actual optional native vision APIs, not mock outputs."""
    root=Path(destination)
    if root.exists():raise ValueError('new adapter project required')
    root.mkdir(parents=True);package=root/'example_cvrs_adapter';package.mkdir()
    (package/'__init__.py').write_text('from .adapter import LocalVisionAdapter\n')
    (package/'adapter.py').write_text("""from cvsubstrate.contracts.frontier import VisionJob
from cvsubstrate.vision.service import vision_job
class LocalVisionAdapter:
    def __init__(self, config=None): self.config=config or {}
    def capabilities(self):
        return {"protocol_version":"1.0", "tasks":["grounded_detection","instance_masks"], "operations":["validate","predict"], "input_formats":["VisionJob/1"], "output_formats":["GroundedPrediction/1","MaskPrediction/1"], "precisions":["float32"], "device":"worker configured", "network_downloads":False}
    def validate(self, request):
        job=VisionJob.model_validate(request["job"])
        return {"valid":True,"backend":job.backend,"execution_verified":False}
    def predict(self, request):
        from pathlib import Path
        output=Path(request["artifact_directory"])/"native-vision"
        return vision_job(request["job"],output,worker_python=request.get("worker_python",self.config.get("worker_python")),timeout=request.get("timeout",self.config.get("timeout",600)))
    def close(self): pass
""")
    (root/'pyproject.toml').write_text('[build-system]\nrequires=["setuptools>=77"]\nbuild-backend="setuptools.build_meta"\n[project]\nname="example-cvrs-native-vision-adapter"\nversion="0.0.1"\ndependencies=["cv-research-substrate>=0.5.0a1"]\n')
    (root/'README.md').write_text('# External adapter example\n\nThis is native-delegating code, not a mock model. Supply local hashed assets and the appropriate isolated worker. No native execution or independent authorship is claimed by generating this template. Inspect the installed plugin SDK before publishing.\n')
    from cvsubstrate.contracts.groundwork import PluginDescriptor
    write_json(root/'plugin.json',PluginDescriptor(id='example_native_vision',kind='model',target='example_cvrs_adapter.adapter:LocalVisionAdapter',tasks=['grounded_detection','instance_masks'],operations=['validate','predict'],formats=['VisionJob/1','GroundedPrediction/1','MaskPrediction/1'],required_packages=['cv-research-substrate'],trust_code=False))
    write_json(root/'conformance-request.json',{'operation':'validate','required_behavior':'reject an empty or malformed VisionJob','fixture_purpose':'software_conformance'})
    return {'status':'CREATED','path':str(root),'native_execution_verified':False}
