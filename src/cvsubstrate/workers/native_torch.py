"""A genuine torchvision Faster R-CNN with a tiny backbone for CPU conformance.

Random initialization; no automatic weights/downloads. This is a software-test
model, not a scientific baseline or reproduced pretrained architecture.
"""
from __future__ import annotations
from collections import Counter, OrderedDict
import importlib.util
from pathlib import Path
import random
from cvsubstrate.contracts.models import AdapterCapabilities, DetectionPrediction, TrainingTrace, TrainingSpec
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.bundle import environment_snapshot
from cvsubstrate.provenance.io import digest, file_digest, safe_join, write_json, write_jsonl
from cvsubstrate.protocols.planner import plan
from cvsubstrate.workers.common import entrypoint, validated_inputs
MODEL_SPEC = {'name': 'tiny_fasterrcnn_conformance_v1', 'weights': 'random_initialization_no_pretrained_weights', 'backbone': 'Conv3x3(3,8,stride2)-ReLU-Conv3x3(8,16,stride2)-ReLU', 'anchors': {'sizes': [8, 16, 32], 'ratios': [0.5, 1.0, 2.0]}, 'roi_pool': {'size': 3, 'sampling_ratio': 2}, 'box_head_features': 32, 'image_min_size': 64, 'image_max_size': 96, 'image_mean': [0.0, 0.0, 0.0], 'image_std': [1.0, 1.0, 1.0], 'rpn_pre_nms': 64, 'rpn_post_nms': 32, 'rpn_batch_size': 32, 'box_batch_size': 32, 'box_detections_per_image': 30, 'box_score_threshold': 0.0, 'box_nms_threshold': 0.5, 'device': 'cpu', 'dtype': 'float32', 'threads': 1, 'augmentation': 'none', 'output': 'torchvision restores boxes to original image coordinates'}

def capabilities():
    installed = all((importlib.util.find_spec(m) is not None for m in ['torch', 'torchvision', 'PIL', 'numpy']))
    return AdapterCapabilities(adapter='native_torch', tasks=['hbb_detection'], operations=['capabilities', 'validate', 'predict', 'train'], installed=installed, limitations=['CPU fp32 conformance detector only', 'No pretrained quality claim', 'No image augmentation', 'No crowd-aware training; such annotations cause a structured error', 'No DDP, GPU, export, or arbitrary backbones'], environment=environment_snapshot()).model_dump(mode='json')

def setup(seed: int):
    import numpy as np
    import torch
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    random.seed(seed)
    np.random.seed(seed % 2 ** 32)
    torch.manual_seed(seed)

def model_factory(num_classes: int):
    import torch
    from torch import nn
    from torchvision.models.detection import FasterRCNN
    from torchvision.models.detection.anchor_utils import AnchorGenerator
    from torchvision.models.detection.faster_rcnn import TwoMLPHead, FastRCNNPredictor
    from torchvision.ops import MultiScaleRoIAlign

    class TinyBackbone(nn.Module):

        def __init__(self):
            super().__init__()
            self.out_channels = 16
            self.layers = nn.Sequential(nn.Conv2d(3, 8, 3, stride=2, padding=1), nn.ReLU(), nn.Conv2d(8, 16, 3, stride=2, padding=1), nn.ReLU())

        def forward(self, x):
            return OrderedDict([('0', self.layers(x))])
    return FasterRCNN(TinyBackbone(), num_classes=None, rpn_anchor_generator=AnchorGenerator(sizes=((8, 16, 32),), aspect_ratios=((0.5, 1.0, 2.0),)), box_roi_pool=MultiScaleRoIAlign(featmap_names=['0'], output_size=3, sampling_ratio=2), box_head=TwoMLPHead(16 * 3 * 3, 32), box_predictor=FastRCNNPredictor(32, num_classes), min_size=64, max_size=96, image_mean=[0.0, 0.0, 0.0], image_std=[1.0, 1.0, 1.0], rpn_pre_nms_top_n_train=64, rpn_pre_nms_top_n_test=64, rpn_post_nms_top_n_train=32, rpn_post_nms_top_n_test=32, rpn_batch_size_per_image=32, box_batch_size_per_image=32, box_detections_per_img=30, box_score_thresh=0.0, box_nms_thresh=0.5)

