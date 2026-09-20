"""End-to-end multi-scale local tiled prediction through existing worker contracts."""
from __future__ import annotations
from pathlib import Path
import copy
from cvsubstrate.contracts.models import DatasetManifest,ExperimentSpec,Sample,Split,DetectionPrediction
from cvsubstrate.contracts.groundwork import LargeImagePlan
from cvsubstrate.data.large import plan_large_image,map_box_to_source
from cvsubstrate.data.manifest import validate_manifest
from cvsubstrate.geometry.merge import merge_detections
from cvsubstrate.provenance.io import read_json,read_jsonl,write_json,write_jsonl,digest,file_digest,safe_join
from cvsubstrate.provenance.artifact_set import seal_directory,assert_not_inside_sealed
from cvsubstrate.execution.runner import run_experiment
from cvsubstrate.evaluation.metrics import evaluate
from cvsubstrate.errors import CVRSError

def _run_large(experiment_path:Path,output:Path,policy:dict,*,worker_python=None,evaluator_python=None,timeout=300):
    try:from PIL import Image
    except ImportError as e:raise CVRSError('DEPENDENCY_UNAVAILABLE','Pillow is required for tiling') from e
    exp=ExperimentSpec.model_validate(read_json(experiment_path));mp=(Path(experiment_path).parent/exp.dataset).resolve()
    m=DatasetManifest.model_validate(read_json(mp));validate_manifest(m,mp.parent)
    if digest(m)!=exp.dataset_sha256:raise CVRSError('DATASET_MISMATCH','dataset content changed')
    if exp.training:raise CVRSError('UNSUPPORTED_CAPABILITY','large-image path is inference only')
    split=m.splits[exp.eval_split]
    if split.role not in {'dev','selection'}:raise CVRSError('PROTECTED_SPLIT','large-image path cannot bypass final-test approval')
    if policy.get('merge',{}).get('kind')=='oriented_nms':raise CVRSError('UNSUPPORTED_CAPABILITY','HBB workers cannot emit oriented polygons')
    output=Path(output);assert_not_inside_sealed(output)
    if output.exists():raise CVRSError('OUTPUT_EXISTS','choose a new output directory')
    output.mkdir(parents=True);(output/'images').mkdir();samples=[];plans=[];tile_by_id={}
    ids=set(split.sample_ids)
    for sample in m.samples:
        if sample.id not in ids:continue
        p=LargeImagePlan.model_validate({**policy,'source_id':sample.id,'source_width':sample.width,'source_height':sample.height})
        plan=plan_large_image(p);plans.append(plan)
        with Image.open(safe_join(mp.parent,sample.image)) as source:
            if source.getexif().get(274,1)!=1:raise CVRSError('IMAGE_ORIENTATION','explicitly normalize EXIF orientation before ingest')
            if source.size!=(sample.width,sample.height):raise CVRSError('DIMENSIONS','source dimensions differ')
            source=source.convert('RGB');resized={}
            for tile in plan['tiles']:
                size=tuple(tile['scaled_size'])
                if size not in resized:resized[size]=source.resize(size,Image.Resampling.BILINEAR)
                crop=resized[size].crop(tuple(tile['crop_scaled_xyxy']));canvas=Image.new('RGB',tuple(tile['output_size']));canvas.paste(crop,(0,0))
                target=output/'images'/f"{tile['id']}.png";canvas.save(target)
                samples.append(Sample(id=tile['id'],image=target.relative_to(output).as_posix(),sha256=file_digest(target),
                    width=canvas.width,height=canvas.height,source_kind=sample.source_kind,domain=sample.domain,
                    lineage_group=sample.lineage_group or sample.id,parent_ids=[sample.id]))
                tile_by_id[tile['id']]=tile
    tm=DatasetManifest(name=m.name+'-tiles',version='large-1',categories=m.categories,samples=samples,
        splits={'dev':Split(role='dev',sample_ids=[s.id for s in samples])},licenses=m.licenses,purpose=m.purpose,
        notes='Inference-only crops; no tile labels; final evaluation uses original annotations.')
    write_json(output/'tiles.json',tm);write_json(output/'plans.json',plans)
    ed=exp.model_dump(mode='json');ed.update(dataset='tiles.json',dataset_sha256=digest(tm),eval_split='dev',training=None)
    # Intermediate tile evaluation is diagnostic on empty labels, never scientific output.
    ed['evaluation']={**ed['evaluation'],'evaluator':'diagnostic_detection','evaluator_version':'1'}
    if ed.get('checkpoint'):ed['checkpoint']['path']=str((Path(experiment_path).parent/ed['checkpoint']['path']).resolve())
    if ed['adapter']['name']=='mmdetection':
        for key in ['config_path','legacy_reference','checkpoint_path']:
            if key in ed['adapter']['config']:ed['adapter']['config'][key]=str((Path(experiment_path).parent/ed['adapter']['config'][key]).resolve())
    write_json(output/'tile-experiment.json',ed)
    run=run_experiment(output/'tile-experiment.json',output/'tile-runs',worker_python,timeout)
    native=read_jsonl(run/'predictions.jsonl');all_detections={sid:[] for sid in ids};discarded=[]
    for row in native:
        tile=tile_by_id[row['sample_id']]
        for i,(box,score,cat) in enumerate(zip(row['boxes'],row['scores'],row['category_ids'])):
            mapped=map_box_to_source(box,tile)
            if mapped is None:discarded.append({'tile':row['sample_id'],'index':i,'reason':'padding_only'});continue
            all_detections[tile['source_id']].append({'id':f"{row['sample_id']}:{i}",'box':mapped,'score':score,'category_id':cat,'tile_id':row['sample_id']})
    rows=[];merges={}
    for sample in m.samples:
        if sample.id not in ids:continue
        report=merge_detections(all_detections[sample.id],policy.get('merge',{}));merges[sample.id]=report
        kept=report['detections'];rows.append(DetectionPrediction(sample_id=sample.id,width=sample.width,height=sample.height,
            boxes=[r['box'] for r in kept],scores=[r['score'] for r in kept],category_ids=[r['category_id'] for r in kept],
            transform_provenance={'plan_digest':next(p['plan_digest'] for p in plans if p['policy']['source_id']==sample.id),'merge':report['policy']}))
    write_jsonl(output/'predictions.jsonl',[r.model_dump(mode='json') for r in rows]);write_json(output/'merge-audit.json',{'merges':merges,'discarded':discarded})
    protocol=exp.evaluation.model_copy(update={'tile_merge_policy':{'multiscale':policy,'renderer':'Pillow BILINEAR RGB'}})
    if evaluator_python and protocol.evaluator=='pycocotools':
        from cvsubstrate.evaluation.service import evaluate_isolated
        metrics=evaluate_isolated(m,exp.eval_split,rows,protocol,worker_python=evaluator_python)
    else:metrics=evaluate(m,exp.eval_split,rows,protocol)
    write_json(output/'metrics.json',metrics);write_json(output/'source-experiment.json',exp)
    report={'status':'SUCCEEDED','source_dataset_digest':digest(m),'source_images':len(ids),'tiles':len(samples),
        'worker_run':run.relative_to(output).as_posix(),'batch_policy':'worker-defined; planned memory batches are advisory',
        'performance_limit':'one resized source image per scale is held; not a streaming gigapixel reader'}
    write_json(output/'execution.json',report);seal_directory(output);return report


def run_large(experiment_path:Path,output:Path,policy:dict,*,worker_python=None,evaluator_python=None,timeout=300):
    existed=Path(output).exists()
    try:
        return _run_large(experiment_path,output,policy,worker_python=worker_python,evaluator_python=evaluator_python,timeout=timeout)
    except (Exception,KeyboardInterrupt) as exc:
        out=Path(output)
        if not existed and out.is_dir() and not (out/'integrity.json').exists():
            write_json(out/'failure.json',{'status':'CANCELLED' if isinstance(exc,KeyboardInterrupt) else 'FAILED','code':getattr(exc,'code',type(exc).__name__),'message':str(exc)})
            seal_directory(out)
        raise
