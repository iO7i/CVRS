"""Human-readable reports generated solely from supplied measured/declared records."""
import json
from pathlib import Path
from cvsubstrate.provenance.io import atomic_bytes,write_json
from cvsubstrate.provenance.artifact_set import seal_directory
from cvsubstrate.errors import CVRSError


def cell(value):
    if value is None:return '—'
    if isinstance(value,float):return f'{value:.6g}'
    return str(value).replace('|',r'\|').replace('\n',' ')


def markdown(payload,title=None):
    kind=payload.get('kind',payload.get('status','Research report'))
    lines=['# '+(title or str(kind)),'', '**Evidence scope:** '+cell(payload.get('scope','See explicitly stated limits below.')),'']
    if kind=='CAMPAIGN_REPORT':
        lines+=['## Every scheduled case','', '| Backend | Arm | Seed | Status | Metric |','|---|---|---:|---|---:|']
        for r in payload['results']:lines.append('| '+' | '.join(cell(r[k]) for k in ['backend','arm','seed','status','metric'])+' |')
        lines+=['','## Seed summary','', '| Backend | Arm | Available | Mean | Sample SD | Missing |','|---|---|---:|---:|---:|---|']
        for r in payload['seed_summaries']:lines.append('| '+' | '.join(cell(r[k]) for k in ['backend','arm','available','mean','sample_std','missing_seeds'])+' |')
    elif kind=='DESCRIPTIVE_DATASET_DIAGNOSTICS':
        lines += [f"Images: {payload['images']}. Positive objects: {payload['positive_objects']}.",'',
            '| Quantity | N | Mean | Median | P10 | P90 |','|---|---:|---:|---:|---:|---:|']
        for name,r in payload['geometry'].items():lines.append('| '+cell(name)+' | '+' | '.join(cell(r[k]) for k in ['count','mean','median','p10','p90'])+' |')
    elif kind=='TINY_FROC_DIAGNOSTICS_NOT_OFFICIAL_AP':
        p=payload['aggregate']['fixed_threshold']
        lines += [f"Images: {p['images']}; positives: {p['ground_truth']}; recall: {cell(p['recall'])}; FP/image: {cell(p['false_positives_per_image'])}.",
            '', '| GT sqrt-box-area bin (px) | Positive objects | Matched | Recall |','|---|---:|---:|---:|']
        for name,r in p['size_slices'].items():lines.append('| '+cell(name)+' | '+' | '.join(cell(r[k]) for k in ['ground_truth','matched','recall'])+' |')
    elif kind=='CANONICAL_OUTPUT_PARITY':
        lines += [f"Status: **{payload['status']}**. Pairs checked: {payload['pairs_checked']}.",
            f"Maximum box delta: {payload['maximum_box_delta']}; score delta: {payload['maximum_score_delta']}."]
    lines+=['','## Interpretation limits','']
    limits=payload.get('limits',payload.get('note','No additional verification beyond these recorded inputs is implied.'))
    lines += limits if isinstance(limits,list) else [str(limits)]
    lines+=['','## Complete machine-readable record','', '```json',json.dumps(payload,indent=2,ensure_ascii=False,allow_nan=False),'```','']
    return '\n'.join(lines)


def publish_report(payload,output:Path,title=None):
    output=Path(output)
    from cvsubstrate.provenance.artifact_set import assert_not_inside_sealed
    assert_not_inside_sealed(output)
    if output.exists():raise CVRSError('OUTPUT_EXISTS','reports create a new derived artifact set')
    output.mkdir(parents=True)
    write_json(output/'report.json',payload);atomic_bytes(output/'report.md',markdown(payload,title).encode())
    seal_directory(output)
    return {'report':str(output/'report.md'),'json':str(output/'report.json'),'kind':payload.get('kind'),'sealed':True}
