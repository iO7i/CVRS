"""Materialize image-population slices without relabeling excluded objects.

Object-level benchmark slices must use evaluator ignore/area semantics. This
function deliberately filters whole images only; it preserves all annotations
and predictions for each selected image, including negatives.
"""
import copy
from cvsubstrate.provenance.io import digest
from cvsubstrate.analysis.metric_plugins import slice_receipt


def population_slice(dataset,predictions,*,task,predicate,split=None):
    derived=copy.deepcopy(dataset)
    if task in {'hbb','obb'}:
        samples=dataset['samples']
        if task=='hbb':
            if split not in dataset['splits']:raise ValueError('slice split missing')
            ids=set(dataset['splits'][split]['sample_ids']);samples=[s for s in samples if s['id'] in ids]
        else:ids={s['id'] for s in samples}
    else:
        samples=dataset['images'];ids={s['id'] for s in samples}
    records=[{**s,'sample_id':s['id']} for s in samples]
    receipt=slice_receipt(records,predicate);selected={s['sample_id'] for s in receipt['selected']}
    if not selected:raise ValueError('empty population has no benchmark score')
    prediction_ids=[p['sample_id'] for p in predictions]
    if len(set(prediction_ids))!=len(prediction_ids) or set(prediction_ids)!=ids:
        raise ValueError('image-population slicing requires complete canonical per-image predictions, including empty images')
    filtered=[p for p in predictions if p['sample_id'] in selected]
    if task=='hbb':
        derived['splits']={split:{**dataset['splits'][split],'sample_ids':[s for s in dataset['splits'][split]['sample_ids'] if s in selected]}}
        derived['samples']=[s for s in samples if s['id'] in selected]
    elif task=='obb':derived['samples']=[s for s in samples if s['id'] in selected]
    else:
        derived['images']=[s for s in samples if s['id'] in selected]
        derived['annotations']=[a for a in dataset['annotations'] if a['sample_id'] in selected]
    receipt.update(task=task,scope='whole_images',source_dataset_sha256=digest(dataset),derived_dataset_sha256=digest(derived),prediction_sha256=digest(predictions))
    return derived,filtered,receipt
