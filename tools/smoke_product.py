"""Execute the product path using owned, random CPU fixtures and no remote services.

The managed environments use only the already-installed Python interpreter and
stdlib. This does not install/certify a legacy CUDA or pretrained model stack.
Run from the source checkout after installing .[native,adoption].
"""
from __future__ import annotations
import json
import shutil
import sys
import time
from pathlib import Path
from cvsubstrate.provenance.io import write_json,read_json,file_digest


def run(destination: str | Path):
    from PIL import Image
    from cvsubstrate.product.environments import EnvironmentManager
    from cvsubstrate.product.onboarding import prepare_paper,approve_paper,execute_approved
    from cvsubstrate.product.interchange import RichInterchange,exchange,audit_roundtrip
    from cvsubstrate.product.browser import build_browser
    from cvsubstrate.product.methodology import review_methodology
    from cvsubstrate.product.launch import preflight,launch_plan,contribution_check
    from cvsubstrate.product.compatibility import freeze_api,make_receipt,render_badge
    from cvsubstrate.adoption.demo import demo
    from cvsubstrate.provenance.artifact_set import verify_directory
    from smoke_adoption import NATIVE
    root=Path(destination).absolute()
    if root.exists():raise ValueError('choose a fresh output path')
    root.mkdir(parents=True);start=time.monotonic()
    source=Path(__file__).resolve().parents[1]
    try:
        manager=EnvironmentManager(root/'managed')
        plan=manager.plan({'name':'metadata','backend':'venv','python':sys.executable,'expected_modules':['json','sqlite3']})
        first=manager.apply(plan,approve_digest=plan.plan_digest)
        repair=manager.repair_plan('metadata');second=manager.apply(repair,approve_digest=repair.plan_digest)
        rollback=manager.activate('metadata',first['revision'],confirm=True)
        uv=None
        if shutil.which('uv'):
            plan=manager.plan({'name':'uv-metadata','backend':'uv','python':sys.executable,'expected_modules':['json']})
            uv=manager.apply(plan,approve_digest=plan.plan_digest)
        write_json(root/'environment-summary.json',{'first':first,'repair':second,'rollback':rollback,'uv':uv,
          'model_stack_installed':False,'network_operations':0})
        paper=root/'native-paper';paper.mkdir();(paper/'infer.py').write_text(NATIVE,encoding='utf-8')
        image=root/'input.png';Image.new('RGB',(64,48),(70,80,90)).save(image)
        decisions={'purpose':'software_fixture','inputs':{'image':str(image)},'operations':{'predict':{
          'argv':['${python}','${repo}/infer.py','--image','${inputs.image}','--out','${output}'],
          'outputs':{'native':{'path':'native.json','kind':'json'}}}}}
        prepared=prepare_paper(paper,root/'paper-project',python=sys.executable,decisions=decisions)
        spec=root/'paper-project/paper.json';original=file_digest(spec)
        approval=approve_paper(spec,'owned-fixture-operator',root/'paper-approval.json')
        executed=execute_approved(spec,root/'paper-approval.json','predict',root/'paper-result',trust=True)
        assert file_digest(spec)==original and read_json(spec)['trust_code'] is False
        raw=read_json(root/'paper-result/outputs/native.json');assert not raw['cvrs_imported']
        rich=RichInterchange(dataset_digest=file_digest(image),categories={3:'fixture_vehicle'},frames=[{
          'sample_id':'fixture','width':raw['width'],'height':raw['height'],'task':'hbb_detection',
          'objects':[{'id':str(i),'box':box,'score':score,'category_id':3} for i,(box,score,label) in enumerate(zip(raw['boxes'],raw['scores'],raw['labels']))],
          'metadata':{'purpose':'software_fixture','native_category_mapping':{'1':3}}}])
        assert all(label==1 for label in raw['labels'])
        write_json(root/'canonical-rich.json',rich)
        audits={}
        for target in ('fiftyone','supervision'):
            payload=exchange(rich.model_dump(mode='json'),target,'export')
            restored=exchange(payload,target,'import')
            audits[target]=audit_roundtrip(rich.model_dump(mode='json'),restored)
            write_json(root/(target+'-payload.json'),payload);write_json(root/(target+'-restored.json'),restored)
            assert audits[target]['status']=='PRESERVED'
        # Real detector runs provide the static browser's data; no invented scores.
        golden=demo(root/'research',worker_python=sys.executable,timeout=240)
        site=build_browser(root/'research',root/'browser',verify=True)
        method=review_methodology({'arms':[{'id':'R','optimizer_updates':100},{'id':'R+S','optimizer_updates':200}],
          'prompts':[{'source':'dataset_class_vocabulary','scope':'dataset'}], 'protocol':{'name':'example'}})
        write_json(root/'methodology.json',method)
        receipt=make_receipt({'subject_id':'mmdetection3','task':'hbb_detection','operation':'predict','implementation':'AVAILABLE'})
        write_json(root/'adapter-available.json',receipt);render_badge(receipt,root/'adapter-available.svg')
        freeze_api(source,root/'api-surface.json')
        gate=preflight(source);write_json(root/'public-preflight.json',gate);write_json(root/'launch-plan.json',launch_plan(source))
        assert gate['status']=='BLOCKED'
        summary={'status':'SUCCEEDED','release':'0.7.0a1','elapsed_seconds':time.monotonic()-start,
          'environment_lifecycle':{'venv':'CREATE_REPAIR_ROLLBACK_EXECUTED','uv':'EXECUTED' if uv else 'UNAVAILABLE'},
          'guided_native_paper':{'detections':len(raw['boxes']),'cvrs_imported':raw['cvrs_imported'],
             'original_spec_unchanged':file_digest(spec)==original,'input_sha256':file_digest(image),'bundle':verify_directory(root/'paper-result')},
          'geometry_payload_roundtrips':audits,'native_sdk_execution':'NOT_RUN',
          'golden_demo_status':golden['status'],'browser':site,'public_release':gate['status'],
          'contribution_check':contribution_check(source)['status'],
          'limits':'Owned CPU fixtures/random initialization; no pretrained framework, service, GPU, independent scientific or remote publication proof.'}
        write_json(root/'summary.json',summary);return summary
    except BaseException as exc:
        write_json(root/'failure.json',{'status':'FAILED','error':str(exc),'elapsed_seconds':time.monotonic()-start});raise


if __name__=='__main__':
    print(json.dumps(run(sys.argv[1]),indent=2))
