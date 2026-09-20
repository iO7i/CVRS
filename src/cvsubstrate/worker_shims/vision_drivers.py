"""Explicit native model loading drivers. All assets must be local and trusted."""
from pathlib import Path
from typing import Any
class GroundingDINODriver:
    task='grounded_detection';prompts: set[str]={'text'}
    def load(self,job,root):
        from transformers import AutoProcessor,AutoModelForZeroShotObjectDetection
        return AutoProcessor.from_pretrained(str(root),local_files_only=True,trust_remote_code=False),AutoModelForZeroShotObjectDetection.from_pretrained(str(root),local_files_only=True,trust_remote_code=False,use_safetensors=True).to(job.device).eval()
class HFSAMDriver:
    task='instance_masks';prompts: set[str]={'points','box','mask'}
    def load(self,job,root):
        from transformers import SamModel,SamProcessor
        return SamProcessor.from_pretrained(str(root),local_files_only=True),SamModel.from_pretrained(str(root),local_files_only=True,use_safetensors=True).to(job.device).eval()
class SAM2Driver:
    task='instance_masks';prompts: set[str]={'points','box','mask'}
    def load(self,job,root):
        if not job.trust_local_code:raise ValueError('SAM2 config needs explicit local code trust')
        from runtime_common import safe_path
        from sam2.build_sam import build_sam2
        from sam2.sam2_image_predictor import SAM2ImagePredictor
        from hydra import initialize_config_dir
        from hydra.core.global_hydra import GlobalHydra
        config=safe_path(root,job.config['config_file']);weights=safe_path(root,job.config['weights_file'])
        GlobalHydra.instance().clear()
        with initialize_config_dir(config_dir=str(config.parent),version_base='1.2'):
            return None,SAM2ImagePredictor(build_sam2(config.name,str(weights),device=job.device))
class YOLOWorldDriver:
    task='grounded_detection';prompts: set[str]={'text'}
    def load(self,job,root):
        if not job.trust_local_code:raise ValueError('native checkpoint needs explicit trust')
        from runtime_common import safe_path
        from ultralytics import YOLOWorld
        return None,YOLOWorld(str(safe_path(root,job.config['weights_file'])))
class UltralyticsMaskDriver:
    task='instance_masks';prompts: set[str]=set()
    def load(self,job,root):
        if not job.trust_local_code:raise ValueError('native checkpoint needs explicit trust')
        from runtime_common import safe_path
        from ultralytics import YOLO
        return None,YOLO(str(safe_path(root,job.config['weights_file'])),task='segment')
class NativeMaskDriver:
    task='instance_masks';prompts: set[str]=set()
    def load(self,job,root):
        import torch
        from runtime_common import safe_path
        from cvsubstrate.vision.native_mask import build_mask_detector
        mapping={int(k):int(v) for k,v in job.config['category_map'].items()}
        if sorted(mapping)!=list(range(1,len(mapping)+1)):raise ValueError('foreground native labels must be 1..N')
        model=build_mask_detector(len(mapping)+1)
        weights=torch.load(safe_path(root,job.config['weights_file']),map_location='cpu',weights_only=True)
        model.load_state_dict(weights,strict=True);return None,model.to(job.device).eval()
DRIVERS={'hf_grounding_dino':GroundingDINODriver,'sam_hf':HFSAMDriver,'sam2':SAM2Driver,'yolo_world':YOLOWorldDriver,'ultralytics_seg':UltralyticsMaskDriver,'torchvision_mask':NativeMaskDriver}
def get_driver(backend):
    if backend not in DRIVERS:raise ValueError('unknown explicit vision driver')
    return DRIVERS[backend]()

def mask_logits(prompt,backend,job,model,processor):
    import numpy as np,torch
    import torch.nn.functional as F
    from runtime_common import check_file,read
    from cvsubstrate.contracts.frontier import MaskRLE
    from cvsubstrate.vision.masks import decode_mask
    if not prompt.source_artifact_sha256:raise ValueError('mask-prompt artifact SHA is mandatory')
    path=check_file(prompt.mask_reference,prompt.source_artifact_sha256)
    mask=MaskRLE.model_validate(read(path));a=torch.from_numpy(decode_mask(mask)).float()[None,None]
    magnitude=float(job.config.get('binary_mask_logit',10.0))
    if not 0<magnitude<=100:raise ValueError('binary mask logit magnitude must be (0,100]')
    if backend=='sam_hf':
        side=int(model.config.vision_config.image_size);size=processor.image_processor.size.get('longest_edge',side)
        scale=size/max(mask.width,mask.height);h=int(mask.height*scale+.5);w=int(mask.width*scale+.5)
        a=F.interpolate(a,size=(h,w),mode='nearest');a=F.pad(a,(0,side-w,0,side-h));low=side//4
    else:
        side=int(getattr(model,'_transforms').resolution);low=side//4
    a=F.interpolate(a,size=(low,low),mode='nearest');a=(a*2-1)*magnitude
    return a.to(job.device) if backend=='sam_hf' else a[0].numpy()


def grouped_prompts(prompts,groups):
    """Lossless grouping of point/box/mask corrections for one native object query."""
    if not groups:return [(p.id,[p]) for p in prompts]
    lookup={p.id:p for p in prompts};seen: set[str]=set();result: list[tuple[str, list[Any]]]=[];targets: set[str]=set()
    for group in groups:
        ids=group['prompt_ids'];target=group['target_id']
        relevant=[p for p in ids if p in lookup]
        if not relevant:continue
        if len(relevant)!=len(ids) or set(ids)&seen or len(set(ids))!=len(ids):raise ValueError('prompt grouping crosses images or duplicates IDs')
        if target in targets:raise ValueError('duplicate target group')
        targets.add(target);seen.update(ids);ps=[lookup[i] for i in ids]
        if any(p.kind not in {'points','box','mask'} for p in ps):raise ValueError('SAM group has unsupported prompt')
        if sum(p.kind=='box' for p in ps)>1 or sum(p.kind=='mask' for p in ps)>1:raise ValueError('replace prior box/mask before supplying a correction; points may append')
        result.append((ps[-1].id,ps))
    if seen!=set(lookup):raise ValueError('not every prompt belongs to a target group')
    return result
