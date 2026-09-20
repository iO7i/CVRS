from copy import deepcopy
import importlib.util
import pytest
from cvsubstrate.contracts.models import DetectionPrediction, EvaluationProtocol
from cvsubstrate.evaluation.metrics import evaluate, validate_predictions, to_coco
from cvsubstrate.evaluation.compare import compare
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import digest

def perfect_rows(m, split='dev'):
    by = {s.id: s for s in m.samples}
    return [DetectionPrediction(sample_id=sid, width=by[sid].width, height=by[sid].height, boxes=[b.xyxy for b in by[sid].boxes], scores=[0.99 for b in by[sid].boxes], category_ids=[b.category_id for b in by[sid].boxes]) for sid in m.splits[split].sample_ids]

def diagnostic():
    return EvaluationProtocol(evaluator='diagnostic_detection', evaluator_version='1', iou_thresholds=[0.5], score_threshold=0.5)

def test_perfect_diagnostic_is_not_coco(dataset):
    m, _ = dataset
    r = evaluate(m, 'dev', perfect_rows(m), diagnostic())
    counts = r['aggregate']['counts_by_iou'][0]
    assert r['kind'] == 'DIAGNOSTIC_NOT_COCO'
    assert counts['true_positives'] == 3 and counts['false_positives'] == 0 and (counts['false_negatives'] == 0)
    assert counts['recall']['value'] == 1.0
    assert 'AP' not in r

def test_empty_prediction_undefined_precision(dataset):
    m, _ = dataset
    rows = perfect_rows(m)
    rows = [DetectionPrediction(sample_id=r.sample_id, width=r.width, height=r.height, boxes=[], scores=[], category_ids=[]) for r in rows]
    result = evaluate(m, 'dev', rows, diagnostic())['aggregate']['counts_by_iou'][0]
    assert result['precision'] == {'value': None, 'reason': 'zero denominator'}
    assert result['recall']['value'] == 0.0

def test_swapped_labels_are_not_equivalent(dataset):
    m, _ = dataset
    rows = perfect_rows(m)
    for r in rows:
        r.category_ids = [17 if c == 3 else 3 for c in r.category_ids]
    assert evaluate(m, 'dev', rows, diagnostic())['aggregate']['counts_by_iou'][0]['true_positives'] == 0

def test_duplicate_detections_are_false_positives(dataset):
    m, _ = dataset
    rows = perfect_rows(m)
    # Construct atomically because assignment validation protects array consistency.
    data = rows[0].model_dump()
    data['boxes'] *= 2
    data['scores'] *= 2
    data['category_ids'] *= 2
    rows[0] = DetectionPrediction.model_validate(data)
    assert evaluate(m, 'dev', rows, diagnostic())['aggregate']['counts_by_iou'][0]['false_positives'] == 1

def test_incomplete_image_universe_rejected(dataset):
    m, _ = dataset
    with pytest.raises(CVRSError, match='exactly one'):
        evaluate(m, 'dev', perfect_rows(m)[:-1], diagnostic())

def test_duplicate_prediction_rows_rejected(dataset):
    m, _ = dataset
    rows = perfect_rows(m)
    with pytest.raises(CVRSError, match='duplicate'):
        evaluate(m, 'dev', rows + [rows[0]], diagnostic())

def test_prediction_dimensions_rejected(dataset):
    m, _ = dataset
    rows = perfect_rows(m)
    rows[0].width += 1
    with pytest.raises(CVRSError, match='dimensions'):
        evaluate(m, 'dev', rows, diagnostic())

def test_unknown_predicted_category_rejected(dataset):
    m, _ = dataset
    rows = perfect_rows(m)
    rows[0].category_ids = [999]
    with pytest.raises(CVRSError, match='category'):
        evaluate(m, 'dev', rows, diagnostic())

def test_crowd_can_absorb_multiple_predictions(dataset):
    m, _ = dataset
    m.samples[8].boxes[0].iscrowd = True
    rows = perfect_rows(m)
    d = rows[0].model_dump()
    d['boxes'] *= 2
    d['scores'] *= 2
    d['category_ids'] *= 2
    rows[0] = DetectionPrediction.model_validate(d)
    r = evaluate(m, 'dev', rows, diagnostic())['aggregate']['counts_by_iou'][0]
    assert r['ignored_crowd_predictions'] == 2 and r['false_positives'] == 0

def test_comparison_same_protocol_different_predictions(dataset):
    m, _ = dataset
    a = evaluate(m, 'dev', perfect_rows(m), diagnostic())
    b = deepcopy(a)
    b['unrelated_weights_digest'] = 'other'
    assert compare(a, b)['status'] == 'COMPARABLE_UNDER_DECLARED_PROTOCOL'
    assert compare(a, b)['training_fairness'] == 'NOT_ASSESSED'

