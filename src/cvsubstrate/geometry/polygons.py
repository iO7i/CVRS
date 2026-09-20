"""Convex polygon and rotated-rectangle geometry in image coordinates.

x right, y down. Positive shoelace area is clockwise on an image. The canonical
start is lexicographically smallest (x,y). Polygon conversion preserves geometry,
not the original vertex ordering. No +1 pixel convention is introduced.
"""
from __future__ import annotations
import math
from typing import Sequence

EPS = 1e-10


def _point(p):
    if len(p) != 2 or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in p):
        raise ValueError('points require two finite numeric coordinates')
    return [float(p[0]), float(p[1])]


def cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def signed_area(points):
    if len(points) < 3:
        return 0.0
    # Translate before summing: better accuracy for large world coordinates.
    x0, y0 = points[0]
    return 0.5 * math.fsum((a[0]-x0)*(b[1]-y0)-(b[0]-x0)*(a[1]-y0)
        for a, b in zip(points, points[1:] + points[:1]))


def canonical_polygon(points: Sequence[Sequence[float]]) -> list[list[float]]:
    p = [_point(x) for x in points]
    if len(p) < 3 or len(set(map(tuple, p))) != len(p):
        raise ValueError('a polygon needs >=3 unique vertices, with no repeated closing point')
    span = max(max(x[0] for x in p)-min(x[0] for x in p), max(x[1] for x in p)-min(x[1] for x in p))
    tol = EPS * max(span * span, 1e-12)
    turns = [cross(p[i-1], p[i], p[(i+1) % len(p)]) for i in range(len(p))]
    if any(abs(t) <= tol for t in turns) or not (all(t > 0 for t in turns) or all(t < 0 for t in turns)):
        raise ValueError('polygon must be ordered, strictly convex and nondegenerate')
    # Consistent turns do not exclude multiply-wound polygons; verify all points
    # lie in every directed edge half-plane as well.
    sign = 1 if turns[0] > 0 else -1
    for a, b in zip(p, p[1:] + p[:1]):
        if any(sign * cross(a, b, c) < -tol for c in p):
            raise ValueError('self-crossing or unordered polygon')
    if signed_area(p) < 0:
        p.reverse()
    start = min(range(len(p)), key=lambda i: (p[i][0], p[i][1]))
    return p[start:] + p[:start]


def polygon_area(points):
    return abs(signed_area(canonical_polygon(points)))


def rbox_to_polygon(cx, cy, width, height, angle, *, unit='radians', positive='clockwise'):
    values = [cx, cy, width, height, angle]
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
        raise ValueError('rotated box values must be finite numbers')
    if min(width, height) <= 0 or unit not in {'radians', 'degrees'} or positive not in {'clockwise', 'counterclockwise'}:
        raise ValueError('invalid extent or undeclared angle convention')
    t = math.radians(angle) if unit == 'degrees' else angle
    if positive == 'counterclockwise':
        t = -t
    c, s = math.cos(t), math.sin(t)
    return canonical_polygon([[cx+c*x-s*y, cy+s*x+c*y] for x,y in
        [(-width/2,-height/2), (width/2,-height/2), (width/2,height/2), (-width/2,height/2)]])


