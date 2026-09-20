"""Semantic segmentation interchange and confusion-matrix diagnostics.

Class-index maps are not Mask R-CNN instances. Ignore/reduce-zero policy is explicit.
"""
from pathlib import Path
from cvsubstrate.provenance.io import file_digest,write_json,digest

def semantic_metrics(pairs,num_classes,ignore_index=255,reduce_zero_label=False):
    import numpy as np
    cm=np.zeros((num_classes,num_classes),dtype=np.int64);pixels=0
    for truth,pred in pairs:
        gt=np.asarray(truth,dtype=np.int64).copy();pr=np.asarray(pred,dtype=np.int64)
        if gt.shape!=pr.shape:raise ValueError('semantic maps have different geometry')
        if reduce_zero_label:
            zero=(gt==0);ignored=(gt==ignore_index);gt-=1;gt[zero|ignored]=ignore_index
        valid=gt!=ignore_index
        if np.any((gt[valid]<0)|(gt[valid]>=num_classes)) or np.any((pr[valid]<0)|(pr[valid]>=num_classes)):
            raise ValueError('unknown semantic label outside declared taxonomy')
        cm+=np.bincount(num_classes*gt[valid]+pr[valid],minlength=num_classes*num_classes).reshape(num_classes,num_classes)
        pixels+=int(valid.sum())
    union=cm.sum(1)+cm.sum(0)-cm.diagonal();ious=[float(cm[i,i]/union[i]) if union[i] else None for i in range(num_classes)]
    known=[x for x in ious if x is not None]
    return {'metric_family':'cvrs_semantic_confusion_diagnostic_v1','official_benchmark':False,'confusion_matrix':cm.tolist(),
            'class_iou':ious,'mean_iou':sum(known)/len(known) if known else None,'evaluated_pixels':pixels,
            'ignore_index':ignore_index,'reduce_zero_label':reduce_zero_label}