def selected_model_spec(config):
    if config.get('model')=='foundation_fasterrcnn_v1':
        return {'name':'foundation_fasterrcnn_v1','backbone':config['backbone'],'head':'torchvision.FasterRCNN/FPN','certification':'NOT_ESTABLISHED'}
    return MODEL_SPEC

def build_selected_model(config,num_classes):
    if config.get('model')=='foundation_fasterrcnn_v1':
        from cvsubstrate.backbones.detector import build_detector
        model=build_detector(config['backbone'],num_classes)
    else:model=model_factory(num_classes)
    model.cvrs_model_spec=selected_model_spec(config)
    return model

def validate_config(config):
    if set(config)-{'model','stage_policy','backbone'}:
        raise CVRSError('MODEL_CONFIG_UNSUPPORTED','unknown native model settings')
    if config.get('model','tiny_fasterrcnn_conformance_v1') not in {'tiny_fasterrcnn_conformance_v1','foundation_fasterrcnn_v1'}:
        raise CVRSError('MODEL_CONFIG_UNSUPPORTED','unknown native model')
    if config.get('model')=='foundation_fasterrcnn_v1' and not config.get('backbone'):
        raise CVRSError('MODEL_CONFIG_UNSUPPORTED','foundation detector needs explicit backbone descriptor')
    if config.get('backbone') and config.get('model')!='foundation_fasterrcnn_v1':
        raise CVRSError('MODEL_CONFIG_UNSUPPORTED','backbone requires foundation_fasterrcnn_v1')
    stage=config.get('stage_policy',{})
    if set(stage)-{'real_weight','transition','stage_id'}:raise CVRSError('MODEL_CONFIG_UNSUPPORTED','unknown stage setting')
    if stage.get('real_weight',1.0)<=0:raise CVRSError('MODEL_CONFIG_UNSUPPORTED','real loss weight must be positive')
    if stage.get('transition','weights_only_reset_optimizer') not in {'weights_only_reset_optimizer','resume_full_state'}:raise CVRSError('MODEL_CONFIG_UNSUPPORTED','unknown checkpoint transition')

def batch(m, root, ids, category_map):
    import numpy as np
    import torch
    from PIL import Image
    by_id = {s.id: s for s in m.samples}
    images = []
    targets = []
    for sid in ids:
        s = by_id[sid]
        with Image.open(safe_join(root, s.image)) as im:
            if im.getexif().get(274, 1) != 1:
                raise CVRSError('EXIF_ORIENTATION', 'EXIF-oriented images must be normalized with corresponding boxes before ingestion')
            array = np.array(im.convert('RGB'), copy=True)
        images.append(torch.from_numpy(array).permute(2, 0, 1).float() / 255.0)
        if any((b.iscrowd or b.ignore for b in s.boxes)):
            raise CVRSError('CROWD_TRAINING_UNSUPPORTED', 'native conformance trainer does not implement crowd-ignore training')
        targets.append({'boxes': torch.tensor([b.xyxy for b in s.boxes], dtype=torch.float32).reshape(-1, 4), 'labels': torch.tensor([category_map[b.category_id] for b in s.boxes], dtype=torch.int64)})
    return (images, targets)

def inference_images(m, root, ids):
    import numpy as np
    import torch
    from PIL import Image
    by_id = {s.id: s for s in m.samples}
    out = []
    for sid in ids:
        with Image.open(safe_join(root, by_id[sid].image)) as im:
            if im.getexif().get(274, 1) != 1:
                raise CVRSError('EXIF_ORIENTATION', 'normalize image/boxes before inference')
            out.append(torch.from_numpy(np.array(im.convert('RGB'), copy=True)).permute(2, 0, 1).float() / 255.0)
    return out

def optimizer_for(model, lr):
    import torch
    optimizer = torch.optim.SGD(model.parameters(), lr=lr, momentum=0.9)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=2, gamma=0.9)
    return (optimizer, scheduler)

