"""Explicit concept taxonomy and diagnostic open-set detection evaluation.

No embedding-based synonyms, implicit ancestor collapse, or oracle relabeling.
Every phrase resolution references an immutable declared ontology identity.
"""
from __future__ import annotations
from typing import Literal
from pydantic import Field,model_validator
from cvsubstrate.contracts.models import Contract,ID
from cvsubstrate.provenance.io import digest

class Concept(Contract):
    id: ID
    name: str
    aliases: list[str]=Field(default_factory=list)
    parents: list[ID]=Field(default_factory=list)
    partition: Literal['known','unknown']='known'
    @model_validator(mode='after')
    def valid(self):
        if not self.name.strip() or any(not a.strip() for a in self.aliases):raise ValueError('concept names and aliases must be nonempty')
        if len(self.parents)!=len(set(self.parents)):raise ValueError('duplicate concept parent')
        return self

class ConceptOntology(Contract):
    name: ID
    concepts: list[Concept]
    phrase_to_concept: dict[str,ID]=Field(default_factory=dict)
    category_to_concept: dict[str,ID]=Field(default_factory=dict)
    case_sensitive: bool=True
    @model_validator(mode='after')
    def valid(self):
        ids={c.id for c in self.concepts}
        if len(ids)!=len(self.concepts):raise ValueError('duplicate concept')
        if set(self.phrase_to_concept.values())-ids or set(self.category_to_concept.values())-ids:raise ValueError('mapping references unknown concept')
        children={c.id:c.parents for c in self.concepts};visiting=set();done=set()
        def visit(k):
            if k in visiting:raise ValueError('ontology cycle')
            if k in done:return
            if k not in children:raise ValueError('unknown parent')
            visiting.add(k)
            for p in children[k]:visit(p)
            visiting.remove(k);done.add(k)
        for k in ids:visit(k)
        aliases={}
        for c in self.concepts:
            for name in [c.name,*c.aliases]:
                key=name if self.case_sensitive else name.casefold()
                if key in aliases and aliases[key]!=c.id:raise ValueError('ambiguous alias')
                aliases[key]=c.id
        for phrase,concept in self.phrase_to_concept.items():
            key=phrase if self.case_sensitive else phrase.casefold()
            if key in aliases and aliases[key]!=concept:raise ValueError('phrase mapping conflicts with alias')
            aliases[key]=concept
        return self
    @property
    def identity(self):return digest(self)
    def resolve(self,phrase):
        key=phrase if self.case_sensitive else phrase.casefold()
        mapping={}
        for c in self.concepts:
            for name in [c.name,*c.aliases]:mapping[name if self.case_sensitive else name.casefold()]=c.id
        for name,concept in self.phrase_to_concept.items():mapping[name if self.case_sensitive else name.casefold()]=concept
        return mapping.get(key)

def iou(a,b):
    inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
    return inter/union if union>0 else 0.

def evaluate_open_set(predictions,annotations,ontology:ConceptOntology,*,iou_threshold=.5,prompt_source='NON_ORACLE',score_threshold=0.0):
    if not 0<iou_threshold<=1 or not 0<=score_threshold<=1:raise ValueError('invalid threshold')
    if prompt_source not in {'ORACLE','NON_ORACLE','EXTERNAL','GENERATED'}:raise ValueError('explicit prompt provenance required')
    import math
    for row in [*predictions,*annotations]:
        b=row.get('box')
        if not isinstance(b,list) or len(b)!=4 or not all(type(x) in (int,float) and math.isfinite(x) for x in b) or not (0<=b[0]<b[2] and 0<=b[1]<b[3]):raise ValueError('invalid canonical detection geometry')
        if not isinstance(row.get('sample_id'),str):raise ValueError('sample identity required')
    for p in predictions:
        if type(p.get('score')) not in (int,float) or not math.isfinite(p['score']) or not 0<=p['score']<=1 or not isinstance(p.get('phrase'),str):raise ValueError('invalid grounded prediction')
    kinds={c.id:c.partition for c in ontology.concepts};matched=set();rows=[];unmapped=0
    support={'known':0,'unknown':0};tp={'known':0,'unknown':0};fp={'known':0,'unknown':0};unknown_as_known=0
    for g in annotations:
        if g['concept_id'] not in kinds:raise ValueError('unknown GT concept')
        support[kinds[g['concept_id']]]+=1
    for p in sorted(predictions,key=lambda x:(-x['score'],str(x.get('id','')))):
        if p['score']<score_threshold:continue
        concept=ontology.resolve(p['phrase'])
        if concept is None:unmapped+=1;rows.append({'id':p.get('id'),'status':'UNMAPPED_PHRASE'});continue
        candidates=[(iou(p['box'],g['box']),i) for i,g in enumerate(annotations) if i not in matched and g['sample_id']==p['sample_id'] and g['concept_id']==concept]
        best=max(candidates,default=(0.,-1))
        if best[0]>=iou_threshold:matched.add(best[1]);tp[kinds[concept]]+=1;status='TRUE_POSITIVE'
        else:
            fp[kinds[concept]]+=1;status='FALSE_POSITIVE'
            if kinds[concept]=='known' and any(g['sample_id']==p['sample_id'] and kinds[g['concept_id']]=='unknown' and iou(p['box'],g['box'])>=iou_threshold for g in annotations):unknown_as_known+=1
        rows.append({'id':p.get('id'),'phrase':p['phrase'],'concept':concept,'status':status})
    result={k:{'support':support[k],'true_positive':tp[k],'false_positive':fp[k],
        'recall':tp[k]/support[k] if support[k] else None,'precision':tp[k]/(tp[k]+fp[k]) if tp[k]+fp[k] else None} for k in kinds.values()}
    return {'evaluator':'explicit_open_set_diagnostic_v1','ontology_sha256':ontology.identity,'partitions':result,
        'unmapped_predictions':unmapped,'unknown_misclassified_as_known':unknown_as_known,'prompt_source':prompt_source,
        'oracle_conditioned':prompt_source=='ORACLE','iou_threshold':iou_threshold,'score_threshold':score_threshold,'predictions':rows,'official_ap':False}
SCHEMAS=[Concept,ConceptOntology]


def canonical_grounding_rows(predictions,images):
    """Convert native canonical per-image grounding to audited evaluation records."""
    from cvsubstrate.contracts.frontier import GroundedPrediction
    image_map={i['id']:i for i in images};parsed=[GroundedPrediction.model_validate(p) for p in predictions]
    if len(image_map)!=len(images) or {p.sample_id for p in parsed}!=set(image_map) or len(parsed)!=len(images):raise ValueError('grounded prediction image universe mismatch')
    flat=[];sources=set();prompts=[]
    for p in parsed:
        image=image_map[p.sample_id]
        if (image['width'],image['height'])!=(p.width,p.height):raise ValueError('grounded prediction dimensions changed')
        sources.add(p.prompt.source);prompts.append(p.prompt.model_dump(mode='json'))
        for i,(box,score,phrase) in enumerate(zip(p.boxes,p.scores,p.phrases)):
            flat.append({'id':p.sample_id+':'+str(i),'sample_id':p.sample_id,'box':box,'score':score,'phrase':phrase})
    source='ORACLE' if 'ground_truth_oracle' in sources else 'GENERATED' if 'upstream_model' in sources else 'EXTERNAL' if 'human' in sources else 'NON_ORACLE'
    return flat,{'prompt_source':source,'prompt_set_sha256':digest(prompts),'samples':len(parsed),'regions':len(flat),'source_kinds':sorted(sources)}