@pytest.mark.parametrize('key', ['dataset_digest', 'split', 'sample_ids', 'taxonomy', 'evaluation_protocol'])
def test_comparison_rejects_incompatible_keys(dataset, key):
    m, _ = dataset
    a = evaluate(m, 'dev', perfect_rows(m), diagnostic())
    b = deepcopy(a)
    b['comparison_key'][key] = 'changed'
    b['comparison_digest'] = digest(b['comparison_key'])
    assert compare(a, b)['status'] == 'INCOMPARABLE'

def test_compare_missing_key_descriptive():
    assert compare({}, {})['status'] == 'DESCRIPTIVE_ONLY'

def test_comparison_digest_tamper(dataset):
    m, _ = dataset
    a = evaluate(m, 'dev', perfect_rows(m), diagnostic())
    b = deepcopy(a)
    b['comparison_digest'] = 'x'
    assert compare(a, b)['status'] == 'INCOMPARABLE'

def test_coco_conversion_area_and_labels_preserved(dataset):
    m, _ = dataset
    m.samples[8].boxes[0].area = 37.0
    gt, dt, mapping = to_coco(m, 'dev', perfect_rows(m))
    assert gt['annotations'][0]['area'] == 37.0
    assert {c['id'] for c in gt['categories']} == {3, 17}
    assert len(mapping) == 4 and len(dt) == 3

def test_coco_missing_dependency_does_not_fallback(dataset):
    if importlib.util.find_spec('pycocotools'):
        pytest.skip('dependency present; exercised by reference tests')
    m, _ = dataset
    with pytest.raises(CVRSError, match='no fallback'):
        evaluate(m, 'dev', perfect_rows(m), EvaluationProtocol())

@pytest.mark.coco
@pytest.mark.parametrize('mode', ['perfect', 'empty', 'duplicate', 'crowd'])
def test_official_coco_reference_parity(dataset, mode):
    pytest.importorskip('numpy')
    pytest.importorskip('pycocotools', reason='official COCO package unavailable; reference parity NOT_RUN')
    import contextlib, io
    import numpy as np
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval
    m, _ = dataset
    rows = perfect_rows(m)
    if mode == 'empty':
        rows = [DetectionPrediction(sample_id=r.sample_id, width=r.width, height=r.height, boxes=[], scores=[], category_ids=[]) for r in rows]
    if mode == 'duplicate':
        d = rows[0].model_dump()
        d['boxes'] *= 2
        d['scores'] *= 2
        d['category_ids'] *= 2
        rows[0] = DetectionPrediction.model_validate(d)
    if mode == 'crowd':
        m.samples[8].boxes[0].iscrowd = True
    protocol = EvaluationProtocol()
    result = evaluate(m, 'dev', rows, protocol)
    # Independent conversion from hand-authored sample fields rather than calling
    # the wrapper's conversion helper for the reference path.
    samples = {s.id: s for s in m.samples}
    ids = {sid: i + 100 for i, sid in enumerate(m.splits['dev'].sample_ids)}
    truth = {'info': {}, 'images': [{'id': ids[sid], 'width': samples[sid].width, 'height': samples[sid].height} for sid in ids], 'categories': [{'id': 3, 'name': 'fixture-a'}, {'id': 17, 'name': 'fixture-b'}], 'annotations': []}
    for sid in ids:
        for b in samples[sid].boxes:
            x, y, xx, yy = b.xyxy
            truth['annotations'].append({'id': len(truth['annotations']) + 1, 'image_id': ids[sid], 'category_id': b.category_id, 'bbox': [x, y, xx - x, yy - y], 'area': b.area if b.area is not None else (xx - x) * (yy - y), 'iscrowd': int(b.iscrowd)})
    detections = []
    for r in rows:
        for b, s, c in zip(r.boxes, r.scores, r.category_ids):
            detections.append({'image_id': ids[r.sample_id], 'category_id': c, 'score': s, 'bbox': [b[0], b[1], b[2] - b[0], b[3] - b[1]]})
    with contextlib.redirect_stdout(io.StringIO()):
        cg = COCO()
        cg.dataset = truth
        cg.createIndex()
        if detections:
            cd = cg.loadRes(detections)
        else:
            cd = COCO()
            cd.dataset = {**truth, 'annotations': []}
            cd.createIndex()
        ev = COCOeval(cg, cd, 'bbox')
        ev.evaluate()
        ev.accumulate()
    precision = ev.eval['precision'][:, :, :, 0, -1]
    valid = precision[precision > -1]
    expected = float(valid.mean()) if valid.size else None
    observed = result['metrics']['AP/all/maxDets=100']['value']
    assert observed == pytest.approx(expected, abs=1e-12) if expected is not None else observed is None
