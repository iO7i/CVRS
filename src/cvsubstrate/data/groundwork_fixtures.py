"""Generate portable software fixtures and explicit command specifications.

All images/labels are procedural; native-looking formats are interoperability
fixtures, not samples from the actual named datasets. No external downloads.
"""
from pathlib import Path
import copy,struct
from cvsubstrate.data.fixtures import generate as generate_base
from cvsubstrate.contracts.models import DatasetManifest,DetectionPrediction
from cvsubstrate.contracts.groundwork import ObjectSizePolicy,ResearchCampaign,BenchmarkSpec
from cvsubstrate.provenance.io import read_json,write_json,write_jsonl,file_digest,digest
from cvsubstrate.errors import CVRSError

def _float_array(path,values,shape):
    # NPY v1.0 numeric fixture, using only standard library (not pickle).
    header=repr({'descr':'<f4','fortran_order':False,'shape':tuple(shape)})
    header+=' '*((16-(10+len(header)+1)%16)%16)+'\n'
    Path(path).write_bytes(b'\x93NUMPY\x01\x00'+struct.pack('<H',len(header))+header.encode('latin1')+struct.pack('<'+'f'*len(values),*values))

def generate(destination):
    out=Path(destination).resolve()
    if out.exists():raise CVRSError('OUTPUT_EXISTS','fresh fixture directory required')
    out.mkdir(parents=True);generate_base(out/'base');m=DatasetManifest.model_validate(read_json(out/'base'/'dataset.json'))
    size=ObjectSizePolicy();write_json(out/'size-policy.json',size)
    write_json(out/'size-envelope-legacy.json',{'schema_version':'1.0','schema_name':'ObjectSizePolicy','payload_version':'1.0','body':size.model_dump(mode='json')})
    graph={'name':'typed-artifact-pipeline','nodes':[
        {'id':'emit','action':'json.emit','parameters':{'value':size.model_dump(mode='json')},'cache':True},
        {'id':'validate','action':'json.validate','inputs':{'artifact':{'node':'emit','artifact':'value.json'}},'parameters':{'schema':'ObjectSizePolicy'},'cache':True},
        {'id':'copy','action':'artifact.copy','inputs':{'artifact':{'node':'emit','artifact':'value.json'}},'depends_on':['validate'],'cache':True}]}
    write_json(out/'graph.json',graph)
    exp=read_json(out/'base'/'real.json');exp['dataset']=str(out/'base'/'dataset.json');exp['training']['updates']=1
    arms=[{'id':'R','stages':[{'id':'real','source':'real','updates':1,'real_per_update':1}]},
          {'id':'S','stages':[{'id':'synthetic','source':'synthetic','updates':1,'synthetic_per_update':1}]},
          {'id':'RS','stages':[{'id':'mixed','source':'mixed','updates':1,'real_per_update':1,'synthetic_per_update':1}]},
          {'id':'SR','stages':[{'id':'pretrain','source':'synthetic','updates':1,'synthetic_per_update':1},{'id':'finetune','source':'real','updates':1,'real_per_update':1}]},
          {'id':'RR','stages':[{'id':'pretrain','source':'real','updates':1,'real_per_update':1},{'id':'continue','source':'real','updates':1,'real_per_update':1,'transition':'resume_full_state'}]},
          {'id':'Rreplay','stages':[{'id':'replay','source':'real','updates':1,'real_per_update':2}]}]
    campaign=ResearchCampaign(name='groundwork-fixture',arms=arms,seeds=[7],backends=[{'name':'native','experiment':exp}],constraints=[{'metric':'real_exposures','arms':['R','RS','SR']}])
    write_json(out/'campaign.json',campaign);write_json(out/'sweep-axes.json',{'/seeds':[[11],[19]]})
    write_json(out/'benchmark.json',BenchmarkSpec(name='software-conformance',version='1',datasets={'all':digest(m)},allowed_training_datasets=[digest(m)],split_roles={k:v.role for k,v in m.splits.items()},taxonomy_digest=digest(m.categories),evaluation=exp['evaluation'],seed_policy={'minimum_fresh_seeds':3}))
    preds=[]
    for s in m.samples:
        if s.id not in m.splits['dev'].sample_ids:continue
        preds.append(DetectionPrediction(sample_id=s.id,width=s.width,height=s.height,boxes=[b.xyxy for b in s.boxes],scores=[.9]*len(s.boxes),category_ids=[b.category_id for b in s.boxes]))
    write_jsonl(out/'fixture-predictions.jsonl',preds)
    write_json(out/'slice-policy.json',{'name':'fixture-arid','expression':{'field':'domain','op':'eq','value':'fixture-arid'},'metadata_origin':'procedural fixture tags, not real arid-image classification'})
    write_json(out/'large-plan.json',{'source_id':'canvas','source_width':128,'source_height':96,'tile_width':64,'tile_height':64,'overlap_x':16,'overlap_y':16,'scales':[1.0,.5],'batch_size':2})
    write_json(out/'large-policy.json',{'tile_width':64,'tile_height':64,'overlap_x':16,'overlap_y':16,'scales':[1.0,.5],'merge':{'kind':'weighted_box_fusion','iou_threshold':.5}})
    inference=copy.deepcopy(exp);inference['training']=None;write_json(out/'inference.json',inference)
    write_json(out/'merge-input.json',[{'id':'a','box':[1,1,9,9],'score':.9,'category_id':3},{'id':'b','box':[1.1,1.1,9.1,9.1],'score':.8,'category_id':3}])
    write_json(out/'merge-policy.json',{'kind':'weighted_box_fusion','iou_threshold':.5})
    write_json(out/'synthetic-raw.json',{'camera':{'altitude_cm':12300},'scene':'fixture-scene','sun':{'elevation':0},'optional':{}})
    write_json(out/'synthetic-mapping.json',{'provider':'generic','record':{'sample_id':'fixture-00','generator':'procedural-fixture'},'record_fields':{'scene_id':'/scene'},'observations':[
        {'group':'scene','name':'altitude','pointer':'/camera/altitude_cm','scale':.01,'unit':'m'},
        {'group':'illumination','name':'sun_elevation','pointer':'/sun/elevation','unit':'degrees'},
        {'group':'weather','name':'visibility','pointer':'/optional/visibility','unit':'m'}]})
    # Dataset-native fixtures use an explicit complete image index, including empty images.
    items=[m.samples[8],m.samples[9]];annotation_dir=out/'native-annotations';annotation_dir.mkdir()
    image_index=[{'id':str(i+1),'path':s.image,'split':'dev','source_kind':'real','domain':s.domain,'sequence':'fixture-flight','frame':i+1} for i,s in enumerate(items)]
    common={'name':'procedural-aerial-format','version':'1','image_root':str(out/'base'),'categories':[c.model_dump(mode='json') for c in m.categories],
        'split_roles':{'dev':'dev'},'images':image_index,'purpose':'software_fixture','licenses':m.licenses.model_dump(mode='json')}
    box=items[0].boxes[0].xyxy;x1,y1,x2,y2=box;w=x2-x1;h=y2-y1
    coco={'images':[{'id':i+1,'file_name':s.image,'width':s.width,'height':s.height} for i,s in enumerate(items)],'categories':[{'id':3,'name':'fixture-a'},{'id':17,'name':'fixture-b'}],'annotations':[{'id':1,'image_id':1,'category_id':3,'bbox':[x1,y1,w,h],'area':w*h,'iscrowd':0}]}
    write_json(annotation_dir/'coco.json',coco)
    write_json(out/'dataset-coco.json',{**common,'format':'coco','annotations':str(annotation_dir/'coco.json'),'category_mapping':{'3':3,'17':17}})
    write_json(annotation_dir/'xview.json',{'type':'FeatureCollection','features':[{'type':'Feature','properties':{'image_id':'1','type_id':3,'bounds_imcoords':','.join(str(v) for v in box)},'geometry':None}]})
    write_json(out/'dataset-xview.json',{**common,'format':'xview','annotations':str(annotation_dir/'xview.json'),'category_mapping':{'3':3,'17':17}})
    (annotation_dir/'uavdt.txt').write_text(f'1,1,{x1},{y1},{w},{h},0,0,3\n')
    write_json(out/'dataset-uavdt.json',{**common,'format':'uavdt','annotation_sources':[{'path':str(annotation_dir/'uavdt.txt'),'sequence':'fixture-flight'}],'category_mapping':{'3':3,'17':17}})
    for fmt in ['dior','visdrone','dota']:
        idx=copy.deepcopy(image_index)
        for i,image in enumerate(idx):
            path=annotation_dir/(fmt+str(i)+('.xml' if fmt=='dior' else '.txt'));image['annotation']=str(path)
            if fmt=='dior':text='<annotation>'+ (f'<object><name>fixture-a</name><difficult>0</difficult><bndbox><xmin>{x1}</xmin><ymin>{y1}</ymin><xmax>{x2}</xmax><ymax>{y2}</ymax></bndbox></object>' if i==0 else '')+'</annotation>'
            elif fmt=='visdrone':text=f'{x1},{y1},{w},{h},1,3,0,0\n' if i==0 else ''
            else:text=f'{x1} {y1} {x2} {y1} {x2} {y2} {x1} {y2} fixture-a 0\n' if i==0 else ''
            path.write_text(text,'utf-8')
        write_json(out/f'dataset-{fmt}.json',{**common,'format':fmt,'images':idx,'inclusive_maximum':False,'category_mapping':{'3':3,'17':17} if fmt=='visdrone' else {'fixture-a':3,'fixture-b':17}})
    # An actual exportable PyTorch operation; no pretrained model or download.
    factory=out/'tensor_factory.py';factory.write_text('import torch\nclass Model(torch.nn.Module):\n    def forward(self,x):return {"values":x*2+1}\ndef build_model():return Model()\n','utf-8')
    _float_array(out/'input.npy',list(range(6)),[2,3])
    write_json(out/'deployment.json',{'name':'tensor-fixture','backend':'torch_export','model_path':str(factory),'model_sha256':file_digest(factory),'input_arrays':{'x':str(out/'input.npy')},'device':'cpu','precision':'fp32','trust_executable_artifact':True,'options':{'warmup':1,'repeats':2,'initialization_seed':0}})
    readme='# Groundwork fixtures\n\nProcedural software fixtures only. Regenerate on a new machine; generated absolute asset paths bind this local instance. These are not actual aerial datasets or published-checkpoint results.\n\nTry `cvrs graph run graph.json --out graph-run --cache cache`, `cvrs campaign compile campaign.json`, `cvrs dataset import dataset-coco.json --out coco-import`, `cvrs deploy export deployment.json --out tensor-export`. Native model/deployment execution requires optional torch/torchvision. No model downloads.\n'
    (out/'README.md').write_text(readme,'utf-8')
    return {'destination':str(out),'json_files':len(list(out.rglob('*.json'))),'purpose':'software_fixture','datasets':['coco','dior','xview','visdrone','uavdt','dota'],'downloaded_assets':0}
