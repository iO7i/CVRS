"""Independent direct pycocotools path used to audit the CVRS wrapper.

This module deliberately rebuilds COCO ground-truth/detection dictionaries instead
of calling ``metrics.to_coco``. It is a second implementation path for parity tests,
not a replacement evaluator. Both paths still rely on the pinned pycocotools package.
"""
from __future__ import annotations
import contextlib
import importlib.metadata
import io
from typing import Sequence
from cvsubstrate.contracts.models import DatasetManifest, DetectionPrediction, EvaluationProtocol
from cvsubstrate.errors import CVRSError


def direct_coco_evaluate(m: DatasetManifest, split: str, rows: Sequence[DetectionPrediction], protocol: EvaluationProtocol) -> dict:
    try:
        import numpy as np
        from pycocotools.coco import COCO
        from pycocotools.cocoeval import COCOeval
    except ImportError as exc:
        raise CVRSError('COCO_DEPENDENCY', 'pycocotools==2.0.11 and numpy are required for direct reference audit') from exc
    version = importlib.metadata.version('pycocotools')
    if version != protocol.evaluator_version:
        raise CVRSError('EVALUATOR_VERSION', f'expected {protocol.evaluator_version}, found {version}')
    ids = list(m.splits[split].sample_ids)
    sample_by_id = {s.id: s for s in m.samples}
    prediction_by_id = {p.sample_id: p for p in rows}
    mapping = {sid: index + 1 for index, sid in enumerate(ids)}
    dataset = {
        'info': {'description': 'cvsubstrate direct reference audit'},
        'licenses': [],
        'images': [{'id': mapping[sid], 'width': sample_by_id[sid].width, 'height': sample_by_id[sid].height} for sid in ids],
        'categories': [{'id': c.id, 'name': c.name} for c in m.categories],
        'annotations': [],
    }
    for sid in ids:
        for box in sample_by_id[sid].boxes:
            if box.ignore and not box.iscrowd:
                raise CVRSError('UNSUPPORTED_IGNORE', 'direct reference audit does not reinterpret noncrowd ignore')
            x1, y1, x2, y2 = box.xyxy
            dataset['annotations'].append({
                'id': len(dataset['annotations']) + 1,
                'image_id': mapping[sid],
                'category_id': box.category_id,
                'bbox': [x1, y1, x2 - x1, y2 - y1],
                'area': box.area if box.area is not None else (x2 - x1) * (y2 - y1),
                'iscrowd': int(box.iscrowd),
            })
    detections = []
    for sid in ids:
        row = prediction_by_id[sid]
        for box, score, category_id in zip(row.boxes, row.scores, row.category_ids):
            if score < protocol.score_threshold:
                continue
            x1, y1, x2, y2 = box
            detections.append({'image_id': mapping[sid], 'category_id': category_id, 'bbox': [x1, y1, x2 - x1, y2 - y1], 'score': score})
    with contextlib.redirect_stdout(io.StringIO()):
        gt = COCO()
        gt.dataset = dataset
        gt.createIndex()
        if detections:
            dt = gt.loadRes(detections)
        else:
            dt = COCO()
            dt.dataset = {'images': dataset['images'], 'categories': dataset['categories'], 'annotations': []}
            dt.createIndex()
        ev = COCOeval(gt, dt, 'bbox')
        ev.params.imgIds = list(mapping.values())
        ev.params.catIds = [c.id for c in m.categories]
        ev.params.iouThrs = np.asarray(protocol.iou_thresholds)
        ev.params.recThrs = np.asarray(protocol.recall_thresholds)
        ev.params.maxDets = list(protocol.max_detections)
        ev.params.areaRng = list(protocol.area_ranges.values())
        ev.params.areaRngLbl = list(protocol.area_ranges)
        ev.params.useCats = 1
        ev.evaluate()
        ev.accumulate()
    metrics = {}
    for ai, area in enumerate(protocol.area_ranges):
        for mi, maximum in enumerate(protocol.max_detections):
            precision = ev.eval['precision'][:, :, :, ai, mi]
            recall = ev.eval['recall'][:, :, ai, mi]
            for label, values in [('AP', precision), ('AR', recall)]:
                valid = values[values > -1]
                metrics[f'{label}/{area}/maxDets={maximum}'] = None if not valid.size else float(valid.mean())
    ap50 = None
    if 0.5 in protocol.iou_thresholds:
        ti = protocol.iou_thresholds.index(0.5)
        ai = list(protocol.area_ranges).index('all')
        valid = ev.eval['precision'][ti, :, :, ai, -1]
        valid = valid[valid > -1]
        ap50 = None if not valid.size else float(valid.mean())
    return {
        'evaluator': 'pycocotools',
        'evaluator_version': version,
        'metrics': metrics,
        'AP50': ap50,
        'image_id_mapping': mapping,
        'support': {'images': len(mapping), 'objects': len(dataset['annotations']), 'categories': len(dataset['categories'])},
    }


def parity_report(m: DatasetManifest, split: str, rows: Sequence[DetectionPrediction], protocol: EvaluationProtocol, tolerance: float = 1e-6) -> dict:
    import math
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError('tolerance must be finite and nonnegative')
    if split not in m.splits or m.splits[split].role != 'dev':
        raise CVRSError('EVAL_ROLE', 'reference parity is development-only; locked test requires a governed final run')
    from cvsubstrate.evaluation.metrics import coco_evaluate, validate_predictions
    validate_predictions(m, split, rows)
    wrapper = coco_evaluate(m, split, rows, protocol)
    direct = direct_coco_evaluate(m, split, rows, protocol)
    differences = []
    for key, direct_value in direct['metrics'].items():
        wrapped = wrapper['metrics'][key]['value']
        if direct_value is None or wrapped is None:
            if direct_value != wrapped:
                differences.append({'metric': key, 'wrapper': wrapped, 'direct': direct_value, 'absolute_delta': None})
        else:
            delta = abs(wrapped - direct_value)
            if delta > tolerance:
                differences.append({'metric': key, 'wrapper': wrapped, 'direct': direct_value, 'absolute_delta': delta})
    wrapped_ap50 = None if wrapper['AP50'] is None else wrapper['AP50']['value']
    direct_ap50 = direct['AP50']
    if wrapped_ap50 is None or direct_ap50 is None:
        if wrapped_ap50 != direct_ap50:
            differences.append({'metric': 'AP50', 'wrapper': wrapped_ap50, 'direct': direct_ap50, 'absolute_delta': None})
    elif abs(wrapped_ap50 - direct_ap50) > tolerance:
        differences.append({'metric': 'AP50', 'wrapper': wrapped_ap50, 'direct': direct_ap50, 'absolute_delta': abs(wrapped_ap50 - direct_ap50)})
    if wrapper['image_id_mapping'] != direct['image_id_mapping']:
        differences.append({'metric': 'image_id_mapping', 'wrapper': wrapper['image_id_mapping'], 'direct': direct['image_id_mapping'], 'absolute_delta': None})
    return {
        'status': 'PASS' if not differences else 'FAIL',
        'tolerance': tolerance,
        'differences': differences,
        'wrapper_evaluator': wrapper['evaluator_version'],
        'direct_evaluator': direct['evaluator_version'],
        'support': direct['support'],
        'note': 'Both paths use the pinned pycocotools package but construct/reference inputs independently.',
    }
