"""Summarize real JUnit outcomes; does not turn tests into scientific certifications."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def summarize(path):
    root=ET.parse(path).getroot();cases=list(root.iter('testcase'))
    failed=[x for x in cases if x.find('failure') is not None or x.find('error') is not None]
    skipped=[x for x in cases if x.find('skipped') is not None]
    passed=len(cases)-len(failed)-len(skipped)
    return {'status':'FAIL' if failed else 'PASS_WITH_SKIPS' if skipped else 'PASS','total':len(cases),'passed':passed,
        'failed':len(failed),'skipped':len(skipped),'failed_cases':[x.attrib for x in failed],
        'skipped_cases':[{'case':x.get('name'),'reason':x.find('skipped').get('message')} for x in skipped],
        'badge_endpoint':{'schemaVersion':1,'label':'CPU tests','message':f'{passed} passed / {len(skipped)} skipped','color':'red' if failed else 'yellow' if skipped else 'green'},
        'limits':'Only these executed test outcomes. Not project completion, real benchmark reproduction, independent verification, or model quality.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('junit',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
    v=summarize(a.junit);text=json.dumps(v,indent=2)+'\n'
    if a.out:
        if a.out.exists():p.error('output exists')
        a.out.write_text(text)
    print(text)
