"""Small independent adoption examples. External models are never silently substituted."""
from pathlib import Path
import sys
from cvsubstrate.provenance.io import read_json,write_json,file_digest

EXAMPLES={
 '01-basic-detection': 'A real random-initialized CPU detector, evidence and re-evaluation',
 '02-mmdetection-heritage': 'Read-only inspection and wrapper preparation for an actual local MM repository',
 '03-cross-framework': 'Compare two existing verified runs without inventing equal training conditions',
 '04-aerial-tiling': 'Generated GeoTIFF, genuine detector, pause/resume and source-coordinate predictions',
 '05-sim2real': 'Six-arm procedural campaign planning; optional explicit native CPU execution',
 '06-open-vocabulary': 'Execute a supplied local grounded-model job, or materialize an honest asset preparation recipe',
 '07-segmentation': 'Real Mask R-CNN inference and exact native-mask/RLE conversion',
 '08-reproduction-registry': 'Original/rerun capture, artifact-only re-evaluation, capsule and static registry'
}

def run_example(name,out,*,repo=None,left=None,right=None,job=None,execute=False,worker_python=None):
    if name not in EXAMPLES:raise ValueError('unknown public example')
    out=Path(out).resolve()
    if out.exists():raise ValueError('use a fresh example output')
    if name in {'01-basic-detection','08-reproduction-registry'}:
        from cvsubstrate.adoption.demo import demo
        return demo(out,worker_python=worker_python)
    if name=='02-mmdetection-heritage':
        if repo:
            from cvsubstrate.adoption.wrapping import wrap_repository
            return wrap_repository(repo,out,python=worker_python or sys.executable)
        from cvsubstrate.adoption.recipes import materialize_recipe
        result=materialize_recipe('pwood-cvpr26',out)
        result['next']='Run again in a new directory with --repo pointing to the actual checkout; no fake MM execution occurred.'
        return result
    if name=='03-cross-framework':
        out.mkdir(parents=True)
        if left and right:
            from cvsubstrate.evaluation.cross_framework import compare_runs
            from cvsubstrate.publication.site import results_site
            result=compare_runs(Path(left),Path(right));write_json(out/'comparison.json',result)
            results_site([left,right],out/'site');return result
        result={'status':'ASSETS_REQUIRED','required':['--left verified CVRS run','--right verified CVRS run'],
                'purpose':'Compare actual observations, not fabricated model scores','same_evaluation_is_not_training_fairness':True}
        write_json(out/'requirements.json',result);return result
    if name=='04-aerial-tiling':return _raster(out,worker_python)
    if name=='05-sim2real':
        from cvsubstrate.data.research_fixtures import generate_research_fixtures
        out.mkdir(parents=True);generate_research_fixtures(out/'fixtures')
        campaign=out/'fixtures/campaign.json'
        if execute:
            import subprocess
            argv=[sys.executable,'-m','cvsubstrate','campaign','run',str(campaign),'--out',str(out/'runs')]
            p=subprocess.run(argv,check=False,capture_output=True,text=True,timeout=240)
            (out/'campaign.log').write_text(p.stdout+p.stderr)
            if p.returncode:raise RuntimeError('campaign failed; see campaign.log')
        result={'status':'EXECUTED_SOFTWARE_FIXTURE' if execute else 'PLANNED_SOFTWARE_FIXTURE','campaign':str(campaign),
                'note':'Procedural source tags; no real-vs-synthetic research result.'}
        write_json(out/'result.json',result);return result
    if name=='06-open-vocabulary':
        if job:
            from cvsubstrate.vision.service import vision_job
            return vision_job(job,out,worker_python=worker_python)
        out.mkdir(parents=True)
        from cvsubstrate.adoption.environments import scaffold_environment
        scaffold_environment('grounding-dino',out/'environment')
        result={'status':'ASSETS_REQUIRED','required':['local model directory and component hashes','image path/hash','explicit prompt provenance'],
                'command':'Supply --job with a valid VisionJob for hf_grounding_dino; no model is downloaded.',
                'not_substituted':'No random or heuristic output is labeled Grounding DINO.'}
        write_json(out/'requirements.json',result);return result
    return _mask(out,worker_python)

