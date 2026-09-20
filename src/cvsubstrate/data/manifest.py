"""Dataset validation and protected-split policy. Hashes are not quality certificates."""
from __future__ import annotations
import struct
from pathlib import Path
from cvsubstrate.contracts.models import DatasetManifest, ExperimentSpec, FinalTestAuthorization
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import digest, experiment_identity, file_digest, read_json, safe_join

def load_manifest(path: Path, check_files: bool=True) -> DatasetManifest:
    m = DatasetManifest.model_validate(read_json(path))
    validate_manifest(m, Path(path).parent, check_files=check_files)
    return m

def image_dimensions(path: Path) -> tuple[int, int]:
    """PNG/JPEG header dimensions without requiring a vision package in core."""
    with path.open('rb') as f:
        header = f.read(24)
        if header[:8] == b'\x89PNG\r\n\x1a\n' and header[12:16] == b'IHDR':
            return struct.unpack('>II', header[16:24])
        f.seek(0)
        if f.read(2) == b'\xff\xd8':
            while True:
                b = f.read(1)
                if not b:
                    break
                if b != b'\xff':
                    continue
                marker = f.read(1)
                while marker == b'\xff':
                    marker = f.read(1)
                if marker in (b'\xd8', b'\xd9'):
                    continue
                size_bytes = f.read(2)
                if len(size_bytes) != 2:
                    break
                size = int.from_bytes(size_bytes, 'big')
                if size < 2:
                    break
                if marker and marker[0] in {192, 193, 194, 195, 197, 198, 199, 201, 202, 203, 205, 206, 207}:
                    data = f.read(5)
                    if len(data) == 5:
                        return (int.from_bytes(data[3:5], 'big'), int.from_bytes(data[1:3], 'big'))
                f.seek(size - 2, 1)
    if path.suffix.lower() in {'.tif','.tiff'}:
        try:
            import rasterio
        except ImportError as exc:
            raise CVRSError('DEPENDENCY_UNAVAILABLE','TIFF dimensions require optional rasterio; core PNG/JPEG checks need no vision package') from exc
        with rasterio.open(path) as dataset:return dataset.width,dataset.height
    raise CVRSError('IMAGE_FORMAT', 'core header validation supports PNG/JPEG; TIFF needs the optional geo adapter')

def validate_manifest(m: DatasetManifest, root: Path | None=None, check_files: bool=True, *, allow_noncrowd_ignore: bool=False) -> dict:
    by_id = {s.id: s for s in m.samples}
    # Split memberships may not overlap, even if role names happen to match.
    membership: dict[str, str] = {}
    content_splits: dict[str, str] = {}
    groups: dict[str, str] = {}
    # A connected lineage component (including external parent IDs) cannot cross splits.
    parent: dict[str, str] = {}

    def find(x):
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(a, b):
        parent[find(a)] = find(b)
    for s in m.samples:
        find('sample:' + s.id)
        if s.lineage_group:
            union('sample:' + s.id, 'group:' + s.lineage_group)
        for p in s.parent_ids:
            union('sample:' + s.id, 'sample:' + p)
    for name, split in m.splits.items():
        for sid in split.sample_ids:
            if sid in membership:
                raise CVRSError('SPLIT_OVERLAP', f'{sid} appears in {membership[sid]} and {name}')
            membership[sid] = name
            s = by_id[sid]
            if s.sha256 in content_splits and content_splits[s.sha256] != name:
                raise CVRSError('CONTENT_LEAKAGE', 'identical image content crosses splits')
            content_splits[s.sha256] = name
            g = find('sample:' + sid)
            if g in groups and groups[g] != name:
                raise CVRSError('LINEAGE_LEAKAGE', 'declared parent/group lineage crosses splits')
            groups[g] = name
    for s in m.samples:
        for b in s.boxes:
            if b.ignore and (not b.iscrowd) and not allow_noncrowd_ignore:
                raise CVRSError('UNSUPPORTED_IGNORE', 'noncrowd ignore semantics are not implemented; annotations were not dropped')
        if check_files:
            if root is None:
                raise CVRSError('DATA_ROOT_REQUIRED', 'file validation requires a dataset root')
            p = safe_join(root, s.image)
            if not p.is_file():
                raise CVRSError('MISSING_IMAGE', f'missing declared image: {s.image}')
            if file_digest(p) != s.sha256:
                raise CVRSError('IMAGE_HASH', f'content mismatch: {s.image}')
            if image_dimensions(p) != (s.width, s.height):
                raise CVRSError('IMAGE_DIMENSIONS', f'wrong dimensions: {s.image}')
    return {'status': 'VALID', 'dataset_digest': digest(m), 'samples': len(m.samples), 'categories': len(m.categories), 'splits': {k: len(v.sample_ids) for k, v in m.splits.items()}, 'limits': 'Exact hashes and declared lineage only; near-duplicate and undeclared leakage are not ruled out.'}

def validate_experiment(spec: ExperimentSpec, m: DatasetManifest, authorization: dict | None=None) -> None:
    validate_manifest(m, check_files=False)
    if digest(m) != spec.dataset_sha256:
        raise CVRSError('DATASET_DIGEST', 'experiment dataset digest does not match')
    if spec.eval_split not in m.splits:
        raise CVRSError('UNKNOWN_SPLIT', 'evaluation split not found')
    if spec.training:
        if spec.train_split not in m.splits:
            raise CVRSError('UNKNOWN_SPLIT', 'training split not found')
        if m.splits[spec.train_split].role != 'train':
            raise CVRSError('TRAIN_ROLE', 'training requires an explicitly train-role split')
    role = m.splits[spec.eval_split].role
    if role == 'train':
        raise CVRSError('EVAL_ROLE', 'evaluation requires dev, selection, or explicitly authorized locked_test')
    if role == 'locked_test':
        if spec.training:
            raise CVRSError('LOCKED_TEST', 'a training run cannot access the locked test set')
        if authorization is None:
            raise CVRSError('LOCKED_TEST', 'explicit final-test authorization record required')
        auth = FinalTestAuthorization.model_validate(authorization)
        if auth.experiment_digest != experiment_identity(spec) or auth.dataset_digest != digest(m) or auth.split != spec.eval_split:
            raise CVRSError('AUTHORIZATION_MISMATCH', 'authorization does not cover this experiment/dataset/split')
    if spec.preprocessing != {'owner': 'worker', 'input': 'RGB uint8', 'controller_transforms': 'none', 'output_frame': 'original_image_xyxy'}:
        raise CVRSError('PREPROCESSING_UNSUPPORTED', 'only explicit worker-owned RGB preprocessing is supported')
    if spec.evaluation.tile_merge_policy != {'kind': 'none'}:
        raise CVRSError('TILING_RUNNER_UNSUPPORTED', 'use the dedicated run-tiled path for explicit tile materialization and source-coordinate merging')
