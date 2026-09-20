"""Analytical Slice4 conformance, not pretrained model evidence."""
import pytest
np = pytest.importorskip("numpy")
from cvsubstrate.contracts.frontier import *
from cvsubstrate.vision.masks import *
from cvsubstrate.vision.grounding import map_grounded,cross_paradigm_report
from cvsubstrate.vision.evaluation import mask_reference_payload

@pytest.mark.parametrize('h,w',[(1,1),(1,7),(4,3),(13,17)])
@pytest.mark.parametrize('seed',[0,1,9])
def test_mask_rle_roundtrip(h,w,seed):
    a=np.random.default_rng(seed).integers(0,2,(h,w),dtype=np.uint8)
    b=np.random.default_rng(seed+5).integers(0,2,(h,w),dtype=np.uint8)
    ra,rb=encode_mask(a),encode_mask(b)
    assert np.array_equal(a,decode_mask(ra));assert mask_area(ra)==int(a.sum())
    assert mask_intersection(ra,rb)==int((a & b).sum())
    u=int((a | b).sum());assert mask_iou(ra,rb)==(int((a&b).sum())/u if u else 1.0)

def test_rle_bad_counts_budget():
    with pytest.raises(ValueError):MaskRLE(width=2,height=2,counts=[1,2])
    with pytest.raises(ValueError):MaskRLE(width=2,height=2,counts=[0,0,4])
    with pytest.raises(ValueError):decode_mask(MaskRLE(width=100,height=100,counts=[10000]),max_pixels=3)
    with pytest.raises(ValueError):encode_mask(np.full((3,3),0.1))

def test_mask_transforms_and_tracked_merge():
    a=np.array([[1,0],[0,0]],np.uint8);m=encode_mask(a)
    out=transform_mask(m,output_size=[4,4],flip_horizontal=True)
    assert np.array_equal(decode_mask(out),np.array([[0,0,1,1],[0,0,1,1],[0,0,0,0],[0,0,0,0]]))
    placed=paste_mask(m,width=4,height=3,x=1,y=1);assert decode_mask(placed)[1,1]
    merged=merge_mask_tiles([{'instance_id':'x','mask':m.model_dump(),'x':0,'y':0},{'instance_id':'x','mask':m.model_dump(),'x':1,'y':0}],width=4,height=3)
    assert mask_area(merged['x'])==2
    with pytest.raises(ValueError):paste_mask(m,width=1,height=1,x=0,y=0)

def test_mask_selection_no_oracle_best():
    right=encode_mask(np.eye(3,dtype=np.uint8));wrong=encode_mask(np.zeros((3,3),np.uint8))
    prompt=PromptSpec(id='p',sample_id='a',kind='points',points=[[1.,1.]],point_labels=[1],source='ground_truth_oracle')
    pred=MaskPrediction(sample_id='a',width=3,height=3,prompts=[prompt],instances=[MaskInstance(id='right',mask=right,score=.1,prompt_id='p'),MaskInstance(id='wrong',mask=wrong,score=.9,prompt_id='p')])
    gt=MaskAnnotation(sample_id='a',instance_id='gt',mask=right)
    v=evaluate_prompt_masks([pred],[gt],[{'sample_id':'a','prompt_id':'p','instance_id':'gt'}])
    assert v['mean_iou']==0 and v['oracle_conditioned'] and not v['official_coco_ap']

def test_grounding_mapping_and_oracle_report():
    prompt=PromptSpec(id='p',sample_id='a',kind='text',text='small car.',source='fixed_protocol')
    p=GroundedPrediction(sample_id='a',width=8,height=8,prompt=prompt,boxes=[[1.,1.,3.,4.]],scores=[.9],phrases=['small car'])
    result,audit=map_grounded(p,{'small car':7});assert result.category_ids==[7] and audit['input_detections']==audit['output_detections']
    with pytest.raises(ValueError):map_grounded(p,{'car':7})
    row={k:'a'*64 for k in ['dataset_sha256','split_sha256','taxonomy_sha256','evaluator_sha256','preprocessing_sha256']}
    row.update(id='a',evaluation_task='hbb',oracle_prompt=False)
    v=cross_paradigm_report([row,{**row,'id':'b','oracle_prompt':True}]);assert v['comparisons'][0]['scientific_use']=='DESCRIPTIVE_ONLY'
    assert cross_paradigm_report([row,{**row,'id':'c','evaluation_task':'mask'}])['comparisons'][0]['metric_comparability']=='INCOMPARABLE'

@pytest.mark.parametrize('bad',[{'id':'../a','path':'x','sha256':'a'*64},{'id':'a','path':'x','sha256':'a'*64,'split_role':'locked_test'}])
def test_vision_image_guards(bad):
    with pytest.raises(ValueError):VisionJob(backend='sam_hf',model_dir='model',model_files={'config.json':'a'*64},images=[bad])

def test_mask_reference_crowd_universe_prompt_policy():
    mask=encode_mask(np.ones((2,3),np.uint8));pred=MaskPrediction(sample_id='x',width=3,height=2,instances=[MaskInstance(id='i',mask=mask,score=.7,category_id=3)])
    gt=MaskAnnotation(sample_id='x',instance_id='g',mask=mask,category_id=3,iscrowd=True)
    req,p=mask_reference_payload([{'id':'x','width':3,'height':2}],[gt.model_dump()],[pred.model_dump()],[{'id':3,'name':'vehicle'}],{})
    assert req['operation']=='evaluate_masks' and req['ground_truth']['annotations'][0]['iscrowd']==1
    assert req['detections'][0]['segmentation']['counts']==[0,6]
    with pytest.raises(ValueError):mask_reference_payload([{'id':'y','width':3,'height':2}],[gt.model_dump()],[pred.model_dump()],[{'id':3,'name':'vehicle'}],{})


def test_mask_predicted_iou_is_not_a_calibrated_probability():
    from cvsubstrate.contracts.frontier import MaskInstance
    item={'id':'mask','mask':{'width':1,'height':1,'counts':[0,1]},'score':1.1,'score_kind':'predicted_iou'}
    assert MaskInstance.model_validate(item).score==1.1
    with pytest.raises(ValueError):MaskInstance.model_validate({**item,'score_kind':'detection_confidence'})

def test_plugin_scaffold_has_valid_descriptor_and_no_arg_factory(tmp_path):
    import importlib.util
    from cvsubstrate.adapters.recipes import scaffold_vision_adapter
    from cvsubstrate.contracts.groundwork import PluginDescriptor
    from cvsubstrate.provenance.io import read_json
    out=tmp_path/'adapter';scaffold_vision_adapter(out)
    d=PluginDescriptor.model_validate(read_json(out/'plugin.json'))
    assert d.operations==['validate','predict'] and not d.trust_code
    spec=importlib.util.spec_from_file_location('isolated_external_fixture',out/'example_cvrs_adapter/adapter.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    p=module.LocalVisionAdapter();assert p.capabilities()['input_formats']==['VisionJob/1']
    with pytest.raises(ValueError):p.validate({'job':{}})

