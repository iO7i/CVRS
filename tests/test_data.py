import json
import pytest
from pydantic import ValidationError
from cvsubstrate.contracts.models import Sample, Split, DatasetManifest, FinalTestAuthorization
from cvsubstrate.data.manifest import validate_manifest, validate_experiment, image_dimensions, load_manifest
from cvsubstrate.data.coco import import_coco
from cvsubstrate.data.fixtures import generate
from cvsubstrate.provenance.io import digest, file_digest, write_json, experiment_identity
from cvsubstrate.errors import CVRSError

def test_fixture_reproducibility(tmp_path):
    a = tmp_path / 'a'
    b = tmp_path / 'b'
    generate(a)
    generate(b)
    assert digest(load_manifest(a / 'dataset.json')) == digest(load_manifest(b / 'dataset.json'))

def test_fixture_refuses_overwrite(tmp_path):
    generate(tmp_path / 'data')
    with pytest.raises(FileExistsError):
        generate(tmp_path / 'data')

def test_image_hash_tamper(dataset):
    m, root = dataset
    p = root / m.samples[0].image
    p.write_bytes(p.read_bytes() + b'tamper')
    with pytest.raises(CVRSError, match='content mismatch'):
        validate_manifest(m, root)

def test_missing_image(dataset):
    m, root = dataset
    (root / m.samples[0].image).unlink()
    with pytest.raises(CVRSError, match='missing'):
        validate_manifest(m, root)

def test_dimension_mismatch(dataset):
    m, root = dataset
    m.samples[0].width += 1
    with pytest.raises(CVRSError, match='dimensions'):
        validate_manifest(m, root)

def test_split_overlap(dataset):
    m, _ = dataset
    m.splits['dev'].sample_ids.append(m.splits['train'].sample_ids[0])
    with pytest.raises(CVRSError, match='appears'):
        validate_manifest(m, check_files=False)

def test_exact_content_leakage(dataset):
    m, _ = dataset
    m.samples[8].sha256 = m.samples[0].sha256
    with pytest.raises(CVRSError, match='identical image'):
        validate_manifest(m, check_files=False)

def test_declared_group_leakage(dataset):
    m, _ = dataset
    m.samples[8].lineage_group = m.samples[0].lineage_group
    with pytest.raises(CVRSError, match='lineage'):
        validate_manifest(m, check_files=False)

def test_transitive_parent_leakage(dataset):
    m, _ = dataset
    m.samples[0].parent_ids = ['parent-external']
    m.samples[8].parent_ids = ['parent-external']
    with pytest.raises(CVRSError, match='lineage'):
        validate_manifest(m, check_files=False)

def test_duplicate_ids_rejected(dataset):
    m, _ = dataset
    d = m.model_dump()
    d['samples'][1]['id'] = d['samples'][0]['id']
    with pytest.raises(ValidationError):
        DatasetManifest.model_validate(d)

def test_missing_split_reference(dataset):
    m, _ = dataset
    d = m.model_dump()
    d['splits']['dev']['sample_ids'].append('missing')
    with pytest.raises(ValidationError):
        DatasetManifest.model_validate(d)

def test_unknown_annotation_category(dataset):
    m, _ = dataset
    d = m.model_dump()
    d['samples'][0]['boxes'][0]['category_id'] = 999
    with pytest.raises(ValidationError):
        DatasetManifest.model_validate(d)

def test_noncrowd_ignore_rejected(dataset):
    m, _ = dataset
    m.samples[0].boxes[0].ignore = True
    with pytest.raises(CVRSError, match='noncrowd'):
        validate_manifest(m, check_files=False)

def test_crowd_preserved(dataset):
    m, _ = dataset
    m.samples[0].boxes[0].iscrowd = True
    assert validate_manifest(m, check_files=False)['status'] == 'VALID'

def test_dataset_digest_enforced(dataset, real_spec):
    m, _ = dataset
    real_spec.dataset_sha256 = 'a' * 64
    with pytest.raises(CVRSError, match='digest'):
        validate_experiment(real_spec, m)

