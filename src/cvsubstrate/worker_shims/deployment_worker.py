"""Standalone tensor-boundary export/inference adapters for real native runtimes.

Requires trusted local artifacts. No universal detector decoder, implicit model
conversion, quantization calibration or CUDA fallback is invented here.
"""
from pathlib import Path
import time,statistics,importlib.util,importlib.metadata,os,json
from runtime_common import main,read,write,file_hash,check_file,offline,dependency

def arrays_for(spec,request):
    import numpy as np
    result={}
    for name,path in spec.get('input_arrays',{}).items():
        check_file(path,request['input_sha256'][name]);a=np.load(path,allow_pickle=False)
        if a.dtype.kind not in 'biuf' or not np.isfinite(a).all():raise ValueError('finite numeric tensor required')
        result[name]=a
    return result

def tensor_dtype(precision):
    import torch
    return {'fp32':torch.float32,'fp16':torch.float16,'bf16':torch.bfloat16}.get(precision)

def torch_model(spec):
    import torch
    path=Path(spec['model_path']);opts=spec['options']
    if path.suffix=='.pt2':return torch.export.load(path).module()
    if path.suffix!='.py':raise ValueError('PyTorch export needs trusted .py factory or .pt2 exported program')
    module_spec=importlib.util.spec_from_file_location('cvrs_trusted_model_factory',path);module=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(module)
    factory=getattr(module,opts.get('factory','build_model'));model=factory(**opts.get('factory_kwargs',{}))
    if not isinstance(model,torch.nn.Module):raise ValueError('factory must return torch.nn.Module')
    source=spec.get('source')
    if source:
        check_file(source['path'],source['sha256'])
        if source['serialization']=='safetensors':
            from safetensors.torch import load_file
            weights=load_file(source['path'])
        else:
            unsafe=source['serialization']=='trusted_pickle'
            if unsafe and not source.get('trust_legacy_pickle'):raise ValueError('legacy pickle requires explicit trust')
            weights=torch.load(source['path'],map_location='cpu',weights_only=not unsafe)
        if source.get('state_dict_key'):weights=weights[source['state_dict_key']]
        model.load_state_dict(weights,strict=True)
    return model

def torch_inputs(spec,arrays):
    import torch
    order=spec['options'].get('input_order',sorted(arrays))
    if set(order)!=set(arrays) or len(order)!=len(arrays):raise ValueError('input_order must name each input exactly once')
    dtype=tensor_dtype(spec['precision']);device=spec['device'];values={}
    for key in order:
        t=torch.from_numpy(arrays[key]).to(device)
        # No implicit cast: the request declares the tensor boundary explicitly.
        if t.is_floating_point() and dtype is not None and t.dtype!=dtype:raise ValueError('input floating dtype differs from requested precision')
        values[key]=t
    if spec['options'].get('call_style','kwargs')=='positional':return tuple(values.values()),{}
    return (),values

def flatten(value,prefix='output'):
    if isinstance(value,dict):
        result={}
        for k,v in value.items():result.update(flatten(v,prefix+'.'+str(k)))
        return result
    if isinstance(value,(list,tuple)):
        result={}
        for i,v in enumerate(value):result.update(flatten(v,prefix+'.'+str(i)))
        return result
    return {prefix:value}

def save_outputs(value,out):
    import numpy as np
    result={}
    for i,(key,tensor) in enumerate(flatten(value).items()):
        dtype=str(getattr(tensor,'dtype','unknown'))
        if hasattr(tensor,'detach'):
            tensor=tensor.detach().cpu()
            if str(tensor.dtype)=='torch.bfloat16':tensor=tensor.float()
            array=tensor.numpy()
        else:array=np.asarray(tensor)
        if array.dtype.kind not in 'biuf' or not np.isfinite(array).all():raise ValueError('nonfinite/non-numeric deployment output')
        name=f'output-{i}.npy';np.save(out/name,array,allow_pickle=False)
        result[key]={'path':name,'sha256':file_hash(out/name),'shape':list(array.shape),'runtime_dtype':dtype,'stored_dtype':str(array.dtype)}
    return result

def timed(call,warmup,repeats,sync=lambda:None):
    if not 0<=warmup<=1000 or not 1<=repeats<=10000:raise ValueError('bounded warmup/repeats required')
    for _ in range(warmup):call();sync()
    values=[];result=None
    for _ in range(repeats):
        sync();start=time.perf_counter();result=call();sync();values.append(time.perf_counter()-start)
    ordered=sorted(values)
    return result,{'warmup':warmup,'repeats':repeats,'samples_seconds':values,'median_seconds':statistics.median(values),
        'p95_seconds':ordered[min(len(values)-1,int(.95*len(values)))],'calls_per_second':1/statistics.mean(values),
        'scope':'single synchronous tensor-boundary call; model loading/export, file IO, image decode and detector postprocessing are excluded unless inside the model'}

