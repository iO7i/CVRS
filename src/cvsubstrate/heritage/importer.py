"""Static config archaeology and safe JSON prediction import. Never unpickles."""
from __future__ import annotations
import ast
from pathlib import Path
import shutil
from cvsubstrate.contracts.models import DetectionPrediction, LegacyExperimentRef, CheckpointRef
from cvsubstrate.data.manifest import load_manifest
from cvsubstrate.evaluation.metrics import validate_predictions
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.artifact_set import seal_directory
from cvsubstrate.provenance.io import digest, file_digest, read_jsonl, safe_join, write_json, write_jsonl


def config_graph(config: Path, source_root: Path, *, max_files=512, max_depth=64):
    root=Path(source_root).resolve(); config=Path(config).resolve()
    visited={};active=set();unresolved=[];edges=[]
    def visit(path,depth):
        path=path.resolve()
        if not path.is_relative_to(root):
            raise CVRSError('CONFIG_ESCAPE','config/base dependency escapes explicit source root')
        name=path.relative_to(root).as_posix()
        if name in active:
            raise CVRSError('CONFIG_CYCLE','cyclic _base_ dependency')
        if name in visited:
            return
        if depth>max_depth or len(visited)>=max_files:
            raise CVRSError('CONFIG_GRAPH_LIMIT','static inheritance graph exceeded limits')
        if not path.is_file():
            unresolved.append({'path':name,'reason':'missing base file'});return
        if path.stat().st_size>2*1024*1024:
            raise CVRSError('CONFIG_TOO_LARGE','config too large for static inspection')
        tree=ast.parse(path.read_text('utf-8'),filename=name)
        active.add(name);literal={};bases=[];dynamic=[];base_assignments=0
        for node in tree.body:
            if isinstance(node,(ast.Assign,ast.AnnAssign)):
                targets=node.targets if isinstance(node,ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target,ast.Name):
                        try:
                            val=ast.literal_eval(node.value)
                            # AST literal values like sets/bytes are not canonical JSON.
                            digest(val)
                            literal[target.id]=val
                        except (ValueError,TypeError):
                            dynamic.append({'name':target.id,'line':node.lineno})
                        if target.id=='_base_':
                            base_assignments+=1
            elif not (isinstance(node,ast.Expr) and isinstance(node.value,ast.Constant)):
                dynamic.append({'statement':type(node).__name__,'line':node.lineno})
        if base_assignments>1:
            dynamic.append({'name':'_base_','reason':'multiple assignments; native resolution required'})
        b=literal.get('_base_',[])
        if isinstance(b,str):b=[b]
        if not isinstance(b,list) or any(not isinstance(x,str) for x in b):
            unresolved.append({'path':name,'reason':'nonliteral _base_'});b=[]
        visited[name]={'path':name,'sha256':file_digest(path),'literal_metadata':literal,'dynamic':dynamic}
        if dynamic:
            unresolved.append({'path':name,'reason':'executable/dynamic content; not statically resolved'})
        for ref in b:
            if '::' in ref:
                unresolved.append({'path':name,'reference':ref,'reason':'package-qualified base requires native resolver'});continue
            child=(path.parent/ref).resolve()
            if not child.is_relative_to(root):
                raise CVRSError('CONFIG_ESCAPE','base path outside source root')
            child_name=child.relative_to(root).as_posix()
            edges.append({'from':name,'to':child_name,'declared_reference':ref})
            visit(child,depth+1)
        active.remove(name)
    visit(config,0)
    value={'schema_version':'1.0','entrypoint':config.relative_to(root).as_posix(),
        'files':list(visited.values()),'edges':edges,'unresolved':unresolved,'executed':False,
        'status':'STATIC_GRAPH_CAPTURED','limits':'Does not resolve executable Python, custom imports, or all runtime dependencies.'}
    value['graph_digest']=digest(value)
    return value


def import_project(config: Path, source_root: Path, output: Path, *, upstream: str,
                   revision: str, checkpoint: Path | None=None, dataset: Path | None=None):
    output=Path(output).resolve()
    if output.exists():
        raise CVRSError('OUTPUT_EXISTS','heritage import output must be new')
    root=Path(source_root).resolve()
    graph=config_graph(config,root)
    output.mkdir(parents=True)
    for item in graph['files']:
        dst=safe_join(output/'source',item['path']);dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(safe_join(root,item['path']),dst)
    write_json(output/'config_graph.json',graph)
    ck=None
    if checkpoint is not None:
        checkpoint=Path(checkpoint).resolve()
        if not checkpoint.is_file():
            raise CVRSError('CHECKPOINT_MISSING','checkpoint file not found')
        ck=CheckpointRef(path=str(checkpoint),sha256=file_digest(checkpoint),trust='trusted_legacy_pickle')
    m=load_manifest(dataset) if dataset is not None else None
    reference=LegacyExperimentRef(upstream=upstream,revision=revision,
        config='source/'+graph['entrypoint'],config_sha256=file_digest(config),
        config_graph_sha256=file_digest(output/'config_graph.json'),checkpoint=ck,
        dataset_sha256=digest(m) if m else None,taxonomy=m.categories if m else [],
        environment_reference='environment-required.json',trust_executable_config=False)
    write_json(output/'reference.json',reference)
    write_json(output/'environment-required.json',{'status':'NOT_CAPTURED','required':[
        'exact Python/PyTorch/MMCV/MMEngine/MMDetection versions','source Git SHA',
        'explicit category mapping','checkpoint license review','trusted executable-config approval'],
        'checkpoint_bytes_copied':False,'checkpoint_deserialized':False})
    report={'status':'HERITAGE_TEMPLATE_CREATED','compatibility_level':'H0_CATALOGUED',
        'config_files_preserved':len(graph['files']),'config_graph_digest':graph['graph_digest'],
        'unresolved':graph['unresolved'],'execution_verified':False,
        'trust_note':'Config trust remains false. Checkpoint trust label describes the required loader; no bytes were executed.'}
    write_json(output/'import_report.json',report)
    seal_directory(output)
    return report


