"""Standalone stdlib shim; all DOTA/NumPy/polyiou imports stay in this interpreter."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import sys


def main():
    p=argparse.ArgumentParser();p.add_argument('--request',required=True);p.add_argument('--response',required=True);a=p.parse_args()
    try:
        with open(a.request,encoding='utf-8') as f:r=json.load(f)
        path=r['module_path']
        with open(path,'rb') as f:h=hashlib.sha256(f.read()).hexdigest()
        if h!=r['module_sha256']:raise ValueError('reference module changed')
        sys.path.insert(0,os.path.dirname(path))
        spec=importlib.util.spec_from_file_location('cvrs_explicit_dota_reference',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        output={}
        for name in r['classes']:
            rec,prec,ap=module.voc_eval(r['detpath'],r['annopath'],r['imagesetfile'],name,ovthresh=r['iou'],use_07_metric=r['use_07_metric'])
            values={'recall':[float(v) for v in rec],'precision':[float(v) for v in prec],'ap':float(ap)}
            if any(not math.isfinite(v) for v in values['recall']+values['precision']+[values['ap']]):
                raise ValueError('reference returned nonfinite/undefined values; no fabricated zero')
            output[name]=values
        result={'per_class':output,'mean_ap':sum(v['ap'] for v in output.values())/len(output),'python':platform.python_version(),
                'module_sha256':h,'upstream_stdout':'retained by controller','polyiou_loaded':'polyiou' in sys.modules}
        if 'numpy' in sys.modules:result['numpy_version']=sys.modules['numpy'].__version__
        value={'status':'SUCCEEDED','result':result}
    except Exception as exc:
        value={'status':'FAILED','error':type(exc).__name__+': '+str(exc)}
    with open(a.response,'w',encoding='utf-8') as f:json.dump(value,f,allow_nan=False,indent=2)
    return 0 if value['status']=='SUCCEEDED' else 2

if __name__=='__main__':sys.exit(main())