def polygon_to_rbox(points, *, convention='le90', tolerance=1e-7):
    """Convert a genuine rectangle only. A generic quadrilateral is NOT a rbox.

    le90: long edge width >= height; clockwise radians in [-pi/2,pi/2).
    le135: long edge width >= height; clockwise radians in [-pi/4,3*pi/4).
    oc_positive: width-edge angle in (0,pi/2], swapping sides as needed.
    oc_negative: explicitly named legacy negative angle [-pi/2,0).
    """
    p = canonical_polygon(points)
    if len(p) != 4 or not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('four rectangle vertices and positive tolerance required')
    edges = [[p[(i+1)%4][j]-p[i][j] for j in (0,1)] for i in range(4)]
    lens = [math.hypot(*v) for v in edges]
    scale = max(lens)
    for i in range(4):
        dot = sum(a*b for a,b in zip(edges[i], edges[(i+1)%4]))
        if abs(dot) > tolerance * lens[i] * lens[(i+1)%4]:
            raise ValueError('nonrectangular polygon: preserve the polygon instead')
    if any(abs(lens[i]-lens[i+2]) > tolerance*scale for i in (0,1)):
        raise ValueError('opposite rectangle sides disagree')
    w,h = lens[:2]
    t = math.atan2(edges[0][1], edges[0][0])
    if convention in {'le90','le135'}:
        if h > w + tolerance*scale:
            w,h = h,w
            t += math.pi/2
        low = -math.pi/2 if convention == 'le90' else -math.pi/4
        t = (t-low) % math.pi + low
    elif convention in {'oc_positive','oc_negative'}:
        # Choose a width edge in the specified half-quadrant. This intentionally
        # does not pretend all OpenCV versions share a single convention.
        t = t % math.pi
        if t > math.pi/2:
            t -= math.pi/2
            w,h = h,w
        if abs(t) < 1e-12:
            t = math.pi/2
            w,h = h,w
        if convention == 'oc_negative':
            t -= math.pi/2
            w,h = h,w
            if abs(t) < 1e-12:
                t = -math.pi/2
                w,h = h,w
    else:
        raise ValueError('unknown explicit angle convention')
    return {'cx': sum(v[0] for v in p)/4, 'cy': sum(v[1] for v in p)/4,
            'width': w, 'height': h, 'angle': t, 'unit': 'radians',
            'positive': 'clockwise', 'convention': convention}


def transform_polygon(points, affine):
    if len(affine) != 6 or not all(math.isfinite(v) for v in affine):
        raise ValueError('expected six finite affine coefficients')
    a,b,c,d,e,f = affine
    return canonical_polygon([[a*x+b*y+c, d*x+e*y+f] for x,y in canonical_polygon(points)])


def _intersection_polygon(subject, clip):
    out = canonical_polygon(subject)
    boundary = canonical_polygon(clip)
    for a,b in zip(boundary, boundary[1:]+boundary[:1]):
        incoming, out = out, []
        if not incoming:
            break
        s = incoming[-1]
        ds = cross(a,b,s)
        for e in incoming:
            de = cross(a,b,e)
            sin, ein = ds >= -1e-12, de >= -1e-12
            if sin != ein:
                denom = ds-de
                if abs(denom) > 1e-30:
                    t = ds/denom
                    out.append([s[0]+t*(e[0]-s[0]), s[1]+t*(e[1]-s[1])])
            if ein:
                out.append(e)
            s,ds = e,de
    return out


def polygon_iou(a, b):
    """Local diagnostic convex IoU. NOT official DOTA/MMCV evaluator parity."""
    aa,bb = canonical_polygon(a),canonical_polygon(b)
    inter = abs(signed_area(_intersection_polygon(aa,bb)))
    area_a,area_b = abs(signed_area(aa)),abs(signed_area(bb))
    inter = min(max(inter, 0.0),area_a,area_b)
    return inter/(area_a+area_b-inter)


def polygon_nms(polygons, scores, categories, threshold=0.5):
    if not 0 <= threshold <= 1 or not len(polygons)==len(scores)==len(categories):
        raise ValueError('invalid NMS arrays or threshold')
    p = [canonical_polygon(x) for x in polygons]
    if any(not math.isfinite(s) or not 0 <= s <= 1 for s in scores):
        raise ValueError('scores must be finite in [0,1]')
    kept, suppressed = [], []
    for i in sorted(range(len(p)), key=lambda k: (-scores[k],k)):
        parent = next((j for j in kept if categories[i]==categories[j] and polygon_iou(p[i],p[j])>threshold), None)
        if parent is None:
            kept.append(i)
        else:
            suppressed.append({'index': i, 'kept_index': parent})
    return {'kept_indices': kept, 'suppressed': suppressed,
            'semantics': 'class-aware diagnostic polygon NMS, suppress IoU > threshold; stable original-index tie-break'}
