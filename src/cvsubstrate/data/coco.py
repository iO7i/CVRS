"""Strict COCO box ingestion; no noncontiguous-category renumbering at storage time."""
from pathlib import Path
from cvsubstrate.contracts.models import Box, Category, DatasetManifest, LicenseInfo, Sample, Split
from cvsubstrate.data.manifest import validate_manifest
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import file_digest, read_json, safe_join

def import_coco(annotation_file: Path, image_root: Path, name: str, split_role='dev', source_kind='unknown', licenses: LicenseInfo | None=None) -> DatasetManifest:
    coco = read_json(annotation_file)
    categories = [Category(id=c['id'], name=c['name']) for c in coco['categories']]
    images = {}
    for image in coco['images']:
        if image['id'] in images:
            raise CVRSError('DUPLICATE_IMAGE', 'duplicate COCO image ID')
        if not isinstance(image['id'], int):
            raise CVRSError('IMAGE_ID', 'COCO image IDs must be integers')
        images[image['id']] = image
    boxes = {key: [] for key in images}
    seen = set()
    for ann in coco['annotations']:
        if ann['id'] in seen:
            raise CVRSError('DUPLICATE_ANNOTATION', 'duplicate COCO annotation ID')
        seen.add(ann['id'])
        if ann['image_id'] not in images:
            raise CVRSError('MISSING_IMAGE_REFERENCE', 'annotation references missing image')
        x, y, w, h = ann['bbox']
        if w <= 0 or h <= 0:
            raise CVRSError('DEGENERATE_BOX', 'COCO width/height must be positive')
        if ann.get('iscrowd', 0) not in (0, 1) or ann.get('ignore', 0) not in (0, 1):
            raise CVRSError('ANNOTATION_FLAG', 'COCO crowd/ignore flags must be 0 or 1')
        boxes[ann['image_id']].append(Box(xyxy=[x, y, x + w, y + h], category_id=ann['category_id'], iscrowd=bool(ann.get('iscrowd', 0)), ignore=bool(ann.get('ignore', 0)), area=ann.get('area', w * h)))
    samples = []
    for image in images.values():
        p = safe_join(image_root, image['file_name'])
        samples.append(Sample(id=f"coco-{image['id']}", image=image['file_name'], sha256=file_digest(p), width=image['width'], height=image['height'], source_kind=source_kind, boxes=boxes[image['id']]))
    m = DatasetManifest(name=name, version='import-1', categories=categories, samples=samples, splits={split_role: Split(role=split_role, sample_ids=[s.id for s in samples])}, licenses=licenses or LicenseInfo(), notes='COCO import: segmentation is not imported; supplied annotation area is retained for bbox evaluation.')
    validate_manifest(m, image_root)
    return m