def import_predictions(native_path: Path, dataset: Path, split: str, category_map: dict,
                       output: Path, *, native_format: str):
    """Supported JSONL: {sample_id, result: [[x1,y1,x2,y2,score], ...] per class}
    for mmdet2_bbox; {sample_id, boxes, scores, labels} for mmdet3_instances.
    The file is exported JSON, never an arbitrary pickle/checkpoint.
    """
    if native_format not in {'mmdet2_bbox','mmdet3_instances'}:
        raise ValueError('explicit supported native JSON format required')
    output=Path(output).resolve()
    if output.exists():raise CVRSError('OUTPUT_EXISTS','prediction import output must be new')
    m=load_manifest(dataset)
    if split not in m.splits or m.splits[split].role!='dev':
        raise CVRSError('EVAL_ROLE','offline import accepts dev only; locked test requires governed execution')
    mapping={}
    for k,v in category_map.items():
        if not isinstance(k,str) or not k.isdigit() or isinstance(v,bool) or not isinstance(v,int):
            raise ValueError('mapping must have numeric-string native keys and integer canonical IDs')
        mapping[int(k)]=v
    if len(set(mapping.values()))!=len(mapping):
        raise ValueError('noninjective category mapping would change task semantics')
    if not set(mapping.values()).issubset({c.id for c in m.categories}):
        raise ValueError('mapped category not in dataset')
    byid={s.id:s for s in m.samples};converted=[];native_count=0
    raw=read_jsonl(native_path)
    for row in raw:
        sid=row.get('sample_id')
        if sid not in byid:raise CVRSError('SAMPLE_UNKNOWN','native output references an unknown sample')
        if native_format=='mmdet2_bbox':
            if set(row)!={'sample_id','result'}:raise ValueError('unexpected MM2 export fields')
            boxes=[];scores=[];labels=[]
            if not isinstance(row['result'],list):raise ValueError('MM2 result must contain a per-class list')
            for cls,rows in enumerate(row['result']):
                if not isinstance(rows,list):raise ValueError('MM2 class result must be a list')
                for v in rows:
                    if not isinstance(v,list) or len(v)!=5:raise ValueError('MM2 bbox row must have five numbers')
                    boxes.append(v[:4]);scores.append(v[4]);labels.append(cls)
        else:
            if set(row)!={'sample_id','boxes','scores','labels'}:raise ValueError('unexpected MM3 export fields')
            boxes=row['boxes'];scores=row['scores'];labels=row['labels']
        if not isinstance(labels,list) or any(isinstance(x,bool) or not isinstance(x,int) for x in labels):
            raise ValueError('native class indices must be integers')
        if any(x not in mapping for x in labels):raise CVRSError('UNMAPPED_CATEGORY','native class would be dropped; import rejected')
        s=byid[sid]
        pred=DetectionPrediction(sample_id=sid,width=s.width,height=s.height,boxes=boxes,scores=scores,
            category_ids=[mapping[x] for x in labels],transform_provenance={'native_format':native_format,
                'native_file_sha256':file_digest(native_path),'source':'externally supplied JSON','coordinate_conversion':'none'})
        native_count+=len(boxes);converted.append(pred)
    validate_predictions(m,split,converted)
    output.mkdir(parents=True)
    shutil.copyfile(native_path,output/'native.jsonl')
    write_jsonl(output/'predictions.jsonl',converted)
    report={'status':'EXTERNAL_JSON_IMPORT_AUDITED','native_format':native_format,
        'native_file_sha256':file_digest(native_path),'dataset_digest':digest(m),'split':split,
        'images':len(converted),'native_detections':native_count,
        'canonical_detections':sum(len(p.boxes) for p in converted),'values_changed':0,
        'category_map':category_map,'native_execution_verified':False,
        'limits':'Exact JSON conversion only. These inputs do not prove genuine MMDetection execution or model provenance.'}
    write_json(output/'conversion_report.json',report);seal_directory(output)
    return report
