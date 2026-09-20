import random
import pytest
from cvsubstrate.data.tiling import TileTransform, tiles, merge_hbb, iou
from cvsubstrate.errors import CVRSError

@pytest.mark.parametrize('seed', range(32))
def test_seeded_transform_roundtrip(seed):
    rng = random.Random(seed)
    for _ in range(30):
        x = rng.randrange(40)
        y = rng.randrange(40)
        w = rng.randrange(10, 60)
        h = rng.randrange(10, 60)
        t = TileTransform(100, 100, x, y, w, h, rng.uniform(0.2, 4), rng.uniform(0.2, 4), rng.uniform(0, 10), rng.uniform(0, 10))
        box = [float(x + 1), float(y + 1), float(x + w - 1), float(y + h - 1)]
        assert t.to_source(t.to_tile(box)) == pytest.approx(box, abs=1e-09)

@pytest.mark.parametrize('width,height,size,overlap', [(5, 5, 10, 2), (64, 80, 32, 8), (73, 91, 32, 0), (100, 100, 33, 32)])
def test_tiles_cover_every_pixel(width, height, size, overlap):
    result = tiles(width, height, size, overlap)
    for y in range(height):
        for x in range(width):
            assert any((t.x <= x < t.x + t.width and t.y <= y < t.y + t.height for t in result))

@pytest.mark.parametrize('args', [(10, 10, 0, 0), (10, 10, 8, 8), (10, 10, 8, -1), (0, 10, 8, 2)])
def test_invalid_tiling(args):
    with pytest.raises(ValueError):
        tiles(*args)

def test_padding_prediction_is_not_silently_clipped():
    t = TileTransform(100, 100, 10, 10, 20, 20, pad_left=5)
    with pytest.raises(CVRSError, match='padding'):
        t.to_source([0.0, 0.0, 10.0, 10.0])

def test_cross_tile_object_requires_explicit_crop():
    t = TileTransform(100, 100, 0, 0, 20, 20)
    with pytest.raises(ValueError):
        t.to_tile([15.0, 5.0, 25.0, 10.0])

def test_original_coordinate_merging():
    a = TileTransform(100, 100, 0, 0, 60, 60)
    b = TileTransform(100, 100, 40, 0, 60, 60)
    box = [45.0, 10.0, 55.0, 20.0]
    result = merge_hbb([a.to_source(a.to_tile(box)), b.to_source(b.to_tile(box))], [0.7, 0.8], [3, 3])
    assert result == ([box], [0.8], [3])

def test_nms_class_aware_and_stable_ties():
    boxes = [[0.0, 0.0, 10.0, 10.0]] * 3
    assert merge_hbb(boxes, [0.8, 0.8, 0.8], [3, 3, 17]) == ([boxes[0], boxes[2]], [0.8, 0.8], [3, 17])

def test_nms_empty():
    assert merge_hbb([], [], []) == ([], [], [])

def test_iou_analytic():
    assert iou([0.0, 0.0, 2.0, 2.0], [1.0, 0.0, 3.0, 2.0]) == pytest.approx(1 / 3)
    assert iou([0.0, 0.0, 1.0, 1.0], [1.0, 0.0, 2.0, 1.0]) == 0
