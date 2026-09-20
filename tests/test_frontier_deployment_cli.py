import json
from dataclasses import replace
import pytest
np = pytest.importorskip("numpy")
from cvsubstrate.deployment.profiles import DetectorProfile,preprocess_image,decode_outputs
from cvsubstrate.cli_frontier import main
from cvsubstrate.provenance.io import write_json

def test_ul_profile_preserves_geometry_and_has_one_nms():
    p=DetectorProfile('ultralytics_raw',1,{'0':7},8,8)
    x,t=preprocess_image(np.zeros((4,8,3),np.uint8),p);assert x.shape==(1,3,8,8) and t['top']==2
    raw=np.asarray([[[4,4],[4,4],[4,4],[2,2],[.9,.8]]],np.float32)
    out=decode_outputs({'output0':raw},p,[t])[0]
    assert len(out['boxes'])==1 and out['boxes'][0]==[2.,1.,6.,3.] and out['category_ids']==[7]
    assert out['audit']['postprocess_nms']

def test_rfdetr_global_query_class_pairs_not_argmax():
    p=DetectorProfile('rfdetr',2,{'0':3,'1':7},8,8,resize='stretch',max_detections=2)
    _,t=preprocess_image(np.zeros((4,4,3),np.uint8),p)
    logits=np.array([[[5.,4.,-10.]]]);boxes=np.array([[[.5,.5,.5,.5]]])
    out=decode_outputs({'pred_logits':logits,'pred_boxes':boxes},p,[t])[0]
    assert out['category_ids']==[3,7] and out['boxes'][0]==[1.,1.,3.,3.]
    assert not out['audit']['postprocess_nms']

def test_mm_profile_padding_clipping_and_contract_rejection():
    p=DetectorProfile('mmdet_end2end',1,{'0':1},8,8)
    _,t=preprocess_image(np.zeros((8,8,3),np.uint8),p)
    out=decode_outputs({'dets':np.array([[[-1,1,3,4,.9],[0,0,0,0,0]]]),'labels':np.array([[0,-1]])},p,[t])[0]
    assert out['boxes']==[[0.,1.,3.,4.]] and out['audit']['clipped_to_original_image']==1
    with pytest.raises(ValueError):decode_outputs({'wrong':np.zeros((1,2,5))},p,[t])
    with pytest.raises(ValueError):replace(p,category_map={'0':0,'1':1}).validate()
    with pytest.raises(ValueError):preprocess_image(np.zeros((8,8,3),np.float32),p)

def test_cli_registry_and_recipes(tmp_path,capsys):
    assert main(['research-registry','init',str(tmp_path/'registry')])==0
    assert main(['research-registry','verify',str(tmp_path/'registry')])==0
    assert main(['adapter-recipes','list'])==0
    assert main(['adapter-recipes','show','sam2'])==0
    assert main(['adapter-recipes','scaffold',str(tmp_path/'adapter')])==0
    assert (tmp_path/'adapter/example_cvrs_adapter/adapter.py').is_file()
    assert main(['research-registry','verify',str(tmp_path/'missing')])==2

def test_cli_stream_plan_and_profile(tmp_path,capsys):
    write_json(tmp_path/'spec.json',{'raster':'x','raster_sha256':'a'*64,'model_identity':'fixture','tile_width':32,'tile_height':32,'overlap':4})
    assert main(['stream','plan',str(tmp_path/'spec.json'),'--width','100','--height','100'])==0
    write_json(tmp_path/'p.json',{'family':'rfdetr','class_count':1,'category_map':{'0':1},'input_height':64,'input_width':64})
    assert main(['detector-deploy','profile',str(tmp_path/'p.json')])==0

def test_quantization_rejects_locked_calibration_without_loading_model():
    from cvsubstrate.contracts.frontier import QuantizationSpec
    with pytest.raises(ValueError):QuantizationSpec(backend='onnxruntime',model_path='x',model_sha256='a'*64,calibration=[{'id':'c','path':'x.npz','sha256':'b'*64,'split_role':'locked_test'}],dataset_sha256='c'*64,preprocessing_sha256='d'*64,input_names=['images'])


def test_ul_end2end_does_not_apply_a_second_nms():
    p=DetectorProfile('ultralytics_end2end',1,{'0':7},8,8)
    _,t=preprocess_image(np.zeros((8,8,3),np.uint8),p)
    raw=np.array([[[1,1,4,4,.9,0],[1,1,4,4,.8,0]]],np.float32)
    out=decode_outputs({'output0':raw},p,[t])[0]
    assert len(out['boxes'])==2 and not out['audit']['postprocess_nms']

def test_calibration_uses_same_preprocessing_and_records_selection(tmp_path):
    pytest.importorskip('PIL')
    from PIL import Image
    from cvsubstrate.deployment.calibration import prepare_calibration
    from cvsubstrate.provenance.io import file_digest,read_json
    from cvsubstrate.provenance.artifact_set import verify_directory
    model=tmp_path/'model.onnx';model.write_bytes(b'not an executed ONNX model; calibration fixture only')
    image=tmp_path/'image.png';Image.fromarray(np.zeros((4,8,3),np.uint8)).save(image)
    spec={'profile':{'family':'ultralytics_raw','class_count':1,'category_map':{'0':0},'input_height':8,'input_width':8},'model_path':str(model),'model_sha256':file_digest(model),'dataset_sha256':'a'*64,'images':[{'id':'sample','path':str(image),'sha256':file_digest(image),'split_role':'train'}]}
    result=prepare_calibration(spec,tmp_path/'cal');assert result['items']==1
    q=read_json(tmp_path/'cal/quantization.json')
    with np.load(q['calibration'][0]['path'],allow_pickle=False) as data:assert data['images'].shape==(1,3,8,8)
    assert verify_directory(tmp_path/'cal')['status']=='VERIFIED'
    spec['images'][0]['split_role']='locked_test'
    with pytest.raises(ValueError):prepare_calibration(spec,tmp_path/'illegal')

