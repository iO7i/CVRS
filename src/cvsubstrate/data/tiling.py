"""Dependency-free HBB crop/resize/padding geometry. Not an OBB/CRS implementation."""
from dataclasses import dataclass
import math
from cvsubstrate.errors import CVRSError

@dataclass(frozen=True)
class TileTransform:
    source_width: int
    source_height: int
    x: int
    y: int
    width: int
    height: int
    scale_x: float = 1.0
    scale_y: float = 1.0
    pad_left: float = 0.0
    pad_top: float = 0.0

    def __post_init__(self):
        if min(self.source_width, self.source_height, self.width, self.height) <= 0:
            raise ValueError('positive dimensions required')
        if self.x < 0 or self.y < 0 or self.x + self.width > self.source_width or (self.y + self.height > self.source_height):
            raise ValueError('tile outside original image')
        if not all((math.isfinite(v) for v in (self.scale_x, self.scale_y, self.pad_left, self.pad_top))):
            raise ValueError('nonfinite transform')
        if min(self.scale_x, self.scale_y) <= 0 or min(self.pad_left, self.pad_top) < 0:
            raise ValueError('scale must be positive and padding nonnegative')

    def to_tile(self, box):
        x1, y1, x2, y2 = box
        if not (self.x <= x1 < x2 <= self.x + self.width and self.y <= y1 < y2 <= self.y + self.height):
            raise ValueError('forward mapping requires a box contained in the tile; no implicit clipping')
        return [(x1 - self.x) * self.scale_x + self.pad_left, (y1 - self.y) * self.scale_y + self.pad_top, (x2 - self.x) * self.scale_x + self.pad_left, (y2 - self.y) * self.scale_y + self.pad_top]

    def to_source(self, box):
        if len(box) != 4 or not all((math.isfinite(v) for v in box)):
            raise ValueError('invalid tile box')
        x1, y1, x2, y2 = box
        if x2 <= x1 or y2 <= y1:
            raise ValueError('degenerate tile box')
        out = [(x1 - self.pad_left) / self.scale_x + self.x, (y1 - self.pad_top) / self.scale_y + self.y, (x2 - self.pad_left) / self.scale_x + self.x, (y2 - self.pad_top) / self.scale_y + self.y]
        if out[0] < self.x - 1e-08 or out[1] < self.y - 1e-08 or out[2] > self.x + self.width + 1e-08 or (out[3] > self.y + self.height + 1e-08):
            raise CVRSError('PADDING_PREDICTION', 'box enters padding/outside valid crop; choose an explicit clipping policy upstream')
        return out

def tiles(width: int, height: int, tile_size: int, overlap: int):
    if min(width, height, tile_size) <= 0 or not 0 <= overlap < tile_size:
        raise ValueError('invalid tiling parameters')

    def offsets(n):
        if n <= tile_size:
            return [0]
        values = list(range(0, n - tile_size + 1, tile_size - overlap))
        if values[-1] != n - tile_size:
            values.append(n - tile_size)
        return values
    return [TileTransform(width, height, x, y, min(tile_size, width), min(tile_size, height)) for y in offsets(height) for x in offsets(width)]

def iou(a, b):
    intersection = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    aa = (a[2] - a[0]) * (a[3] - a[1])
    bb = (b[2] - b[0]) * (b[3] - b[1])
    return intersection / (aa + bb - intersection) if aa + bb - intersection > 0 else 0.0

def merge_hbb(boxes, scores, categories, threshold=0.5):
    """Class-aware greedy NMS, stable input-order tiebreak, suppress IoU > threshold.

    Input must already be mapped to original-image coordinates. Utility output is
    NOT evidence that model runner integrated tiling has been certified.
    """
    if not 0 <= threshold <= 1:
        raise ValueError('invalid merge threshold')
    if not len(boxes) == len(scores) == len(categories):
        raise ValueError('mismatched arrays')
    from cvsubstrate.contracts.models import Box
    for b, s, c in zip(boxes, scores, categories):
        Box(xyxy=b, category_id=c)
        if not math.isfinite(s) or not 0 <= s <= 1:
            raise ValueError('invalid score')
    order = sorted(range(len(boxes)), key=lambda i: (-scores[i], i))
    kept = []
    for index in order:
        if all((categories[index] != categories[k] or iou(boxes[index], boxes[k]) <= threshold for k in kept)):
            kept.append(index)
    return ([boxes[k] for k in kept], [scores[k] for k in kept], [categories[k] for k in kept])
