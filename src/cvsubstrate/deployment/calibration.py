"""Create calibration tensors using the same explicit detector preprocess profile."""
from pathlib import Path
from dataclasses import asdict
from cvsubstrate.provenance.io import digest,file_digest,write_json
from cvsubstrate.provenance.artifact_set import seal_directory,assert_not_inside_sealed
from cvsubstrate.deployment.profiles import DetectorProfile,preprocess_image
from cvsubstrate.contracts.frontier import QuantizationSpec

def prepare_calibration(spec,output):
    import numpy as np
    from PIL import Image
    out=Path(output).resolve();assert_not_inside_sealed(out)
    if out.exists():raise ValueError('new calibration output directory required')
    profile=DetectorProfile(**spec['profile']);profile.validate();rows=spec['images'];seen=set()
    if not rows:raise ValueError('nonempty calibration dataset required')
    if file_digest(Path(spec['model_path']))!=spec['model_sha256']:raise ValueError('model identity differs')
    for row in rows:
        if row['id'] in seen:raise ValueError('duplicate calibration sample ID')
        seen.add(row['id'])
        if row['split_role'] not in {'train','calibration','dev'}:raise ValueError('protected test/selection data cannot calibrate model')
        if file_digest(Path(row['path']))!=row['sha256']:raise ValueError('calibration image identity differs')
    out.mkdir(parents=True);(out/'tensors').mkdir();items=[];transforms=[]
    for row in rows:
        with Image.open(row['path']) as im:
            if im.getexif().get(274,1)!=1:raise ValueError('normalize image orientation before calibration')
            tensor,transform=preprocess_image(np.asarray(im.convert('RGB')),profile)
        name=digest(row['id'])+'.npz';path=out/'tensors'/name
        np.savez(path,**{spec.get('input_name','images'):tensor})
        items.append({'id':row['id'],'path':str(path),'sha256':file_digest(path),'split_role':row['split_role']})
        transforms.append({'sample_id':row['id'],'source_sha256':row['sha256'],'tensor_path':'tensors/'+name,'transform':transform})
    q=QuantizationSpec(backend=spec.get('backend','onnxruntime'),model_path=str(Path(spec['model_path']).resolve()),model_sha256=spec['model_sha256'],
        calibration=items,dataset_sha256=spec['dataset_sha256'],preprocessing_sha256=digest(asdict(profile)),
        input_names=[spec.get('input_name','images')],input_shapes={spec.get('input_name','images'):[1,3,profile.input_height,profile.input_width]},
        method=spec.get('method','minmax'),per_channel=spec.get('per_channel',True),weight_type=spec.get('weight_type','int8'),activation_type=spec.get('activation_type','uint8'),trust_model=spec.get('trust_model',False))
    write_json(out/'quantization.json',q);write_json(out/'transforms.json',transforms)
    write_json(out/'calibration.json',{'status':'PREPARED','items':len(items),'profile':asdict(profile),'dataset_sha256':spec['dataset_sha256'],
        'subset_sha256':digest([{k:v for k,v in row.items() if k!='path'} for row in rows]),'quantization_executed':False,
        'calibration_on_dev':any(row['split_role']=='dev' for row in rows),'warning':'Calibration is training-time data use; reuse of dev data for evaluation must be disclosed.'})
    seal_directory(out)
    return {'status':'PREPARED','path':str(out),'items':len(items),'quantization_spec':str(out/'quantization.json'),'profile_sha256':digest(asdict(profile))}

def accuracy_regression(baseline,quantized,maximum_drop):
    from cvsubstrate.deployment.compare import compare_metrics
    import math
    if not maximum_drop or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in maximum_drop.values()):raise ValueError('predeclared metric-specific nonnegative limits required')
    compared=compare_metrics(baseline,quantized);rows={}
    for name,limit in maximum_drop.items():
        if name not in compared['differences'] or compared['differences'][name]['delta'] is None:raise ValueError('required comparable metric missing: '+name)
        d=compared['differences'][name];rows[name]={**d,'maximum_drop':limit,'within_limit':d['delta']>=-limit}
    return {'kind':'QUANTIZATION_ACCURACY_REGRESSION','status':'WITHIN_DECLARED_LIMITS' if all(v['within_limit'] for v in rows.values()) else 'REGRESSION',
        'metrics':rows,'comparison_digest':compared['comparison_digest'],'scope':'higher-is-better metrics under one evaluation protocol; not deployment hardware certification'}