def test_training_on_dev_rejected(dataset, real_spec):
    m, _ = dataset
    real_spec.train_split = 'dev'
    with pytest.raises(CVRSError, match='train-role'):
        validate_experiment(real_spec, m)

def test_evaluating_train_rejected(dataset, real_spec):
    m, _ = dataset
    real_spec.eval_split = 'train'
    with pytest.raises(CVRSError, match='evaluation requires'):
        validate_experiment(real_spec, m)

def test_locked_test_blocks_training(dataset, real_spec):
    m, _ = dataset
    m.splits['dev'].role = 'locked_test'
    real_spec.dataset_sha256 = digest(m)
    with pytest.raises(CVRSError, match='cannot access'):
        validate_experiment(real_spec, m)

def test_locked_test_requires_bound_authorization(dataset, real_spec):
    m, _ = dataset
    m.splits['dev'].role = 'locked_test'
    real_spec.dataset_sha256 = digest(m)
    real_spec.training = None
    with pytest.raises(CVRSError, match='authorization'):
        validate_experiment(real_spec, m)
    auth = FinalTestAuthorization(experiment_digest=experiment_identity(real_spec), dataset_digest=digest(m), split='dev', approved_by='fixture-approver', approved_at='2026-09-17T00:00:00Z', acknowledge_policy_not_sandbox=True)
    validate_experiment(real_spec, m, auth.model_dump(mode='json'))
    auth.experiment_digest = 'b' * 64
    with pytest.raises(CVRSError, match='does not cover'):
        validate_experiment(real_spec, m, auth.model_dump(mode='json'))

def test_preprocessing_not_silently_ignored(dataset, real_spec):
    m, _ = dataset
    real_spec.preprocessing = {'normalize_twice': True}
    with pytest.raises(CVRSError, match='worker-owned'):
        validate_experiment(real_spec, m)

def test_generic_runner_requires_dedicated_tiling_path(dataset, real_spec):
    m, _ = dataset
    real_spec.evaluation.tile_merge_policy = {'kind': 'nms', 'iou': 0.5}
    with pytest.raises(CVRSError, match='dedicated run-tiled'):
        validate_experiment(real_spec, m)

def simple_coco(m):
    s = m.samples[0]
    b = s.boxes[0].xyxy
    return {'images': [{'id': 29, 'file_name': s.image, 'width': s.width, 'height': s.height}], 'categories': [{'id': 3, 'name': 'fixture-a'}, {'id': 17, 'name': 'fixture-b'}], 'annotations': [{'id': 1, 'image_id': 29, 'category_id': 3, 'bbox': [b[0], b[1], b[2] - b[0], b[3] - b[1]], 'area': 33.0, 'iscrowd': 0}]}

def test_coco_import_retains_category_ids_and_annotation_area(dataset, tmp_path):
    m, root = dataset
    p = tmp_path / 'coco.json'
    write_json(p, simple_coco(m))
    out = import_coco(p, root, 'imported')
    assert [c.id for c in out.categories] == [3, 17]
    assert out.samples[0].boxes[0].area == 33.0

@pytest.mark.parametrize('fault', ['missing-image', 'duplicate-image', 'duplicate-ann', 'degenerate', 'unknown-category', 'noncrowd-ignore'])
def test_coco_import_rejects_malformed(dataset, tmp_path, fault):
    m, root = dataset
    d = simple_coco(m)
    if fault == 'missing-image':
        d['annotations'][0]['image_id'] = 5
    if fault == 'duplicate-image':
        d['images'] *= 2
    if fault == 'duplicate-ann':
        d['annotations'] *= 2
    if fault == 'degenerate':
        d['annotations'][0]['bbox'][2] = 0.0
    if fault == 'unknown-category':
        d['annotations'][0]['category_id'] = 999
    if fault == 'noncrowd-ignore':
        d['annotations'][0]['ignore'] = 1
    p = tmp_path / 'coco.json'
    write_json(p, d)
    with pytest.raises((CVRSError, ValidationError)):
        import_coco(p, root, 'bad')
