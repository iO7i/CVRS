"""Generate reproducible PNG software fixtures using only the standard library.

The colored rectangles are known test geometry, NOT simulated realistic vehicles.
Source labels named real/synthetic exercise accounting only; every fixture is generated.
"""
from pathlib import Path
import random
import struct
import zlib
from cvsubstrate.contracts.models import Box, Category, DatasetManifest, EvaluationProtocol, ExperimentSpec, LicenseInfo, Sample, Split, TrainingSpec
from cvsubstrate.provenance.io import atomic_bytes, digest, file_digest, write_json

def _png(width, height, rgb):

    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 4294967295)
    rows = b''.join((b'\x00' + rgb[y * width * 3:(y + 1) * width * 3] for y in range(height)))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b'')

def generate(destination: Path) -> dict:
    dest = Path(destination)
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError('fixture destination must be absent or empty')
    dest.mkdir(parents=True, exist_ok=True)
    rng = random.Random(271828)
    samples = []
    sizes = [(64, 64), (80, 64), (64, 80), (72, 64), (64, 72), (80, 80), (64, 64), (72, 80), (80, 64), (64, 80), (72, 72), (64, 64)]
    for idx, (width, height) in enumerate(sizes):
        pixels = bytearray((rng.randrange(25, 70) for _ in range(width * height * 3)))
        annotations = []
        if idx not in {3, 9}:
            xyxy = [0.0, 0.0, 12.0, 10.0] if idx == 2 else [float(5 + idx % 4), float(7 + idx % 5), float(20 + idx % 4), float(19 + idx % 5)]
            cat = 3 if idx % 2 == 0 else 17
            annotations.append(Box(xyxy=xyxy, category_id=cat))
            x1, y1, x2, y2 = map(int, xyxy)
            for y in range(y1, y2):
                for x in range(x1, x2):
                    off = (y * width + x) * 3
                    pixels[off:off + 3] = bytes((190, 120, 80) if cat == 3 else (80, 150, 210))
        path = dest / 'images' / f'fixture-{idx:02}.png'
        atomic_bytes(path, _png(width, height, bytes(pixels)))
        samples.append(Sample(id=f'fixture-{idx:02}', image=path.relative_to(dest).as_posix(), sha256=file_digest(path), width=width, height=height, source_kind='real' if idx < 4 or idx >= 8 else 'synthetic', domain='fixture-arid' if idx % 2 == 0 else 'fixture-nonarid', lineage_group=f'independent-fixture-{idx}', boxes=annotations))
    m = DatasetManifest(name='geometry-accounting-fixtures', version='1', categories=[Category(id=3, name='fixture-a'), Category(id=17, name='fixture-b')], samples=samples, splits={'train': Split(role='train', sample_ids=[s.id for s in samples[:8]]), 'dev': Split(role='dev', sample_ids=[s.id for s in samples[8:]])}, licenses=LicenseInfo(data='original generated software fixtures; project licensing pending', annotations='same', redistribution='unknown'), purpose='software_fixture', notes='All images are procedural fixtures. real/synthetic are MOCK accounting tags, not actual image provenance.')
    write_json(dest / 'dataset.json', m)
    for arm, name in [('R', 'real'), ('S', 'synthetic'), ('R+S', 'supplement'), ('S->R', 'pretrain')]:
        spec = ExperimentSpec(name=f'cpu-fixture-{name}', dataset='dataset.json', dataset_sha256=digest(m), training=TrainingSpec(arm=arm, updates=2, pretrain_updates=2), evaluation=EvaluationProtocol(evaluator='diagnostic_detection', evaluator_version='1', iou_thresholds=[0.5], score_threshold=0.05), notes='Execution/accounting test only; diagnostic fixed-threshold metrics are NOT COCO AP.')
        write_json(dest / f'{name}.json', spec)
    coco_spec = ExperimentSpec.model_validate({**spec.model_dump(mode='json'), 'name': 'cpu-fixture-coco', 'training': TrainingSpec(arm='R', updates=2).model_dump(mode='json'), 'evaluation': EvaluationProtocol().model_dump(mode='json'), 'notes': 'Requires explicitly installed pycocotools==2.0.11. No diagnostic fallback.'})
    write_json(dest / 'coco.json', coco_spec)
    return {'dataset': str(dest / 'dataset.json'), 'experiments': ['real.json', 'synthetic.json', 'supplement.json', 'pretrain.json', 'coco.json'], 'warning': 'Procedural geometry fixtures; NOT real images or scientific evidence.'}
