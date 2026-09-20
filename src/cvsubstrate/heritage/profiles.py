"""Declared API families. Profiles are not dependency compatibility certificates."""
PROFILES={
 'mmdet2':{'upstream':'open-mmlab/mmdetection','version_prefix':'2.','config_resolver':'mmcv.Config','prediction_shape':'per_class_bbox_arrays','packages':['torch','mmcv-full','mmdet'],'training_entrypoint':'tools/train.py'},
 'mmdet3':{'upstream':'open-mmlab/mmdetection','version_prefix':'3.','config_resolver':'mmengine.Config','prediction_shape':'DetDataSample.pred_instances','packages':['torch','mmcv','mmengine','mmdet'],'training_entrypoint':'tools/train.py'},
 'onedl':{'upstream':'VBTI-development/onedl-mmdetection','version_prefix':None,'config_resolver':'mmengine.Config','prediction_shape':'DetDataSample.pred_instances','packages':['torch','onedl-mmcv','onedl-mmengine','onedl-mmdetection'],'training_entrypoint':'tools/train.py'}
}

def detect_profile(version,upstream):
    if upstream=='VBTI-development/onedl-mmdetection':return 'onedl'
    if str(version).startswith('2.'):return 'mmdet2'
    if str(version).startswith('3.'):return 'mmdet3'
    raise ValueError('unrecognized MMDetection family; explicit profile needed')

def get_profile(name):
    if name not in PROFILES:raise ValueError('profile must be mmdet2, mmdet3 or onedl')
    return {'id':name,**PROFILES[name],'execution_status':'NOT_RUN'}
