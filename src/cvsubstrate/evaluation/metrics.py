"""Explicit evaluator selection. Diagnostic matching is NEVER called COCO AP.

The optional COCO adapter invokes pycocotools directly. Import failure is an
error, not permission to silently substitute the diagnostic implementation.
"""
from __future__ import annotations
from collections import defaultdict
import contextlib
import importlib.metadata
import io
from typing import Sequence
from cvsubstrate.contracts.models import DatasetManifest, DetectionPrediction, EvaluationProtocol
from cvsubstrate.data.tiling import iou
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import digest

def validate_predictions(m: DatasetManifest, split: str, predictions: Sequence[DetectionPrediction]) -> None:
    ids = m.splits[split].sample_ids
    seen = [p.sample_id for p in predictions]
    if len(set(seen)) != len(seen):
        raise CVRSError('DUPLICATE_PREDICTIONS', 'duplicate prediction rows for image')
    if set(seen) != set(ids):
        raise CVRSError('IMAGE_UNIVERSE', 'predictions must contain exactly one row per selected image, including empty results')
    samples = {s.id: s for s in m.samples}
    categories = {c.id for c in m.categories}
    for pred in predictions:
        s = samples[pred.sample_id]
        if (pred.width, pred.height) != (s.width, s.height):
            raise CVRSError('PREDICTION_DIMENSIONS', 'original image dimensions mismatch')
        if not set(pred.category_ids).issubset(categories):
            raise CVRSError('UNKNOWN_CATEGORY', 'prediction category missing from dataset taxonomy')

def _safe_ratio(n, d):
    return {'value': n / d if d else None, 'reason': None if d else 'zero denominator'}

def _diagnostic_subset(m, ids, predictions, protocol):
    samples = {s.id: s for s in m.samples}
    thresholds = protocol.iou_thresholds
    results = []
    for threshold in thresholds:
        tp = fp = fn = ignored = gt_count = det_count = 0
        by_area = {name: {'ground_truth': 0, 'matched_ground_truth': 0} for name in ['tiny_lt_256', 'small_256_to_1024', 'larger_ge_1024']}
        for sid in ids:
            s = samples[sid]
            pred = predictions[sid]
            candidates = sorted([i for i, v in enumerate(pred.scores) if v >= protocol.score_threshold], key=lambda i: (-pred.scores[i], i))[:protocol.max_detections[-1]]
            gt = [b for b in s.boxes if not b.iscrowd]
            crowd = [b for b in s.boxes if b.iscrowd]
            used = set()
            gt_count += len(gt)
            det_count += len(candidates)
            for i in candidates:
                b = pred.boxes[i]
                cat = pred.category_ids[i]
                matches = [(iou(b, g.xyxy), j) for j, g in enumerate(gt) if j not in used and g.category_id == cat]
                overlap, index = max(matches, default=(-1.0, -1), key=lambda pair: (pair[0], -pair[1]))
                if overlap >= threshold:
                    tp += 1
                    used.add(index)
                    continue

                def ioa(g):
                    a = b
                    v = g.xyxy
                    inter = max(0.0, min(a[2], v[2]) - max(a[0], v[0])) * max(0.0, min(a[3], v[3]) - max(a[1], v[1]))
                    return inter / ((a[2] - a[0]) * (a[3] - a[1]))
                if any((g.category_id == cat and ioa(g) >= threshold for g in crowd)):
                    ignored += 1
                else:
                    fp += 1
            fn += len(gt) - len(used)
            for j, g in enumerate(gt):
                # Diagnostic pixel-area is BBOX area, not segmentation area.
                a = (g.xyxy[2] - g.xyxy[0]) * (g.xyxy[3] - g.xyxy[1])
                key = 'tiny_lt_256' if a < 256 else 'small_256_to_1024' if a < 1024 else 'larger_ge_1024'
                by_area[key]['ground_truth'] += 1
                by_area[key]['matched_ground_truth'] += int(j in used)
        for stats in by_area.values():
            stats['recall'] = _safe_ratio(stats['matched_ground_truth'], stats['ground_truth'])
        results.append({'iou': threshold, 'true_positives': tp, 'false_positives': fp, 'false_negatives': fn, 'ignored_crowd_predictions': ignored, 'ground_truth_objects': gt_count, 'predictions_after_threshold': det_count, 'precision': _safe_ratio(tp, tp + fp), 'recall': _safe_ratio(tp, tp + fn), 'object_size_recall_slices': by_area})
    return {'images': len(ids), 'counts_by_iou': results}

def diagnostic_detection(m, split, rows, protocol):
    """Greedy per-image, class-aware fixed-threshold diagnostics; not AP or COCOeval."""
    pred = {p.sample_id: p for p in rows}
    ids = m.splits[split].sample_ids
    by_domain = defaultdict(list)
    by_id = {s.id: s for s in m.samples}
    for sid in ids:
        by_domain[by_id[sid].domain].append(sid)
    return {'kind': 'DIAGNOSTIC_NOT_COCO', 'evaluator': 'diagnostic_detection', 'evaluator_version': '1', 'warning': 'Fixed-threshold greedy counts/precision/recall. NOT COCO AP, not calibrated, no confidence intervals.', 'aggregate': _diagnostic_subset(m, ids, pred, protocol), 'domain_slices': {domain: _diagnostic_subset(m, sids, pred, protocol) for domain, sids in sorted(by_domain.items())}}