def train_step(model, optimizer, scheduler, m, root, step, category_map, weight, real_weight=1.0):
    import torch
    model.train()
    optimizer.zero_grad(set_to_none=True)
    losses = {}
    groups={'real':step.get('real_primary',step['real']), 'synthetic':step['synthetic'], 'real_replay':step.get('real_replay',[])}
    for source in ['real', 'synthetic', 'real_replay']:
        if not groups[source]:
            continue
        images, targets = batch(m, root, groups[source], category_map)
        # Independent source RNG prevents the extra synthetic forward from
        # consuming the real source's proposal-sampling RNG stream.
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(step[source + '_forward_seed'])
            terms = model(images, targets)
        loss = sum(terms.values())
        if not torch.isfinite(loss):
            raise CVRSError('NONFINITE_LOSS', 'training produced a nonfinite loss')
        losses[source] = loss
    if not losses:
        raise CVRSError('EMPTY_STEP', 'no samples in optimizer step')
    total = sum((value * (weight if key in {'synthetic', 'real_replay'} else real_weight) for key, value in losses.items()))
    total.backward()
    if not all((p.grad is None or torch.isfinite(p.grad).all() for p in model.parameters())):
        raise CVRSError('NONFINITE_GRADIENT', 'training produced a nonfinite gradient')
    optimizer.step()
    scheduler.step()
    return ({source: float(value.detach()) for source, value in losses.items()}, float(total.detach()))

