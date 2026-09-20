import math
import random
import pytest
from cvsubstrate.geometry.polygons import (canonical_polygon, rbox_to_polygon, polygon_to_rbox,
    polygon_area, polygon_iou, transform_polygon, polygon_nms)
from cvsubstrate.contracts.research import GeoReference, SyntheticObject, Quantity, CameraRecord
from cvsubstrate.geometry.geospatial import pixel_to_world, world_to_pixel, tile_reference

@pytest.mark.parametrize('seed',range(40))
def test_rbox_roundtrip_all_explicit_conventions(seed):
    rng=random.Random(seed)
    p=rbox_to_polygon(rng.uniform(-100,100),rng.uniform(-100,100),rng.uniform(.2,60),
        rng.uniform(.2,60),rng.uniform(-720,720),unit='degrees')
    for convention in ['le90','le135','oc_positive','oc_negative']:
        b=polygon_to_rbox(p,convention=convention)
        q=rbox_to_polygon(b['cx'],b['cy'],b['width'],b['height'],b['angle'])
        assert polygon_iou(p,q)==pytest.approx(1,abs=1e-8)
        if convention=='le90':assert -math.pi/2<=b['angle']<math.pi/2
        if convention=='le135':assert -math.pi/4<=b['angle']<3*math.pi/4
        if convention=='oc_positive':assert 0<b['angle']<=math.pi/2
        if convention=='oc_negative':assert -math.pi/2<=b['angle']<0

@pytest.mark.parametrize('angle',[0,90,180,270,-90,360])
def test_angle_boundaries(angle):
    p=rbox_to_polygon(0,0,4,2,angle,unit='degrees')
    for c in ['le90','le135','oc_positive','oc_negative']:
        b=polygon_to_rbox(p,convention=c)
        assert polygon_iou(p,rbox_to_polygon(b['cx'],b['cy'],b['width'],b['height'],b['angle']))==pytest.approx(1)

@pytest.mark.parametrize('p',[
 [[0,0],[1,1],[0,1],[1,0]], [[0,0],[1,0],[2,0],[0,1]],
 [[0,0],[1,0],[1,0],[0,1]], [[0,0],[1,0],[.1,.1],[0,1]],
 [[0,0],[float('nan'),0],[1,1],[0,1]]])
def test_invalid_polygon_is_rejected(p):
    with pytest.raises(ValueError):canonical_polygon(p)

def test_canonical_is_rotation_order_independent():
    p=[[3,4],[7,4],[7,9],[3,9]]
    for i in range(4):
        q=p[i:]+p[:i]
        assert canonical_polygon(q)==canonical_polygon(list(reversed(q)))==p

def test_nonuniform_scaling_preserves_polygon_not_fake_rectangle():
    p=rbox_to_polygon(10,10,4,2,35,unit='degrees')
    q=transform_polygon(p,[2,0,0,0,1,0])
    assert polygon_area(q)==pytest.approx(2*polygon_area(p))
    with pytest.raises(ValueError,match='nonrectangular'):polygon_to_rbox(q)

def test_iou_analytic_and_nms():
    p=rbox_to_polygon(1,1,2,2,0);q=rbox_to_polygon(2,1,2,2,0)
    assert polygon_iou(p,q)==pytest.approx(1/3)
    assert polygon_iou(p,rbox_to_polygon(9,9,2,2,0))==0
    r=polygon_nms([p,p,p],[.5,.5,.4],[1,1,2],.5)
    assert r['kept_indices']==[0,2] and r['suppressed']==[{'index':1,'kept_index':0}]

@pytest.mark.parametrize('seed',range(40))
def test_convex_iou_against_independent_shapely(seed):
    shapely=pytest.importorskip('shapely.geometry')
    rng=random.Random(100+seed)
    polygons=[rbox_to_polygon(rng.uniform(0,30),rng.uniform(0,30),rng.uniform(1,25),rng.uniform(1,25),rng.uniform(-math.pi,math.pi)) for _ in range(2)]
    a,b=map(shapely.Polygon,polygons)
    expected=a.intersection(b).area/a.union(b).area
    assert polygon_iou(*polygons)==pytest.approx(expected,abs=1e-8)
    assert polygon_iou(*polygons)==pytest.approx(polygon_iou(*reversed(polygons)),abs=1e-8)

@pytest.mark.parametrize('seed',range(20))
def test_affine_roundtrip_crop_resize_padding(seed):
    rng=random.Random(seed)
    geo=GeoReference(crs='EPSG:32637',affine=[.5,.03,500000.0,-.05,-.4,2500000.0])
    for center in [True,False]:
        x,y=rng.uniform(0,10000),rng.uniform(0,10000)
        w=pixel_to_world(geo,x,y,center=center)
        assert world_to_pixel(geo,*w,center=center)==pytest.approx([x,y],abs=1e-7)
    tiled=tile_reference(geo,100,200,2.0,3.0,4.0,5.0)
    assert pixel_to_world(tiled,44,65)==pytest.approx(pixel_to_world(geo,120,220))

def test_unknown_observation_never_becomes_zero():
    with pytest.raises(ValueError):Quantity(status='unknown',value=0)
    with pytest.raises(ValueError):Quantity(status='measured',value=2,unit='m')
    obj=SyntheticObject(object_id='car1',attributes={'occlusion_fraction':Quantity(status='unknown')})
    assert obj.attributes['occlusion_fraction'].value is None
    with pytest.raises(ValueError):
        SyntheticObject(object_id='car1',attributes={'occlusion_fraction':Quantity(status='simulator_reported',value=1.1,unit='fraction',method='mask area')})

def test_camera_matrix_conventions_required():
    with pytest.raises(ValueError):CameraRecord(camera_to_world=[[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.],[0.,0.,0.,1.]])
    with pytest.raises(ValueError):GeoReference(crs='EPSG:4326',affine=[1.,2.,3.,2.,4.,5.])
