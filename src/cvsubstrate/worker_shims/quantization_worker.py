"""Actual ORT static QDQ / OpenVINO NNCF calibration. No fake INT8 flag."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from runtime_common import main,check_file,write,offline,sha

def run(req):
    from cvsubstrate.contracts.frontier import QuantizationSpec
    from cvsubstrate.provenance.io import digest
    q=QuantizationSpec.model_validate(req['spec']);out=Path(req['output_dir']);out.mkdir(parents=True,exist_ok=True)
    if not q.trust_model:raise ValueError('explicit trust_model required')
    check_file(q.model_path,q.model_sha256)
    for i in q.calibration:check_file(i.path,i.sha256)
    offline();import numpy as np
    def sample(item):
        # Limit uncompressed archive size before np.load, not just compressed bytes.
        import zipfile
        with zipfile.ZipFile(item.path) as z:
            if sum(x.file_size for x in z.infolist())>512*1024*1024:raise ValueError('calibration tensor sample exceeds 512 MiB')
        with np.load(item.path,allow_pickle=False) as f:arrays={name:f[name] for name in f.files}
        if set(arrays)!=set(q.input_names):raise ValueError('calibration input names differ')
        for name,a in arrays.items():
            if a.dtype.kind not in 'fiu' or not np.isfinite(a).all():raise ValueError('nonfinite/invalid calibration tensor')
            shape=q.input_shapes.get(name)
            if shape and list(a.shape)!=shape:raise ValueError('calibration input shape differs')
        return arrays
    # All items validated before invoking quantizer; iterator remains bounded.
    for item in q.calibration:sample(item)
    import onnx
    def reject_external(message):
        if isinstance(message,onnx.TensorProto) and message.external_data:raise ValueError('self-contained ONNX model required')
        for field,value in message.ListFields():
            if field.message_type:
                if field.is_repeated:
                    for child in value:reject_external(child)
                else:reject_external(value)
    reject_external(onnx.load(q.model_path,load_external_data=False))
    if q.backend=='onnxruntime':
        import onnx
        from onnxruntime.quantization import CalibrationDataReader,QuantType,QuantFormat,CalibrationMethod,quantize_static
        graph=onnx.load(q.model_path,load_external_data=False)
        # External data must be made self-contained in a separately hashed model.
        def scan(m):
            if isinstance(m,onnx.TensorProto) and m.external_data:raise ValueError('quantizer requires self-contained ONNX model')
            for field,value in m.ListFields():
                if field.message_type:
                    if field.is_repeated:
                        for child in value:scan(child)
                    else:scan(value)
        scan(graph)
        class Reader(CalibrationDataReader):
            def __init__(self):self.rewind()
            def get_next(self):
                item=next(self.items,None);return sample(item) if item else None
            def rewind(self):self.items=iter(q.calibration)
        method={'minmax':CalibrationMethod.MinMax,'entropy':CalibrationMethod.Entropy,'percentile':CalibrationMethod.Percentile}[q.method]
        quantize_static(q.model_path,str(out/'model-int8.onnx'),Reader(),quant_format=QuantFormat.QDQ,
            activation_type=QuantType.QInt8 if q.activation_type=='int8' else QuantType.QUInt8,
            weight_type=QuantType.QInt8 if q.weight_type=='int8' else QuantType.QUInt8,
            per_channel=q.per_channel,calibrate_method=method,nodes_to_exclude=q.nodes_to_exclude)
        artifact=out/'model-int8.onnx';graph=onnx.load(artifact)
        nodes=sum(n.op_type=='QuantizeLinear' for n in graph.graph.node)
        if nodes==0:raise ValueError('quantizer produced no QDQ nodes; refuse INT8 success claim')
        details={'qdq_nodes':nodes,'format':'ONNX_QDQ','tensorrt_usage':'consume QDQ model with explicit supported operators/shapes; no calibrator flag required'}
    else:
        import openvino as ov
        import nncf
        if q.method!='minmax' or not q.per_channel or q.weight_type!='int8':raise ValueError('NNCF recipe supports minmax/per-channel int8 weights only; no silent parameter ignoring')
        if Path(q.model_path).suffix!='.onnx':raise ValueError('this NNCF recipe accepts self-contained ONNX input only')
        import onnx
        g=onnx.load(q.model_path,load_external_data=False)
        if any(t.external_data for t in g.graph.initializer):raise ValueError('self-contained ONNX required')
        class Data:
            def __len__(self):return len(q.calibration)
            def __getitem__(self,i):return sample(q.calibration[i])
        model=ov.Core().read_model(q.model_path)
        quantized=nncf.quantize(model,nncf.Dataset(Data()),subset_size=len(q.calibration),
            preset=nncf.QuantizationPreset.PERFORMANCE if q.activation_type=='int8' else nncf.QuantizationPreset.MIXED,
            ignored_scope=nncf.IgnoredScope(names=q.nodes_to_exclude) if q.nodes_to_exclude else None)
        artifact=out/'model-int8.xml';ov.save_model(quantized,str(artifact),compress_to_fp16=False)
        details={'format':'OpenVINO_NNCF','activation_interpretation':'PERFORMANCE/MIXED presets control symmetric/asymmetric; runtime tensor types are not inferred from requested label'}
    files={p.name:sha(p) for p in out.iterdir() if p.is_file()}
    result={'status':'QUANTIZED_NOT_ACCURACY_CERTIFIED','backend':q.backend,'artifact':artifact.name,'artifacts':files,
        'model_sha256':q.model_sha256,'calibration_sha256':digest(q.calibration),'calibration_samples':len(q.calibration),
        'accuracy_regression':'NOT_EVALUATED','details':details}
    write(out/'execution.json',result);return result
if __name__=='__main__':main(run)
