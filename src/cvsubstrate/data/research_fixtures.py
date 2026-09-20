"""Small portable examples, unmistakably procedural fixtures, not aerial data."""
from pathlib import Path
import shutil
from cvsubstrate.data.fixtures import generate
from cvsubstrate.contracts.models import ExperimentSpec,Category
from cvsubstrate.contracts.research import CampaignSpec,BackendTemplate,TilingPolicy,SidecarMapping,FieldMapping,SyntheticRecord
from cvsubstrate.data.synthetic import map_sidecar
from cvsubstrate.provenance.io import read_json,write_json,write_jsonl
from cvsubstrate.errors import CVRSError


def generate_research_fixtures(output:Path):
    output=Path(output)
    if output.exists():raise CVRSError('OUTPUT_EXISTS','research-fixture directory must be new')
    generate(output/'images')
    spec=ExperimentSpec.model_validate(read_json(output/'images'/'real.json'))
    spec.dataset='images/dataset.json'
    campaign=CampaignSpec(name='procedural-six-arm-conformance',backends=[BackendTemplate(name='native-conformance',experiment=spec)],
        seeds=[41],updates=1,pretrain_updates=1,
        rationale='CPU execution and exposure-accounting checks only. Both real/synthetic tags refer to procedurally generated software fixtures.')
    write_json(output/'campaign.json',campaign)
    inference=spec.model_copy(deep=True);inference.training=None;inference.name='procedural-tiled-inference'
    write_json(output/'inference.json',inference)
    write_json(output/'tiling.json',TilingPolicy(width=48,height=48,overlap_x=16,overlap_y=16,max_tiles=100))
    sources={
        'generic':({'sample_id':'syn-0','camera':{'altitude_m':80.},'weather':{'visibility_m':None},'scene':'test-scene'},
            SidecarMapping(name='user-generic-v1',generator='procedural-example',fields=[
                FieldMapping(pointer='/camera/altitude_m',target='altitude',unit='m'),
                FieldMapping(pointer='/weather/visibility_m',target='visibility',unit='m')],identity_pointers={'scene_id':'/scene'})),
        'unreal-shaped':({'frame':{'id':'syn-1'},'pose':{'height_cm':12500.},'render':{'sun_elevation_deg':25.}},
            SidecarMapping(name='user-unreal-shaped-v1',sample_id_pointer='/frame/id',generator='user-export-example',simulator='Colosseum (declared example only)',engine='Unreal (declared example only)',fields=[
                FieldMapping(pointer='/pose/height_cm',target='altitude',scale=.01,unit='m'),
                FieldMapping(pointer='/render/sun_elevation_deg',target='sun_elevation',unit='deg')])),
        'blender-shaped':({'image':'syn-2','camera_export':{'height':12.},'scene_label':'procedural'},
            SidecarMapping(name='user-blender-shaped-v1',sample_id_pointer='/image',generator='user-export-example',engine='Blender (declared example only)',fields=[
                FieldMapping(pointer='/camera_export/height',target='altitude',unit='m')],identity_pointers={'scene_id':'/scene_label'})),
        'isaac-shaped':({'frame_id':'syn-3','metadata':{'camera_altitude_m':20.,'exposure_ms':4.}},
            SidecarMapping(name='user-isaac-shaped-v1',sample_id_pointer='/frame_id',generator='user-export-example',simulator='Isaac (declared example only)',fields=[
                FieldMapping(pointer='/metadata/camera_altitude_m',target='altitude',unit='m'),
                FieldMapping(pointer='/metadata/exposure_ms',target='exposure',scale=.001,unit='s')]))}
    for name,(source,mapping) in sources.items():
        write_json(output/'sidecars'/f'{name}.source.json',source)
        write_json(output/'sidecars'/f'{name}.mapping.json',mapping)
        write_json(output/'sidecars'/f'{name}.canonical.json',map_sidecar(source,mapping))
    write_json(output/'dota-categories.json',[Category(id=1,name='small-vehicle')])
    manifest=read_json(output/'images'/'dataset.json')
    sid=manifest['splits']['dev']['sample_ids'][0]
    sample=next(s for s in manifest['samples'] if s['id']==sid)
    dest=output/'dota-images';dest.mkdir();labels=output/'dota-labels';labels.mkdir()
    shutil.copyfile(output/'images'/sample['image'],dest/'fixture.png')
    (labels/'fixture.txt').write_text('imagesource:procedural-software-fixture\ngsd:None\n8 8 24 8 24 20 8 20 small-vehicle 0\n28 28 40 28 40 38 28 38 small-vehicle 1\n','utf-8')
    (output/'README.md').write_text('''# Procedural research examples

All images are software fixtures. The source tags do not turn generated images
into real aerial data. The tiny Faster R-CNN is a randomly initialized conformance
model; no pretrained checkpoint is downloaded.

From this directory (after installing `cvrs` and the native extra):

```text
cvrs campaign plan campaign.json
cvrs campaign run campaign.json --out six-arm-run
cvrs campaign run campaign.json --out six-arm-run --resume
cvrs campaign report six-arm-run --out six-arm-report
cvrs run-tiled inference.json --policy tiling.json --out tiled-runs
cvrs synthetic map sidecars/unreal-shaped.source.json --mapping sidecars/unreal-shaped.mapping.json --out mapped.json
cvrs dota import --images dota-images --labels dota-labels --categories dota-categories.json --name procedural-obb --dataset-version fixture-1 --out dota-images/dataset.json
```

The simulator-shaped exports are invented user-export examples, not native API
formats and not evidence that any simulator integration has been executed.
Run IDs/checkpoint references are execution-specific. Use the recorded checkpoint
hash to create an explicit checkpoint reference for trained tiled inference.
''','utf-8')
    return {'status':'GENERATED','directory':str(output),'campaign':'campaign.json','arms':6,
        'sidecar_export_profiles':4,'real_aerial_dataset':False,'simulators_executed':False,'model_execution':'NOT_RUN'}