def to_coco(m: DatasetManifest, split: str, rows: Sequence[DetectionPrediction], score_threshold=0.0):
    ids = m.splits[split].sample_ids
    by_id = {s.id: s for s in m.samples}
    # Stable positive internal image IDs; original IDs preserved in mapping evidence.
    image_mapping = {sid: i + 1 for i, sid in enumerate(ids)}
    gt = {'info': {'description': 'cvsubstrate explicit bbox evaluation'}, 'licenses': [], 'images': [{'id': image_mapping[sid], 'width': by_id[sid].width, 'height': by_id[sid].height} for sid in ids], 'categories': [{'id': c.id, 'name': c.name} for c in m.categories], 'annotations': []}
    for sid in ids:
        for b in by_id[sid].boxes:
            if b.ignore and (not b.iscrowd):
                raise CVRSError('UNSUPPORTED_IGNORE', 'noncrowd ignore unsupported')
            x1, y1, x2, y2 = b.xyxy
            gt['annotations'].append({'id': len(gt['annotations']) + 1, 'image_id': image_mapping[sid], 'category_id': b.category_id, 'bbox': [x1, y1, x2 - x1, y2 - y1], 'area': b.area if b.area is not None else (x2 - x1) * (y2 - y1), 'iscrowd': int(b.iscrowd)})
    dt = []
    for row in rows:
        for b, score, category in zip(row.boxes, row.scores, row.category_ids):
            if score < score_threshold:
                continue
            x1, y1, x2, y2 = b
            dt.append({'image_id': image_mapping[row.sample_id], 'category_id': category, 'bbox': [x1, y1, x2 - x1, y2 - y1], 'score': score})
    return (gt, dt, image_mapping)

def coco_evaluate(m, split, rows, protocol):
    try:
        import numpy as np
        from pycocotools.coco import COCO
        from pycocotools.cocoeval import COCOeval
    except ImportError as exc:
        raise CVRSError('COCO_DEPENDENCY', 'pycocotools==2.0.11 and numpy are required; no fallback was used') from exc
    version = importlib.metadata.version('pycocotools')
    if version != protocol.evaluator_version:
        raise CVRSError('EVALUATOR_VERSION', f'expected {protocol.evaluator_version}, found {version}')
    gt, dt, mapping = to_coco(m, split, rows, protocol.score_threshold)
    with contextlib.redirect_stdout(io.StringIO()):
        cg = COCO()
        cg.dataset = gt
        cg.createIndex()
        if dt:
            cd = cg.loadRes(dt)
        else:
            # COCO.loadRes([]) indexes anns[0] in some versions. Make an empty
            # detection COCO object directly; do not fabricate a detection.
            cd = COCO()
            cd.dataset = {'images': gt['images'], 'categories': gt['categories'], 'annotations': []}
            cd.createIndex()
        ev = COCOeval(cg, cd, 'bbox')
        ev.params.imgIds = list(mapping.values())
        ev.params.catIds = [c.id for c in m.categories]
        ev.params.iouThrs = np.asarray(protocol.iou_thresholds)
        ev.params.recThrs = np.asarray(protocol.recall_thresholds)
        ev.params.maxDets = protocol.max_detections
        ev.params.areaRng = list(protocol.area_ranges.values())
        ev.params.areaRngLbl = list(protocol.area_ranges)
        ev.params.useCats = 1
        ev.evaluate()
        ev.accumulate()
    # Extract directly from reference precision/recall arrays instead of relying
    # on summarize(), whose printed slots assume default COCO settings.
    metric = {}
    for ai, area in enumerate(protocol.area_ranges):
        for mi, maximum in enumerate(protocol.max_detections):
            for label, values in [('AP', ev.eval['precision'][:, :, :, ai, mi]), ('AR', ev.eval['recall'][:, :, ai, mi])]:
                valid = values[values > -1]
                metric[f'{label}/{area}/maxDets={maximum}'] = {'value': float(valid.mean()) if valid.size else None, 'reason': None if valid.size else 'no evaluable ground truth in this slice'}
    ap50 = None
    if 0.5 in protocol.iou_thresholds:
        ti = protocol.iou_thresholds.index(0.5)
        ai = list(protocol.area_ranges).index('all')
        values = ev.eval['precision'][ti, :, :, ai, -1]
        values = values[values > -1]
        ap50 = {'value': float(values.mean()) if values.size else None, 'reason': None if values.size else 'no evaluable ground truth'}
    return {'kind': 'REFERENCE_COCO_BBOX', 'evaluator': 'pycocotools', 'evaluator_version': version, 'metrics': metric, 'AP50': ap50, 'image_id_mapping': mapping, 'support': {'images': len(mapping), 'objects': len(gt['annotations']), 'categories': len(gt['categories'])}, 'note': 'AP uses declared reference parameters; non-default settings are not the canonical COCO leaderboard protocol.'}

def evaluate(m: DatasetManifest, split: str, rows: Sequence[DetectionPrediction], protocol: EvaluationProtocol) -> dict:
    validate_predictions(m, split, rows)
    for s in m.samples:
        if any((b.ignore and (not b.iscrowd) for b in s.boxes)):
            raise CVRSError('UNSUPPORTED_IGNORE', 'noncrowd ignore unsupported')
    result = (coco_evaluate if protocol.evaluator == 'pycocotools' else diagnostic_detection)(m, split, rows, protocol)
    result['comparison_key'] = {'dataset_digest': digest(m), 'split': split, 'sample_ids': m.splits[split].sample_ids, 'taxonomy': [c.model_dump(mode='json') for c in m.categories], 'evaluation_protocol': protocol.model_dump(mode='json')}
    result['comparison_digest'] = digest(result['comparison_key'])
    result['dataset_purpose'] = m.purpose
    if m.purpose == 'software_fixture':
        result['scientific_claim'] = 'NONE: software fixtures do not establish detector quality or Sim2Real improvement'
    return result
