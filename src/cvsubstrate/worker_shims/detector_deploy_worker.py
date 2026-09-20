"""Detector image preprocessing, native ORT/OpenVINO/TRT runtime, audited decoding.

The TensorRT path reuses the tensor runtime and loads the engine per image. Its
recorded inference timing excludes loading; it is not a throughput-optimized service.
"""
from pathlib import Path
import sys,time,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from runtime_common import main,check_file,offline,write,write_lines,sha

def run(req):
    from cvsubstrate.deployment.profiles import DetectorProfile,preprocess_image,decode_outputs
    from cvsubstrate.contracts.models import DetectionPrediction
    from pydantic import TypeAdapter
    from cvsubstrate.contracts.models import ID
    s=req['spec'];out=Path(req['output_dir']);out.mkdir(parents=True,exist_ok=True)
    if not s.get('trust_model'):raise ValueError('explicit executable model trust required')
    model=check_file(s['model_path'],s['model_sha256']);profile=DetectorProfile(**s['profile']);profile.validate()
    images=s['images'];seen=set()
    for image in images:
        TypeAdapter(ID).validate_python(image['id'])
        if image['id'] in seen:raise ValueError('duplicate image ID')
        seen.add(image['id'])
        if image.get('split_role','dev') not in {'dev','selection'}:raise ValueError('standalone deployment evaluation excludes protected test')
        check_file(image['path'],image['sha256'])
    for item in s.get('associated_files',[]):check_file(item['path'],item['sha256'])
    if model.suffix=='.xml' and model.with_suffix('.bin').is_file():
        if str(model.with_suffix('.bin').resolve()) not in {str(Path(x['path']).resolve()) for x in s.get('associated_files',[])}:raise ValueError('OpenVINO weights .bin requires explicit companion hash')
    offline();import numpy as np
    from PIL import Image
    backend=s.get('backend','onnxruntime');runtime_meta={}
    if model.suffix=='.onnx':
        import onnx
        g=onnx.load(model,load_external_data=False)
        def scan(message):
            if isinstance(message,onnx.TensorProto) and message.external_data:raise ValueError('detector recipe requires self-contained ONNX')
            for field,value in message.ListFields():
                if field.message_type:
                    if field.is_repeated:
                        for child in value:scan(child)
                    else:scan(value)
        scan(g)
    if backend=='onnxruntime':
        import onnxruntime as ort
        providers=s.get('providers',['CPUExecutionProvider'])
        if any(p not in ort.get_available_providers() for p in providers):raise ValueError('requested runtime provider unavailable')
        session=ort.InferenceSession(str(model),providers=providers);session.disable_fallback()
        if len(session.get_inputs())!=1:raise ValueError('one image input required; use tensor API for extra shape tensors')
        def call(tensor,work):return {x.name:a for x,a in zip(session.get_outputs(),session.run(None,{session.get_inputs()[0].name:tensor}))}
        runtime_meta={'providers':session.get_providers()}
    elif backend=='openvino':
        import openvino as ov
        device=s.get('device','CPU')
        if device=='AUTO':raise ValueError('explicit OpenVINO device required')
        compiled=ov.Core().compile_model(str(model),device)
        if len(compiled.inputs)!=1:raise ValueError('one image input required')
        def call(tensor,work):return {p.get_any_name():v for p,v in compiled({compiled.input(0).get_any_name():tensor}).items()}
        runtime_meta={'device':device}
    elif backend=='tensorrt':
        from deployment_worker import run_trt
        def call(tensor,work):
            work.mkdir()
            opts={'warmup':0,'repeats':1,**s.get('runtime_options',{})}
            spec={'model_path':str(model),'device':s.get('device','cuda:0'),'options':opts,'precision':s.get('precision','fp32')}
            native=run_trt(spec,'infer',{s['input_name']:tensor},work)
            values={}
            for name,item in native['outputs'].items():
                if not name.startswith('output.'):raise ValueError('unexpected runtime output-name envelope')
                check_file(work/item['path'],item['sha256']);values[name[len('output.'):]]=np.load(work/item['path'],allow_pickle=False)
            write(work/'tensor-runtime.json',native);return values
        runtime_meta={'device':s.get('device','cuda:0'),'engine_loading':'per image; use tensor timing for execution-only comparison'}
    else:raise ValueError('unsupported detector runtime backend')
    rows=[];timings=[];transforms=[]
    for image in images:
        with Image.open(image['path']) as im:
            if im.getexif().get(274,1)!=1:raise ValueError('normalize EXIF and annotations before inference')
            rgb=np.asarray(im.convert('RGB'))
        tensor,t=preprocess_image(rgb,profile);transforms.append({'sample_id':image['id'],**t})
        tag=hashlib.sha256(image['id'].encode()).hexdigest()[:24]
        start=time.perf_counter();native=call(tensor,out/(tag+'-runtime'));timings.append(time.perf_counter()-start)
        np.savez_compressed(out/(tag+'-raw.npz'),**native)
        result=decode_outputs(native,profile,[t])[0];audit=result.pop('audit')
        row=DetectionPrediction(sample_id=image['id'],width=t['width'],height=t['height'],**result,
            transform_provenance={'profile':s['profile'],'decode_audit':audit})
        rows.append(row.model_dump(mode='json'))
    write_lines(out/'predictions.jsonl',rows);write(out/'transforms.json',transforms)
    result={'status':'EXECUTED','backend':backend,'samples':len(rows),'runtime_call_seconds':timings,'runtime':runtime_meta,
        'model_sha256':s['model_sha256'],'accuracy_parity':'NOT_INFERRED_FROM_EXPORT',
        'latency_scope':'ORT/OpenVINO: call only; TRT: engine setup plus tensor run plus output disk transfer; do not mix these timings'}
    write(out/'execution.json',result);return result
if __name__=='__main__':main(run)