def _raster(out,worker_python):
    import numpy as np, torch, rasterio
    from rasterio.transform import from_origin
    from cvsubstrate.workers.native_torch import model_factory,save_checkpoint
    from cvsubstrate.streaming.service import stream_job
    out.mkdir(parents=True);torch.set_num_threads(1);torch.manual_seed(17)
    model=model_factory(2);ckpt=out/'model.pt'
    save_checkpoint(ckpt,model,None,None,{'purpose':'software_fixture'},{'completed_updates':0})
    raster=out/'generated.tif'
    with rasterio.open(raster,'w',driver='GTiff',width=96,height=80,count=3,dtype='uint8',crs='EPSG:32637',transform=from_origin(400000,2500000,.5,.5)) as ds:
        ds.write(np.random.default_rng(17).integers(0,255,(3,80,96),dtype=np.uint8))
    spec={'raster':str(raster),'raster_sha256':file_digest(raster),'tile_width':64,'tile_height':64,'overlap':16,
          'scales':[1.0],'sample_id':'procedural-scene','model':{'backend':'native_torch','checkpoint':str(ckpt),
          'checkpoint_sha256':file_digest(ckpt),'trust_checkpoint':True,'category_map':{'1':0},'config':{},'cpu_threads':1}}
    write_json(out/'stream.json',spec)
    partial=stream_job(out/'stream.json',out/'run',worker_python=worker_python,max_tiles=1,timeout=90)
    complete=stream_job(out/'stream.json',out/'run',worker_python=worker_python,resume=True,timeout=90)
    result={'status':complete['status'],'partial':partial,'complete':complete,'purpose':'small_geometry_fixture_not_gigapixel_benchmark'}
    write_json(out/'result.json',result);return result

def _mask(out,worker_python):
    import numpy as np,torch
    from PIL import Image
    from cvsubstrate.vision.native_mask import build_mask_detector
    from cvsubstrate.vision.service import vision_job
    from cvsubstrate.vision.masks import decode_mask
    from cvsubstrate.contracts.frontier import MaskPrediction
    from cvsubstrate.provenance.io import read_jsonl
    out.mkdir(parents=True);(out/'model').mkdir();torch.set_num_threads(1);torch.manual_seed(17)
    model=build_mask_detector(2);torch.save(model.state_dict(),out/'model/mask.pt')
    Image.fromarray(np.random.default_rng(17).integers(0,255,(64,80,3),dtype=np.uint8)).save(out/'image.png')
    job={'backend':'torchvision_mask','model_dir':str(out/'model'),'model_files':{'mask.pt':file_digest(out/'model/mask.pt')},
         'images':[{'id':'mask-image','path':str(out/'image.png'),'sha256':file_digest(out/'image.png'),'split_role':'dev'}],
         'config':{'weights_file':'mask.pt','category_map':{'1':0}},'purpose':'software_fixture'}
    write_json(out/'job.json',job);result=vision_job(job,out/'run',worker_python=worker_python,timeout=90)
    canonical=MaskPrediction.model_validate(read_jsonl(out/'run/worker/predictions.jsonl')[0])
    with np.load(next((out/'run/worker').glob('*-native.npz')),allow_pickle=False) as raw:
        exact=len(raw['masks'])==len(canonical.instances) and all(np.array_equal(m,decode_mask(c.mask)) for m,c in zip(raw['masks'],canonical.instances))
    result={'native':result,'canonical_mask_count':len(canonical.instances),'mask_roundtrip_exact':exact,'pretrained':False,'status':'SUCCEEDED' if exact else 'FAILED'}
    write_json(out/'result.json',result);return result

def main(name,argv=None):
    import argparse,json
    p=argparse.ArgumentParser(description=EXAMPLES[name]);p.add_argument('output');p.add_argument('--repo');p.add_argument('--left');p.add_argument('--right');p.add_argument('--job');p.add_argument('--execute',action='store_true');p.add_argument('--python')
    a=p.parse_args(argv)
    print(json.dumps(run_example(name,a.output,repo=a.repo,left=a.left,right=a.right,job=a.job,execute=a.execute,worker_python=a.python),indent=2,default=str))