def dynamic_shapes(options):
    value=options.get('dynamic_shapes')
    if value is None:return None
    import torch
    result={}
    for input_name,axes in value.items():
        result[input_name]={int(axis):torch.export.Dim(v['name'],min=v.get('min',1),max=v.get('max',100000)) for axis,v in axes.items()}
    return result

def run_torch(spec,operation,arrays,out):
    import torch
    if spec['precision']=='int8':raise ValueError('generic PyTorch int8 conversion is not a calibration implementation')
    device=spec['device']
    if device.startswith('cuda') and not torch.cuda.is_available():raise ValueError('CUDA unavailable; no CPU fallback')
    torch.manual_seed(int(spec['options'].get('initialization_seed',0)))
    model=torch_model(spec).to(device=device,dtype=tensor_dtype(spec['precision']))
    if Path(spec['model_path']).suffix!='.pt2':model.eval()
    args,kwargs=torch_inputs(spec,arrays)
    options=spec['options'];artifacts={}
    if operation=='export':
        if spec['backend']=='torch_export':
            ep=torch.export.export(model,args,kwargs=kwargs,dynamic_shapes=dynamic_shapes(options),strict=options.get('strict_export',True))
            torch.export.save(ep,out/'model.pt2');artifacts['model']='model.pt2'
        elif spec['backend']=='onnx':
            torch.onnx.export(model,args,str(out/'model.onnx'),kwargs=kwargs,dynamo=True,
                input_names=options.get('input_order',sorted(arrays)),output_names=options.get('output_names'),
                dynamic_shapes=dynamic_shapes(options),opset_version=options.get('opset_version',18),external_data=True)
            artifacts['model']='model.onnx'
        elif spec['backend']=='openvino':
            import openvino as ov
            ov_model=ov.convert_model(model,example_input=kwargs if kwargs else args)
            ov.save_model(ov_model,str(out/'model.xml'),compress_to_fp16=options.get('compress_weights_to_fp16',False));artifacts['model']='model.xml'
        else:raise ValueError('unsupported torch export destination')
        return {'artifacts':artifacts,'precision':spec['precision'],'inference_ran':False,'export_fidelity':'NOT_ESTABLISHED'}
    sync=(lambda:torch.cuda.synchronize(device)) if device.startswith('cuda') else (lambda:None)
    if device.startswith('cuda'):torch.cuda.reset_peak_memory_stats(device)
    with torch.inference_mode():result,timing=timed(lambda:model(*args,**kwargs),options.get('warmup',1),options.get('repeats',5),sync)
    return {'outputs':save_outputs(result,out),'timing':timing,'peak_memory':{'value':torch.cuda.max_memory_allocated(device) if device.startswith('cuda') else None,'unit':'bytes','kind':'torch_cuda_peak_allocated' if device.startswith('cuda') else 'NOT_MEASURED'}}

def run_ort(spec,arrays,out):
    import onnxruntime as ort
    options=spec['options'];providers=options.get('providers',['CPUExecutionProvider'])
    names=[p if isinstance(p,str) else p[0] for p in providers]
    if any(p not in ort.get_available_providers() for p in names):raise ValueError('requested execution provider unavailable')
    session=ort.InferenceSession(spec['model_path'],providers=providers);session.disable_fallback()
    expected={i.name for i in session.get_inputs()}
    if expected!=set(arrays):raise ValueError('model/request input names differ')
    result,timing=timed(lambda:session.run(None,arrays),options.get('warmup',1),options.get('repeats',5))
    return {'outputs':save_outputs({x.name:v for x,v in zip(session.get_outputs(),result)},out),'timing':timing,
        'providers_requested':providers,'providers_actual':session.get_providers(),'memory':{'value':None,'reason':'native ORT arena peak not instrumented'},
        'precision_statement':'graph and input tensor dtypes govern execution; requested label is not a quantization operation'}

