"""Python >=3.8 native rich-interchange worker, without controller imports.

This calls real SDKs only on explicitly trusted requests. It does not download
models, launch the browser UI, or copy media. FiftyOne may start its local DB.
"""
from pathlib import Path
import copy
import importlib.metadata
import json
from runtime_common import main, read, write, check_file


def supervision_payload(payload):
    import numpy as np
    import supervision as sv
    try:
        from supervision.config import ORIENTED_BOX_COORDINATES
    except ImportError:
        ORIENTED_BOX_COORDINATES = 'xyxyxyxy'
    result = copy.deepcopy(payload)
    for row in result['records']:
        n = len(row['xyxy'])
        data = {'cvrs_object_id': np.array([m['id'] for m in row['cvrs_objects']], dtype=str)}
        if row.get('xyxyxyxy') is not None:
            data[ORIENTED_BOX_COORDINATES] = np.asarray(row['xyxyxyxy'], dtype=float).reshape(-1, 4, 2)
        d = sv.Detections(xyxy=np.asarray(row['xyxy'], dtype=float).reshape(-1, 4),
            confidence=np.asarray(row['confidence'], dtype=float),
            class_id=np.asarray(row['class_id'], dtype=int),
            mask=np.asarray(row['mask'], dtype=bool).reshape(n, row['height'], row['width']) if row.get('mask') is not None else None,
            data=data)
        row['xyxy'] = d.xyxy.tolist()
        row['confidence'] = d.confidence.tolist()
        row['class_id'] = d.class_id.tolist()
        row['mask'] = d.mask.astype('uint8').tolist() if d.mask is not None else None
        row['xyxyxyxy'] = d.data[ORIENTED_BOX_COORDINATES].tolist() if ORIENTED_BOX_COORDINATES in d.data else None
    return result


def native_label(item):
    import fiftyone as fo
    import numpy as np
    common = dict(label=item['label'], confidence=item['confidence'], cvrs=item['cvrs'])
    if item['kind'] == 'polyline':
        return fo.Polyline(points=item['points'], closed=item['closed'], filled=item['filled'], **common)
    return fo.Detection(bounding_box=item['bounding_box'],
        mask=np.asarray(item['mask'], dtype=bool) if item.get('mask') is not None else None,
        cvrs_mask_window=item.get('cvrs_mask_window'), **common)


def label_payload(label, kind):
    result = {'kind': kind, 'label': label.label, 'confidence': float(label.confidence), 'cvrs': dict(label['cvrs'])}
    if kind == 'polyline':
        result.update(points=label.points, closed=label.closed, filled=label.filled)
    else:
        result['bounding_box'] = label.bounding_box
        if label.mask is not None:
            result['mask'] = label.mask.astype('uint8').tolist()
            result['cvrs_mask_window'] = label['cvrs_mask_window']
    return result


def serialize_dataset(ds, metadata):
    result = copy.deepcopy(metadata)
    result['records'] = []
    for sample in ds:
        base = dict(sample['cvrs_frame'])
        labels = []
        try:
            predictions = sample['cvrs_detections']
        except KeyError:
            predictions = None
        try:
            polygons = sample['cvrs_polylines']
        except KeyError:
            polygons = None
        if predictions:
            labels += [label_payload(d, 'detection') for d in predictions.detections]
        if polygons:
            labels += [label_payload(d, 'polyline') for d in polygons.polylines]
        order = {ident: i for i, ident in enumerate(base.pop('object_order', []))}
        labels.sort(key=lambda x: order.get(x['cvrs']['id'], len(order)))
        base['labels'] = labels
        result['records'].append(base)
    return result


def handle(req):
    from ecosystem_worker import local_only
    local_only()
    out = Path(req['output_dir'])
    out.mkdir(parents=True, exist_ok=True)
    p = req['payload']
    if not p.get('trust_code'):
        raise ValueError('TRUST_REQUIRED: native SDK code must be explicitly authorized')
    target = p['target']
    if target == 'supervision':
        value = read(p['input'])
        check_file(p['input'], p['input_sha256'])
        result = supervision_payload(value)
    elif target == 'fiftyone':
        import fiftyone as fo
        if p.get('dataset_name'):
            ds = fo.load_dataset(p['dataset_name'])
            metadata = ds.info.get('cvrs_interchange')
            if not metadata:
                raise ValueError('Native dataset needs explicit CVRS frame/taxonomy metadata; no identity is guessed')
            result = serialize_dataset(ds, metadata)
        else:
            value = read(p['input'])
            check_file(p['input'], p['input_sha256'])
            ds = fo.Dataset()
            ds.persistent = False
            try:
                metadata = {k:v for k,v in value.items() if k != 'records'}
                ds.info['cvrs_interchange'] = metadata
                ds.save()
                for row in value['records']:
                    if not row.get('image') or not row.get('image_sha256'):
                        raise ValueError('FiftyOne native export requires explicit existing image paths and hashes')
                    check_file(row['image'], row['image_sha256'])
                    sample = fo.Sample(filepath=row['image'], metadata=fo.ImageMetadata(width=row['width'], height=row['height']))
                    frame = {k:v for k,v in row.items() if k != 'labels'}
                    frame['object_order'] = [o['cvrs']['id'] for o in row['labels']]
                    sample['cvrs_frame'] = frame
                    sample['cvrs_detections'] = fo.Detections(detections=[native_label(x) for x in row['labels'] if x['kind']=='detection'])
                    sample['cvrs_polylines'] = fo.Polylines(polylines=[native_label(x) for x in row['labels'] if x['kind']=='polyline'])
                    ds.add_sample(sample)
                ds.export(export_dir=str(out/'fiftyone'), dataset_type=fo.types.FiftyOneDataset, export_media=False)
                result = serialize_dataset(ds, metadata)
            finally:
                ds.delete()  # Only the temporary dataset created in this call.
    else:
        raise ValueError('unsupported rich SDK target')
    write(out/'native-view.json', result)
    return {'target': target, 'version': importlib.metadata.version(target), 'records': len(result['records']),
            'native_execution': 'COMPLETED', 'media_copied': False, 'network': 'LOCAL_ONLY_GUARD_NOT_SANDBOX'}


if __name__ == '__main__':
    main(handle)