def tensor_state_digest(state):
    import hashlib
    h = hashlib.sha256()
    for name, t in sorted(state.items()):
        h.update(name.encode())
        h.update(str(t.dtype).encode())
        h.update(str(tuple(t.shape)).encode())
        h.update(t.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()

def save_checkpoint(path, model, optimizer, scheduler, metadata, progress):
    import os
    import torch
    # Tensor/primitives-only checkpoint; load with weights_only=True below.
    value = {'schema_version': '1.0', 'model': model.state_dict(), 'optimizer': optimizer.state_dict() if optimizer else None, 'scheduler': scheduler.state_dict() if scheduler else None, 'torch_rng': torch.get_rng_state(), 'metadata': metadata, 'progress': progress}
    temporary = path.with_suffix('.writing')
    torch.save(value, temporary)
    os.replace(temporary, path)

def load_owned_checkpoint(path, expected_sha=None):
    import torch
    if expected_sha and file_digest(path) != expected_sha:
        raise CVRSError('CHECKPOINT_HASH', 'checkpoint bytes do not match reference')
    value = torch.load(path, map_location='cpu', weights_only=True)
    if value.get('schema_version') != '1.0':
        raise CVRSError('CHECKPOINT_SCHEMA', 'unsupported owned checkpoint schema')
    return value

def predict_rows(model, m, root, split, category_map):
    import torch
    reverse = {v: k for k, v in category_map.items()}
    by_id = {s.id: s for s in m.samples}
    rows = []
    model.eval()
    with torch.no_grad():
        for sid in m.splits[split].sample_ids:
            result = model(inference_images(m, root, [sid]))[0]
            sample = by_id[sid]
            rows.append(DetectionPrediction(sample_id=sid, width=sample.width, height=sample.height, boxes=result['boxes'].tolist(), scores=result['scores'].tolist(), category_ids=[reverse[int(i)] for i in result['labels'].tolist()], transform_provenance={'owner': 'torchvision.GeneralizedRCNNTransform', 'restored_to_original': True, 'model_spec_digest': digest(getattr(model,'cvrs_model_spec',MODEL_SPEC))}))
    return rows

def run(req):
    if req.operation == 'capabilities':
        return capabilities()
    if not capabilities()['installed']:
        raise CVRSError('NATIVE_DEPENDENCIES', 'native worker needs torch, torchvision, numpy, Pillow')
    spec, m, root, out = validated_inputs(req)
    if spec.adapter.name != 'native_torch':
        raise CVRSError('ADAPTER_MISMATCH', 'wrong worker for this experiment')
    validate_config(spec.adapter.config)
    if req.operation == 'validate':
        return {'status': 'VALID', 'model_spec': selected_model_spec(spec), 'environment': environment_snapshot()}
    if req.operation == 'predict' and spec.training:
        raise CVRSError('OPERATION_MISMATCH', 'predict request may not contain a training plan')
    if req.operation == 'train' and spec.training is None:
        raise CVRSError('OPERATION_MISMATCH', 'train request requires a training plan')
    import torch
    import time
    execution_start = time.perf_counter()
    setup(spec.seed)
    category_map = {c.id: i + 1 for i, c in enumerate(m.categories)}
    model = build_selected_model(spec.adapter.config,len(category_map) + 1)
    model_spec = selected_model_spec(spec.adapter.config)
    ck = None
    if req.checkpoint:
        if req.checkpoint.get('trust') != 'owned_weights_only':
            raise CVRSError('CHECKPOINT_TRUST', 'native worker accepts only owned weights-only checkpoints')
        ck = load_owned_checkpoint(Path(req.checkpoint['path']), req.checkpoint['sha256'])
        if ck['metadata']['model_spec_digest'] != digest(model_spec) or ck['metadata']['category_map'] != {str(k): v for k, v in category_map.items()}:
            raise CVRSError('CHECKPOINT_ARCHITECTURE', 'checkpoint model/taxonomy differs')
        model.load_state_dict(ck['model'], strict=True)
    before = tensor_state_digest(model.state_dict())
    trace = []
    optimizer = scheduler = None
    protocol_plan = None
    if spec.training:
        protocol_plan = plan(spec, m)
        write_json(out / 'protocol_plan.json', protocol_plan)
        for stage_index, stage in enumerate(protocol_plan['stages']):
            optimizer, scheduler = optimizer_for(model, spec.training.learning_rate)
            if stage_index==0 and spec.adapter.config.get('stage_policy',{}).get('transition')=='resume_full_state':
                if not ck or ck.get('optimizer') is None or ck.get('scheduler') is None:
                    raise CVRSError('CHECKPOINT_STATE_MISSING','full-state transition needs optimizer/scheduler checkpoint')
                optimizer.load_state_dict(ck['optimizer']);scheduler.load_state_dict(ck['scheduler']);torch.set_rng_state(ck['torch_rng'])
            for step in stage['steps']:
                loss, total = train_step(model, optimizer, scheduler, m, root, step, category_map, spec.training.synthetic_weight, spec.adapter.config.get('stage_policy',{}).get('real_weight',1.0))
                trace.append(TrainingTrace(update=step['update'], stage=stage['name'], real_sample_ids=step['real'], synthetic_sample_ids=step['synthetic'], real_loss=loss.get('real'), synthetic_loss=loss.get('synthetic'), nominal_synthetic_weight=spec.training.synthetic_weight, weighted_total_loss=total, real_primary_sample_ids=step.get('real_primary',step['real']), real_replay_sample_ids=step.get('real_replay',[]), real_replay_loss=loss.get('real_replay')))
        write_jsonl(out / 'training_trace.jsonl', trace)
    after = tensor_state_digest(model.state_dict())
    metadata = {'model_spec': model_spec, 'model_spec_digest': digest(model_spec), 'category_map': {str(k): v for k, v in category_map.items()}, 'seed': spec.seed, 'weights_origin': 'owned_checkpoint' if req.checkpoint else 'random_initialization'}
    save_checkpoint(out / 'checkpoint.pt', model, optimizer, scheduler, metadata, {'completed_updates': len(trace)})
    rows = predict_rows(model, m, root, spec.eval_split, category_map)
    write_jsonl(out / 'predictions.jsonl', rows)
    # Real prediction parity after serialization, not a fabricated golden.
    reloaded = build_selected_model(spec.adapter.config,len(category_map) + 1)
    reloaded.load_state_dict(load_owned_checkpoint(out / 'checkpoint.pt')['model'], strict=True)
    roundtrip = predict_rows(reloaded, m, root, spec.eval_split, category_map)
    parity = all((a.model_dump(mode='json') == b.model_dump(mode='json') for a, b in zip(rows, roundtrip)))
    if not parity:
        raise CVRSError('CHECKPOINT_PARITY', 'same-environment checkpoint roundtrip predictions differ')
    real = [sid for t in trace for sid in t.real_sample_ids]
    syn = [sid for t in trace for sid in t.synthetic_sample_ids]
    measured = {'optimizer_updates': len(trace), 'real_exposures': len(real), 'synthetic_exposures': len(syn), 'real_unique': len(set(real)), 'synthetic_unique': len(set(syn)), 'real_replayed_exposures': len(real) - len(set(real)), 'synthetic_replayed_exposures': len(syn) - len(set(syn))}
    measured['additional_real_control_exposures']=sum(len(t.real_replay_sample_ids) for t in trace)
    measured['primary_real_exposures']=sum(len(t.real_primary_sample_ids) for t in trace)
    if protocol_plan:
        if any((v != protocol_plan['planned_counts'][k] for k, v in measured.items())):
            raise CVRSError('EXPOSURE_MISMATCH', 'measured training exposure disagrees with plan')
    result = {'model_spec': model_spec, 'nominal_real_loss_weight':spec.adapter.config.get('stage_policy',{}).get('real_weight',1.0), 'checkpoint_transition':spec.adapter.config.get('stage_policy',{}).get('transition','weights_only_reset_optimizer'), 'environment': environment_snapshot(), 'device': 'cpu', 'gpu_used': False, 'initial_parameter_digest': before, 'final_parameter_digest': after, 'parameters_changed': before != after, 'trainable_parameters': sum((p.numel() for p in model.parameters() if p.requires_grad)), 'checkpoint_roundtrip_predictions_exact': parity, 'checkpoint_sha256': file_digest(out / 'checkpoint.pt'), 'prediction_images': len(rows), 'predictions_total': sum((len(r.boxes) for r in rows)), 'measured_counts': measured, 'gradient_influence': 'NOT_MEASURED', 'artifacts': {'predictions': 'predictions.jsonl', 'checkpoint': 'checkpoint.pt'}, 'claims': ['CPU execution verified in this process', 'Checkpoint roundtrip verified in this process'], 'nonclaims': ['No pretrained quality reproduction', 'No scientific synthetic-data benefit', 'No GPU or cross-hardware reproducibility']}
    result['timing']={'worker_execution_wall_seconds':time.perf_counter()-execution_start,'gpu_time_seconds':None,'scope':'CPU wall time including model initialization, train/inference and checkpoint parity'}
    write_json(out / 'execution.json', result)
    return result

def resume_selftest(m, root, out: Path):
    """Scoped same-process, same-environment interrupted/resumed training proof.

    Explicit per-step schedules/forward seeds mean no opaque dataloader state.
    This tests model/optimizer/scheduler/Torch RNG save/restore, not DDP or CUDA.
    It is separate from the CLI's weights-only initialization behavior.
    """
    from cvsubstrate.contracts.models import ExperimentSpec, EvaluationProtocol
    import torch
    setup(41)
    cmap = {c.id: i + 1 for i, c in enumerate(m.categories)}
    spec = ExperimentSpec(name='resume-test', dataset='dataset.json', dataset_sha256=digest(m), seed=41, training=TrainingSpec(updates=4), evaluation=EvaluationProtocol(evaluator='diagnostic_detection', evaluator_version='1'))
    steps = plan(spec, m)['stages'][0]['steps']
    full = model_factory(len(cmap) + 1)
    opt, sch = optimizer_for(full, 0.001)
    for s in steps:
        train_step(full, opt, sch, m, root, s, cmap, 1.0)
    expected = tensor_state_digest(full.state_dict())
    expected_predictions = predict_rows(full, m, root, 'dev', cmap)
    setup(41)
    half = model_factory(len(cmap) + 1)
    opt2, sch2 = optimizer_for(half, 0.001)
    for s in steps[:2]:
        train_step(half, opt2, sch2, m, root, s, cmap, 1.0)
    out.mkdir(parents=True, exist_ok=True)
    checkpoint = out / 'resume-test.pt'
    save_checkpoint(checkpoint, half, opt2, sch2, {}, {'next_step': 2, 'steps': steps})
    saved = load_owned_checkpoint(checkpoint)
    resumed = model_factory(len(cmap) + 1)
    resumed.load_state_dict(saved['model'])
    opt3, sch3 = optimizer_for(resumed, 0.001)
    opt3.load_state_dict(saved['optimizer'])
    sch3.load_state_dict(saved['scheduler'])
    torch.set_rng_state(saved['torch_rng'])
    for s in saved['progress']['steps'][saved['progress']['next_step']:]:
        train_step(resumed, opt3, sch3, m, root, s, cmap, 1.0)
    observed = tensor_state_digest(resumed.state_dict())
    actual_predictions = predict_rows(resumed, m, root, 'dev', cmap)
    exact = expected == observed
    prediction_exact = [r.model_dump() for r in expected_predictions] == [r.model_dump() for r in actual_predictions]
    result = {'status': 'PASS' if exact and prediction_exact else 'FAIL', 'parameter_state_exact': exact, 'predictions_exact': prediction_exact, 'uninterrupted_digest': expected, 'resumed_digest': observed, 'updates': 4, 'interruption_after': 2, 'scope': 'same-environment CPU fp32; explicit schedule and source forward seeds', 'cli_resume_support': 'CLI checkpoint initialization is weights-only; arbitrary interrupted-run resume orchestration is deferred.'}
    write_json(out / 'resume-verification.json', result)
    if not exact or not prediction_exact:
        raise CVRSError('RESUME_MISMATCH', 'resume selftest differs')
    return result
if __name__ == '__main__':
    entrypoint(run)
