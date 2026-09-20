"""Reports from sealed runs, with every missing/failed case explicitly listed."""
from collections import defaultdict
from pathlib import Path
from cvsubstrate.campaigns.engine import _latest_attempts
from cvsubstrate.governance.ledger import Ledger
from cvsubstrate.data.synthetic import pointer,MISSING
from cvsubstrate.provenance.bundle import verify_bundle
from cvsubstrate.provenance.io import read_json,safe_join,digest
from cvsubstrate.analysis.statistics import summarize_seeds,paired_seed_difference
from cvsubstrate.errors import CVRSError


def campaign_report(root:Path):
    root=Path(root);plan=read_json(root/'plan.json');latest=_latest_attempts(Ledger(root/'events.jsonl').rows())
    results=[];groups=defaultdict(dict);by_arm=defaultdict(dict)
    for case in plan['cases']:
        row=latest.get(case['case_id']);entry={'case_id':case['case_id'],'backend':case['backend'],'arm':case['arm'],
            'seed':case['seed'],'metric':None,'status':'NOT_RUN','error':None,'measured_counts':None}
        if row:
            entry['status']=row['event'].removeprefix('CASE_')
            if row['event']=='CASE_SUCCEEDED':
                run=safe_join(root,row['payload']['run']);v=verify_bundle(run)
                if v['status']!='VERIFIED' or v['run_state']!='SUCCEEDED':raise CVRSError('REPORT_EVIDENCE','run evidence invalid')
                actual=read_json(run/'run.json')
                if actual['experiment_digest']!=case['experiment_digest']:raise CVRSError('REPORT_IDENTITY','case and run disagree')
                metrics=read_json(run/'metrics.json');value=pointer(metrics,plan['primary_metric_pointer'])
                if value is MISSING:entry['error']='declared primary metric missing from result'
                elif value is None:entry['error']='primary metric undefined (see evaluator denominator/support)'
                elif isinstance(value,bool) or not isinstance(value,(int,float)):entry['error']='primary metric is not numeric'
                else:entry['metric']=float(value)
                worker=read_json(run/'worker_result.json');entry['measured_counts']=worker.get('measured_counts')
                entry['source_dataset_purpose']=read_json(run/'dataset_manifest.json').get('purpose')
                entry['run']=row['payload']['run'];entry['wall_seconds']=row['payload'].get('wall_seconds')
            else:entry['error']=row['payload'].get('error',row['payload'].get('reason'))
        results.append(entry);groups[(case['backend'],case['arm'])][case['seed']]=entry['metric']
    summaries=[];comparisons=[]
    for (backend,arm),values in sorted(groups.items()):
        summaries.append({'backend':backend,'arm':arm,**summarize_seeds(values)})
    pairs=[('R','R+S'),('R','S->R'),('R-replay','R+S'),('R->R','S->R')]
    for backend in sorted({b for b,a in groups}):
        for left,right in pairs:
            if (backend,left) in groups and (backend,right) in groups:
                comparisons.append({'backend':backend,'left_arm':left,'right_arm':right,
                    **paired_seed_difference(groups[(backend,left)],groups[(backend,right)])})
    scope='SOFTWARE_FIXTURE_EVIDENCE' if any(x.get('source_dataset_purpose')=='software_fixture' for x in results) else 'RESEARCH_RUN_EVIDENCE_REQUIRES_SCIENTIFIC_REVIEW'
    return {'schema_version':'1.0','kind':'CAMPAIGN_REPORT','campaign_digest':plan['campaign_digest'],
        'phase':plan['phase'],'scope':scope,'primary_metric_pointer':plan['primary_metric_pointer'],
        'results':results,'seed_summaries':summaries,'paired_comparisons':comparisons,
        'ledger':Ledger(root/'events.jsonl').verify(),'limits':[
            'Failed, blocked and missing seeds remain visible; no best-seed selection.',
            'Matching evaluation does not imply matched pretraining, model capacity or compute.',
            'Fixture runs prove infrastructure, not real aerial transfer or detector quality.']}
