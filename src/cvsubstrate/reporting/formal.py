"""Evidence-linked JSON/Markdown research reports, with unknowns preserved."""
from __future__ import annotations
from pathlib import Path
from collections import defaultdict
import statistics
from cvsubstrate.provenance.io import digest,write_json
from cvsubstrate.provenance.artifact_set import seal_directory
from cvsubstrate.errors import CVRSError
KINDS={'tiling','detector_comparison','sim2real','domain_gap','foundation_backbone','deployment_fidelity','heritage','general'}

def create_report(kind,records,output:Path,*,title=None,limitations=None):
    if kind not in KINDS:raise ValueError('unknown report type')
    out=Path(output)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','report is a derived artifact; choose new output')
    out.mkdir(parents=True);identities=[digest(r) for r in records];seed_groups=defaultdict(list)
    for r in records:
        if isinstance(r,dict) and 'seed' in r:
            seed_groups[(str(r.get('backend','unknown')),str(r.get('arm','unknown')))].append(r)
    seed_summaries=[]
    for (backend,arm),group in seed_groups.items():
        seeds=[r['seed'] for r in group]
        if len(seeds)!=len(set(seeds)):raise ValueError('duplicate seed in a backend/arm report; no silent double-counting')
        values=[r.get('value') for r in group if isinstance(r.get('value'),(int,float))]
        seed_summaries.append({'backend':backend,'arm':arm,'records':group,'available_n':len(values),'total_n':len(group),
            'mean_available':statistics.mean(values) if values else None,'std_available':statistics.stdev(values) if len(values)>1 else None,
            'missing_seeds':[r['seed'] for r in group if r.get('value') is None]})
    comparisons=[]
    for i,a in enumerate(records):
        for j,b in enumerate(records[i+1:],i+1):
            if isinstance(a,dict) and isinstance(b,dict) and 'comparison_digest' in a and 'comparison_digest' in b:
                comparisons.append({'left':i,'right':j,'evaluation_comparable':a['comparison_digest']==b['comparison_digest'],'training_fairness':'NOT_ESTABLISHED'})
    report={'schema_version':'1.0','kind':kind,'title':title or kind.replace('_',' ').title(),'record_digests':identities,
        'records':records,'seed_summaries':seed_summaries,'comparisons':comparisons,
        'limitations':limitations or ['No scientific effect inferred automatically.','Missing executions and failed seeds remain missing.','Same evaluation does not imply training fairness.','Hardware, native-source, dataset and checkpoint evidence must be inspected.'],
        'certification':'NOT_AUTOMATICALLY_CERTIFIED'}
    write_json(out/'report.json',report)
    lines=['# '+report['title'],'','Status: evidence summary; not automatic scientific certification.','',f'Input artifacts: {len(records)}','',
        '## Evidence identities','']+[f'- `{i}`: `{h}`' for i,h in enumerate(identities)]
    if seed_summaries:
        lines+=['','## Seed accounting','','| Backend | Arm | Available / declared | Mean available | SD available |','|---|---|---:|---:|---:|']
        for s in seed_summaries:lines.append(f"| {s['backend']} | {s['arm']} | {s['available_n']} / {s['total_n']} | {s['mean_available']} | {s['std_available']} |")
    lines+=['','## Limitations','']+['- '+x for x in report['limitations']]+['','Full records and comparison decisions are in `report.json`.','']
    (out/'report.md').write_text('\n'.join(lines),'utf-8');seal_directory(out);return {'report':str(out/'report.json'),'record_count':len(records),'kind':kind}
