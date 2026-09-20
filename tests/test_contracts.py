import math
import json
import random
import pytest
from pydantic import ValidationError
from cvsubstrate.errors import CVRSError
from cvsubstrate.contracts.models import Box, DetectionPrediction, DatasetManifest, EvaluationProtocol, GenerationMetadata, WorkerRequest, WorkerResponse, SCHEMAS
from cvsubstrate.provenance.io import canonical_bytes, digest, read_json, write_json, experiment_identity, safe_join, read_jsonl

@pytest.mark.parametrize('box', [[-1.0, 0.0, 1.0, 1.0], [0.0, -1.0, 1.0, 1.0], [0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 1.0, 0.0], [3.0, 0.0, 2.0, 1.0], [0.0, 0.0, math.inf, 1.0], [0.0, 0.0, math.nan, 1.0], [0.0, 0.0, 1.0], ['0', 0.0, 1.0, 1.0], [False, 0.0, 1.0, 1.0]])
def test_invalid_box_rejected(box):
    with pytest.raises(ValidationError):
        Box(xyxy=box, category_id=3)

@pytest.mark.parametrize('category', [-1, True, 3.1, '3'])
def test_category_ids_are_strict(category):
    with pytest.raises(ValidationError):
        Box(xyxy=[0.0, 0.0, 1.0, 1.0], category_id=category)

def test_no_pixel_plus_one():
    b = Box(xyxy=[0.0, 0.0, 1.0, 1.0], category_id=0)
    assert (b.xyxy[2] - b.xyxy[0]) * (b.xyxy[3] - b.xyxy[1]) == 1.0

@pytest.mark.parametrize('score', [-0.1, 1.1, math.nan, math.inf, '0.5'])
def test_invalid_score(score):
    with pytest.raises(ValidationError):
        DetectionPrediction(sample_id='a', width=2, height=2, boxes=[[0.0, 0.0, 1.0, 1.0]], scores=[score], category_ids=[3])

def test_empty_prediction_valid():
    row = DetectionPrediction(sample_id='empty', width=64, height=64, boxes=[], scores=[], category_ids=[])
    assert row.boxes == []

def test_prediction_arrays_must_align():
    with pytest.raises(ValidationError):
        DetectionPrediction(sample_id='a', width=2, height=2, boxes=[], scores=[0.5], category_ids=[])

def test_prediction_frame_and_bounds():
    with pytest.raises(ValidationError):
        DetectionPrediction(sample_id='a', width=2, height=2, boxes=[[0.0, 0.0, 3.0, 1.0]], scores=[0.5], category_ids=[3])
    with pytest.raises(ValidationError):
        DetectionPrediction(sample_id='a', width=2, height=2, boxes=[], scores=[], category_ids=[], coordinate_frame='tile')

def test_unknown_fields_rejected():
    with pytest.raises(ValidationError):
        Box(xyxy=[0.0, 0.0, 1.0, 1.0], category_id=3, mystery=True)

def test_nested_nonfinite_metadata_rejected():
    with pytest.raises(ValidationError):
        GenerationMetadata(planned={'camera': {'altitude': math.inf}})

def test_unknown_occlusion_not_zero():
    assert GenerationMetadata().occlusion_fraction is None

def test_schema_protocol_version_rejected():
    with pytest.raises(ValidationError):
        WorkerRequest(operation='predict', protocol_version='9.9')
    with pytest.raises(ValidationError):
        WorkerResponse(status='SUCCEEDED', schema_version='2.0')

@pytest.mark.parametrize('change', [{'iou_thresholds': [0.5, 0.5]}, {'iou_thresholds': [0.6, 0.5]}, {'iou_thresholds': [0.0]}, {'max_detections': [100, 10, 1]}, {'max_detections': [1, 100]}, {'area_ranges': {'small': [0.0, 3.0]}}, {'area_ranges': {'all': [3.0, 1.0]}}, {'evaluator': 'diagnostic_detection', 'evaluator_version': '2.0.11'}])
def test_protocol_invalid(change):
    with pytest.raises(ValidationError):
        EvaluationProtocol(**change)

def test_canonical_json_order_and_defaults():
    assert digest({'b': 1, 'a': 2}) == digest({'a': 2, 'b': 1})
    assert digest([1, 2]) != digest([2, 1])
    assert b' ' not in canonical_bytes({'a': 1})
    assert b'\\u' not in canonical_bytes({'name': 'العربية'})

def test_canonical_json_no_nonfinite_or_nonstring_keys():
    with pytest.raises(ValueError):
        canonical_bytes({'x': math.nan})
    with pytest.raises(ValueError):
        canonical_bytes({1: 'a'})

def test_duplicate_json_key_rejected(tmp_path):
    p = tmp_path / 'bad.json'
    p.write_text('{"a":1,"a":2}')
    with pytest.raises(ValueError):
        read_json(p)

@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-Infinity'])
def test_invalid_json_number(tmp_path, value):
    p = tmp_path / 'bad.json'
    p.write_text('{"a":' + value + '}')
    with pytest.raises(ValueError):
        read_json(p)

@pytest.mark.parametrize('value', ['../x', '/absolute', 'a/../../x', 'C:/users/file', 'a\\b', './x', 'a//x'])
def test_path_escape_rejected(tmp_path, value):
    with pytest.raises((ValueError, CVRSError)):
        safe_join(tmp_path, value)

def test_json_roundtrip_model(dataset, tmp_path):
    m, _ = dataset
    p = tmp_path / 'manifest.json'
    write_json(p, m)
    assert digest(DatasetManifest.model_validate(read_json(p))) == digest(m)

def test_experiment_digest_ignores_location_not_training(real_spec):
    a = real_spec.model_copy(deep=True)
    b = real_spec.model_copy(deep=True)
    b.dataset = '/another/machine/dataset.json'
    b.notes = 'different prose'
    assert experiment_identity(a) == experiment_identity(b)
    b.seed += 1
    assert experiment_identity(a) != experiment_identity(b)

@pytest.mark.parametrize('cls', SCHEMAS)
def test_schema_serializable_and_versioned(cls):
    schema = cls.model_json_schema()
    assert schema['additionalProperties'] is False
    assert schema['properties']['schema_version']['const'] == '1.0'
    json.dumps(schema, allow_nan=False)

def test_schemas_validate_positive_fixtures(dataset):
    jsonschema = pytest.importorskip('jsonschema')
    m, _ = dataset
    jsonschema.Draft202012Validator(DatasetManifest.model_json_schema()).validate(m.model_dump(mode='json'))
