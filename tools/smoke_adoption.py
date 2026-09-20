"""A genuine no-rewrite native paper → stdlib conversion workflow.

The generated native repository does not import CVRS. A random CPU detector
produces real predictions, then a -S stdlib worker converts the explicit output.
This is software evidence, not a pretrained paper reproduction.
"""
from pathlib import Path
import json,sys
from cvsubstrate.provenance.io import write_json,read_json,file_digest

NATIVE = r'''
import argparse,json
from pathlib import Path
import torch,torchvision
from PIL import Image
from torchvision.models.detection import FasterRCNN
from torchvision.models.detection.rpn import AnchorGenerator
from torchvision.ops import MultiScaleRoIAlign
p=argparse.ArgumentParser();p.add_argument('--image',required=True);p.add_argument('--out',required=True);a=p.parse_args()
torch.set_num_threads(1);torch.manual_seed(17)
backbone=torch.nn.Sequential(torch.nn.Conv2d(3,8,3,padding=1,stride=2),torch.nn.ReLU())
backbone.out_channels=8
model=FasterRCNN(backbone,num_classes=2,min_size=32,max_size=64,
    rpn_anchor_generator=AnchorGenerator(((8,16,32),),((.5,1.,2.),)),
    box_roi_pool=MultiScaleRoIAlign(['0'],3,2),rpn_pre_nms_top_n_test=30,rpn_post_nms_top_n_test=20,
    box_detections_per_img=10)
image=Image.open(a.image).convert('RGB')
x=torchvision.transforms.functional.to_tensor(image)
model.eval()
with torch.inference_mode():pred=model([x])[0]
value={'width':image.width,'height':image.height,'boxes':pred['boxes'].tolist(),'scores':pred['scores'].tolist(),
       'labels':pred['labels'].tolist(),'torch':torch.__version__,'torchvision':torchvision.__version__,
       'cvrs_imported':any(x.startswith('cvsubstrate') for x in __import__('sys').modules)}
Path(a.out).mkdir(parents=True,exist_ok=True)
(Path(a.out)/'native.json').write_text(json.dumps(value,allow_nan=False))
'''
CONVERT = r'''
import argparse,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--out',required=True);a=p.parse_args()
r=json.loads(Path(a.input).read_text())
if any(x!=1 for x in r['labels']):raise ValueError('unexpected native label')
row={'schema_version':'1.0','sample_id':'fixture','width':r['width'],'height':r['height'],
     'boxes':r['boxes'],'scores':r['scores'],'category_ids':[3 for _ in r['labels']]}
Path(a.out).mkdir(parents=True,exist_ok=True)
(Path(a.out)/'predictions.jsonl').write_text(json.dumps(row)+'\n')
(Path(a.out)/'conversion.json').write_text(json.dumps({'mapping':{'1':3},'torch_imported':'torch' in sys.modules,'python_site_disabled':sys.flags.no_site}))
'''

def run(root):
    from cvsubstrate.adoption.wrapping import wrap_repository
    from cvsubstrate.adoption.composition import run_composition
    from cvsubstrate.contracts.models import DetectionPrediction
    from cvsubstrate.provenance.artifact_set import verify_directory
    from PIL import Image
    root=Path(root).resolve()
    if root.exists():raise ValueError('choose a new smoke output')
    root.mkdir(parents=True)
    native=root/'paper';native.mkdir();(native/'infer.py').write_text(NATIVE)
    convert=root/'conversion';convert.mkdir();(convert/'convert.py').write_text(CONVERT)
    Image.new('RGB',(64,48),(70,80,90)).save(root/'input.png')
    wrap_repository(native,root/'wrapped-native',purpose='software_fixture',commands={'predict':{
        'argv':['${python}','${repo}/infer.py','--image','${inputs.image}','--out','${output}'],
        'outputs':{'native':{'path':'native.json','kind':'json'}}}})
    p=root/'wrapped-native/paper.json';v=read_json(p);v['trust_code']=True;v['inputs']={'image':str(root/'input.png')};v['input_digests']={'image':file_digest(root/'input.png')};write_json(p,v)
    wrap_repository(convert,root/'wrapped-converter',purpose='software_fixture',commands={'predict':{
        'argv':['${python}','-S','${repo}/convert.py','--input','${inputs.native}','--out','${output}'],
        'outputs':{'predictions':{'path':'predictions.jsonl','kind':'cvrs_hbb'},'conversion':{'path':'conversion.json','kind':'json'}}}})
    p=root/'wrapped-converter/paper.json';v=read_json(p);v['trust_code']=True;write_json(p,v)
    plan={'nodes':[{'id':'native','paper_spec':str(root/'wrapped-native/paper.json')},
      {'id':'canonical','paper_spec':str(root/'wrapped-converter/paper.json'),'depends_on':['native'],
       'bindings':{'native':{'node':'native','output':'native'}}}]}
    write_json(root/'composition.json',plan);result=run_composition(plan,root/'runs',trust=True)
    if result['status']!='SUCCEEDED':raise RuntimeError('native adoption workflow failed')
    raw=read_json(root/'runs/native/outputs/native.json')
    row=DetectionPrediction.model_validate_json((root/'runs/canonical/outputs/predictions.jsonl').read_text())
    audit=read_json(root/'runs/canonical/outputs/conversion.json')
    exact=raw['boxes']==row.boxes and raw['scores']==row.scores
    if not exact or raw['cvrs_imported'] or audit['torch_imported']:raise RuntimeError('native preservation/isolation failed')
    summary={'status':'SUCCEEDED','native_boxes':len(row.boxes),'native_repo_imported_cvrs':raw['cvrs_imported'],
      'converter_imported_torch':audit['torch_imported'],'stdlib_site_disabled':audit['python_site_disabled'],
      'native_coordinates_and_scores_preserved':exact,'category_mapping':audit['mapping'],
      'observed_inputs':result['runs']['native']['inputs'],'composition_integrity':verify_directory(root/'runs'),
      'purpose':'random-initialized CPU software fixture; not a pretrained paper reproduction'}
    write_json(root/'summary.json',summary);return summary

if __name__=='__main__':
    print(json.dumps(run(sys.argv[1]),indent=2))