def run_openvino(spec,operation,arrays,out):
    import openvino as ov
    options=spec['options'];path=Path(spec['model_path']);model=ov.Core().read_model(str(path))
    if operation=='export':
        ov.save_model(model,str(out/'model.xml'),compress_to_fp16=options.get('compress_weights_to_fp16',False))
        return {'artifacts':{'model':'model.xml'},'inference_ran':False,'weight_compression':options.get('compress_weights_to_fp16',False),'export_fidelity':'NOT_ESTABLISHED'}
    device=options.get('openvino_device','CPU')
    if device=='AUTO':raise ValueError('explicit OpenVINO device required for reproducible backend identity')
    compiled=ov.Core().compile_model(model,device,options.get('compile_config',{}))
    if {x.get_any_name() for x in compiled.inputs}!=set(arrays):raise ValueError('OpenVINO input names differ')
    result,timing=timed(lambda:compiled(arrays),options.get('warmup',1),options.get('repeats',5))
    return {'outputs':save_outputs({p.get_any_name():value for p,value in result.items()},out),'timing':timing,'device':device,
        'memory':{'value':None,'reason':'native plugin peak not instrumented'}}

def run_trt(spec,operation,arrays,out):
    import tensorrt as trt
    import numpy as np
    import torch
    if not torch.cuda.is_available():raise ValueError('TensorRT requires an available CUDA execution path; no CPU fallback')
    options=spec['options'];logger=trt.Logger(trt.Logger.WARNING);device=spec['device']
    if not device.startswith('cuda'):raise ValueError('TensorRT device must explicitly select CUDA')
    torch.cuda.set_device(torch.device(device))
    if operation=='export':
        builder=trt.Builder(logger)
        flags=0
        if hasattr(trt.NetworkDefinitionCreationFlag,'STRONGLY_TYPED'):flags|=1<<int(trt.NetworkDefinitionCreationFlag.STRONGLY_TYPED)
        network=builder.create_network(flags);parser=trt.OnnxParser(network,logger)
        if not parser.parse_from_file(spec['model_path']):raise ValueError('ONNX parse failed: '+'; '.join(str(parser.get_error(i)) for i in range(parser.num_errors)))
        cfg=builder.create_builder_config();cfg.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE,int(options.get('workspace_bytes',1<<30)))
        if any(-1 in tuple(network.get_input(i).shape) for i in range(network.num_inputs)):
            profile=builder.create_optimization_profile();profiles=options.get('profiles',{})
            for i in range(network.num_inputs):
                t=network.get_input(i)
                if -1 in tuple(t.shape):
                    if t.name not in profiles:raise ValueError('dynamic ONNX inputs require explicit min/opt/max shapes')
                    p=profiles[t.name]
                    if not profile.set_shape(t.name,p['min'],p['opt'],p['max']):raise ValueError('invalid optimization profile')
            cfg.add_optimization_profile(profile)
        # Strongly typed build follows graph dtypes, no silent precision/calibration flags.
        engine=builder.build_serialized_network(network,cfg)
        if engine is None:raise ValueError('TensorRT build returned no engine')
        (out/'model.plan').write_bytes(bytes(engine));return {'artifacts':{'model':'model.plan'},'hardware':torch.cuda.get_device_name(device),
            'precision_statement':'strongly typed ONNX graph controls precision; no automatic int8 calibration','export_fidelity':'NOT_ESTABLISHED'}
    runtime=trt.Runtime(logger);engine=runtime.deserialize_cuda_engine(Path(spec['model_path']).read_bytes())
    if engine is None:raise ValueError('engine deserialization failed; engine/device/runtime may differ')
    context=engine.create_execution_context();buffers={};stream=torch.cuda.Stream(device=device);names=[engine.get_tensor_name(i) for i in range(engine.num_io_tensors)]
    input_names={n for n in names if engine.get_tensor_mode(n)==trt.TensorIOMode.INPUT}
    if input_names!=set(arrays):raise ValueError('TensorRT input names differ')
    for name in input_names:
        a=arrays[name];expected=np.dtype(trt.nptype(engine.get_tensor_dtype(name)))
        if a.dtype!=expected:raise ValueError('input dtype differs from engine')
        if not context.set_input_shape(name,tuple(a.shape)):raise ValueError('input shape not accepted')
        buffers[name]=torch.from_numpy(np.ascontiguousarray(a)).to(device)
        context.set_tensor_address(name,buffers[name].data_ptr())
    unresolved=context.infer_shapes()
    if unresolved:raise ValueError('unresolved shape tensors: '+str(unresolved))
    allocators={}
    for name in names:
        if name in buffers:continue
        shape=tuple(context.get_tensor_shape(name))
        if any(x<0 for x in shape):
            from trt_allocator import make_allocator
            limit=options.get('max_dynamic_output_bytes')
            if not isinstance(limit,int) or limit<=0:raise ValueError('data-dependent outputs require explicit max_dynamic_output_bytes')
            allocator=make_allocator(trt,torch,device,limit);context.set_output_allocator(name,allocator);context.set_tensor_address(name,0)
            allocators[name]=allocator;continue
        npdtype=np.dtype(trt.nptype(engine.get_tensor_dtype(name)));tdtype=torch.from_numpy(np.empty((),dtype=npdtype)).dtype
        buffers[name]=torch.empty(shape,device=device,dtype=tdtype);context.set_tensor_address(name,buffers[name].data_ptr())
    torch.cuda.synchronize(device);torch.cuda.reset_peak_memory_stats(device)
    def call():
        if not context.execute_async_v3(stream.cuda_stream):raise ValueError('TensorRT execution failed')
        return {k:v for k,v in buffers.items() if k not in input_names}
    result,timing=timed(call,options.get('warmup',1),options.get('repeats',5),stream.synchronize)
    for name,allocator in allocators.items():
        npdtype=np.dtype(trt.nptype(engine.get_tensor_dtype(name)));dtype=torch.from_numpy(np.empty((),dtype=npdtype)).dtype
        result[name]=allocator.value(dtype)
    return {'outputs':save_outputs(result,out),'timing':timing,'hardware':torch.cuda.get_device_name(device),
        'peak_memory':{'value':torch.cuda.max_memory_allocated(device),'unit':'bytes','kind':'torch buffers only; excludes TensorRT native workspace'}}

