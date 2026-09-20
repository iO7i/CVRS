"""Diagnostic oriented precision/recall. Never presented as DOTA official AP."""
from cvsubstrate.contracts.research import OrientedDataset,OrientedPrediction
from cvsubstrate.data.dota import validate_oriented_predictions
from cvsubstrate.geometry.polygons import polygon_iou
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import digest


def oriented_diagnostics(m:OrientedDataset,rows:list[OrientedPrediction], *, iou_threshold=.5,score_threshold=.5):
    if m.role!='dev':raise CVRSError('EVAL_ROLE','diagnostics accept dev only')
    if not 0<iou_threshold<=1 or not 0<=score_threshold<=1:raise ValueError('invalid thresholds')
    validate_oriented_predictions(m,rows);pred={r.sample_id:r for r in rows}
    tp=fp=ignored=total=0
    for sample in m.samples:
        gt=[a for a in sample.annotations if not a.difficult];difficult=[a for a in sample.annotations if a.difficult]
        used=set();total+=len(gt);r=pred[sample.id]
        for i in sorted(range(len(r.scores)),key=lambda k:(-r.scores[k],k)):
            if r.scores[i]<score_threshold:continue
            candidates=[(polygon_iou(r.polygons[i],g.polygon),j) for j,g in enumerate(gt) if j not in used and g.category_id==r.category_ids[i]]
            overlap,index=max(candidates,default=(-1,-1),key=lambda x:(x[0],-x[1]))
            if overlap>=iou_threshold:tp+=1;used.add(index)
            elif any(g.category_id==r.category_ids[i] and polygon_iou(r.polygons[i],g.polygon)>=iou_threshold for g in difficult):ignored+=1
            else:fp+=1
    return {'kind':'DIAGNOSTIC_ORIENTED_NOT_DOTA_AP','dataset_digest':digest(m),
        'iou_threshold':iou_threshold,'score_threshold':score_threshold,'images':len(m.samples),
        'true_positives':tp,'false_positives':fp,'ignored_detections':ignored,'positive_ground_truth':total,
        'recall':tp/total if total else None,'precision':tp/(tp+fp) if tp+fp else None,
        'false_positives_per_image':fp/len(m.samples),'official_reference_verified':False}
