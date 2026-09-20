"""Evidence-based methodology linting. Warnings are not misconduct findings."""
from typing import Any
from cvsubstrate.adoption.contracts import MethodologySpec
from cvsubstrate.provenance.io import digest

def evaluation_equivalence(a,b):
    fields=('task','evaluator','evaluator_version','iou_thresholds','recall_thresholds','area_ranges','max_detections',
            'score_threshold','ignore_policy','use_categories','tile_merge_policy','image_universe','taxonomy_digest')
    missing=[k for k in fields if k not in a or k not in b]
    different=[{'field':k,'left':a[k],'right':b[k]} for k in fields if k in a and k in b and a[k]!=b[k]]
    return {'status':'INCOMPATIBLE' if different else ('UNKNOWN' if missing else 'EQUIVALENT_DECLARED_PROTOCOL'),
            'differences':different,'missing_fields':missing,'native_implementation_parity':'NOT_INFERRED'}

def lint_methodology(value):
    s=MethodologySpec.model_validate(value);findings=[]
    def add(code,severity,message,evidence):findings.append({'code':code,'severity':severity,'message':message,'evidence':evidence})
    if s.dataset_digest and s.baseline_dataset_digest and s.dataset_digest!=s.baseline_dataset_digest:
        add('DATASET_CHANGED','WARN','The evaluation population differs from the baseline',[s.baseline_dataset_digest,s.dataset_digest])
    if s.evaluation or s.baseline_evaluation:
        eq=evaluation_equivalence(s.evaluation,s.baseline_evaluation)
        if eq['status']!='EQUIVALENT_DECLARED_PROTOCOL':add('EVALUATION_'+eq['status'],'WARN','Metric equivalence is not established',eq)
    if len(s.arms)>1:
        for field in ('real_exposures','optimizer_updates','total_samples','compute_seconds'):
            known=[(a.get('id'),a[field]) for a in s.arms if field in a and a[field] is not None]
            if len({v for _,v in known})>1 and field not in s.declared_interventions:
                add('UNMATCHED_'+field.upper(),'WARN','Arms differ in '+field,known)
        if any(a.get('exposure_source')=='planned' for a in s.arms):
            add('PLANNED_NOT_MEASURED','INFO','Planned exposure is not observed data consumption',s.arms)
    for p in s.prompts:
        if p.get('source') in {'ground_truth','ground_truth_oracle','oracle','ORACLE'}:
            add('ORACLE_PROMPT','WARN','Ground-truth-derived prompts require an explicit oracle comparison track',p)
        elif not p.get('source'):add('PROMPT_SOURCE_UNKNOWN','WARN','Prompt origin is not recorded',p)
    for a in s.assets:
        if not a.get('sha256') or a.get('revision') in {'main','master','latest'}:
            add('UNLOCKED_ASSET','WARN','Asset lacks a content-pinned revision or digest',a)
    for access in s.test_accesses:
        if access.get('before_selection') is True or access.get('purpose') in {'tuning','selection'}:
            add('TEST_SELECTION_ACCESS','WARN','Protected-test data was accessed during selection',access)
    groups: dict[tuple[str, Any], set[str]]={}
    for x in s.lineage:
        for key in ('parent','scene','asset','background','photogrammetry_source'):
            if x.get(key):groups.setdefault((key,x[key]),set()).add(x.get('split','unknown'))
    for (kind,key),splits in groups.items():
        if 'train' in splits and splits&{'test','locked_test','selection','dev'}:
            add('CROSS_SPLIT_LINEAGE','WARN','Declared shared lineage crosses train/evaluation splits',{'kind':kind,'id':key,'splits':sorted(splits)})
    return {'status':'REVIEW_REQUIRED' if any(f['severity']=='WARN' for f in findings) else 'NO_DECLARED_ISSUES',
            'findings':findings,'input_digest':digest(s),'limits':'Only declared information is checked. Missing evidence cannot establish absence of leakage or fairness.'}

def experiment_diff(a,b):
    changes=[]
    def visit(x,y,path=''):
        if isinstance(x,dict) and isinstance(y,dict):
            for k in sorted(set(x)|set(y)):
                if k not in x or k not in y:changes.append({'path':path+'/'+k,'left':x.get(k),'right':y.get(k),'kind':'added_or_removed'})
                else:visit(x[k],y[k],path+'/'+k)
        elif x!=y:changes.append({'path':path,'left':x,'right':y,'kind':'changed'})
    visit(a,b)
    return {'left_digest':digest(a),'right_digest':digest(b),'identical':not changes,'changes':changes,
            'training_fairness':'NOT_AUTOMATICALLY_INFERRED'}

def reviewer_report(root):
    from pathlib import Path
    from cvsubstrate.provenance.artifact_set import verify_directory
    from cvsubstrate.provenance.bundle import verify_bundle
    from cvsubstrate.provenance.io import read_json
    p=Path(root)
    integrity=verify_directory(p) if (p/'integrity.json').is_file() else (verify_bundle(p) if (p/'artifacts.json').is_file() else {'status':'MISSING'})
    methodology=lint_methodology(read_json(p/'methodology.json')) if (p/'methodology.json').is_file() else {'status':'MISSING_DECLARATIONS'}
    return {'integrity':integrity,'methodology':methodology,'verdict':'REVIEW_EVIDENCE_NOT_SCIENTIFIC_CERTIFICATION',
            'missing':[x for x in ('environment.json','model.json','dataset_manifest.json') if not (p/x).exists()]}