def run(request):
    if request.get('operation')=='capabilities':return {'backends':['torch_export','onnx','onnxruntime','tensorrt','openvino'],'operations':['export','infer'],'automatic_certification':False}
    operation=request['operation'];spec=request['spec'];out=Path(request['output_dir']);out.mkdir(parents=True,exist_ok=True)
    if operation not in {'export','infer'}:raise ValueError('unknown operation')
    if not spec.get('trust_executable_artifact'):raise ValueError('explicit trust required for executable model artifacts/factories')
    check_file(spec['model_path'],spec['model_sha256'])
    for companion in spec.get('options',{}).get('associated_files',[]):check_file(companion['path'],companion['sha256'])
    if Path(spec['model_path']).suffix=='.xml':
        weights=Path(spec['model_path']).with_suffix('.bin')
        if weights.exists() and str(weights.resolve()) not in {str(Path(x['path']).resolve()) for x in spec['options'].get('associated_files',[])}:raise ValueError('OpenVINO .bin identity must be explicitly listed in associated_files')
    if Path(spec['model_path']).suffix.lower()=='.onnx':
        dependency('onnx');import onnx
        graph=onnx.load_model(spec['model_path'],load_external_data=False)
        identities={str(Path(x['path']).resolve()) for x in spec['options'].get('associated_files',[])}
        # Inspect all nested TensorProto messages before ORT/TRT loads external bytes.
        root=Path(spec['model_path']).resolve().parent
        def visit(message):
            if isinstance(message,onnx.TensorProto):
                external={x.key:x.value for x in message.external_data}
                if 'location' in external:
                    child=(root/external['location']).resolve()
                    try:child.relative_to(root)
                    except ValueError:raise ValueError('ONNX external data escapes model directory')
                    if str(child) not in identities:raise ValueError('ONNX external data identity missing from associated_files')
            for field,value in message.ListFields():
                if field.message_type is None:continue
                if field.is_repeated:
                    for child in value:visit(child)
                else:visit(value)
        visit(graph)
    arrays=arrays_for(spec,request);offline()
    backend=spec['backend'];suffix=Path(spec['model_path']).suffix
    if backend in {'torch_export','onnx'}:
        if backend=='onnx' and operation=='infer':raise ValueError('use the explicit onnxruntime backend for inference')
        result=run_torch(spec,operation,arrays,out)
    elif backend=='onnxruntime':
        if operation!='infer':raise ValueError('onnxruntime is a runtime, not an exporter')
        result=run_ort(spec,arrays,out)
    elif backend=='openvino':result=run_torch(spec,operation,arrays,out) if suffix in {'.py','.pt2'} and operation=='export' else run_openvino(spec,operation,arrays,out)
    elif backend=='tensorrt':result=run_trt(spec,operation,arrays,out)
    else:raise ValueError('unsupported runtime')
    files={p.relative_to(out).as_posix():file_hash(p) for p in out.rglob('*') if p.is_file()}
    result.update(backend=backend,operation=operation,model_sha256=spec['model_sha256'],input_sha256=request['input_sha256'],artifacts_sha256=files,
        runtime_status='EXECUTED_IN_THIS_PROCESS',fidelity_certification='NOT_ESTABLISHED')
    write(out/'execution.json',result);return result

if __name__=='__main__':main(run)
