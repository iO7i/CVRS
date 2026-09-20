"""Finite MM API drivers, stdlib-only until a selected native operation executes.

Controller code may inspect driver metadata without importing a legacy runtime.
Run these in the configured trusted MM interpreter. Training remains the native
upstream entrypoint, not a replacement trainer.
"""
import importlib,runpy,sys
from pathlib import Path

class MMDetection2Driver:
    family='mmdet2';major='2';config_module='mmcv'
    def capabilities(self):return {'family':self.family,'operations':['resolve','construct','predict','train','checkpoint'],'task':'hbb_detection'}
    def validate_version(self):
        version=importlib.import_module('mmdet').__version__
        if self.major and version.split('.')[0]!=self.major:raise RuntimeError('MM_VERSION: '+self.family+' cannot execute '+version)
        return version
    def resolve(self,path):
        self.validate_version();return getattr(importlib.import_module(self.config_module),'Config').fromfile(str(path))
    def construct(self,config,checkpoint,device='cpu'):
        self.validate_version();return importlib.import_module('mmdet.apis').init_detector(config,checkpoint,device=device)
    def predict(self,model,image):return importlib.import_module('mmdet.apis').inference_detector(model,image)
    def checkpoint(self,model,path,metadata=None):
        return importlib.import_module('mmcv.runner').save_checkpoint(model,str(path),meta=metadata or {})
    def train(self,entry,argv):
        old=sys.argv;sys.argv=[str(entry),*argv]
        try:runpy.run_path(str(entry),run_name='__main__')
        finally:sys.argv=old
    def configure_updates(self,config,updates,accumulation=1):
        if updates<=0 or accumulation!=1:raise ValueError('MM2 built-in update recipe requires positive updates and accumulation=1')
        hook=config.get('optimizer_config',{}) or {}
        if hook.get('cumulative_iters',1)!=1:raise ValueError('MM2 fixed-update recipe does not support cumulative optimizer hooks')
        config.runner=dict(type='IterBasedRunner',max_iters=updates)
        return config

class MMDetection3Driver(MMDetection2Driver):
    family='mmdet3';major='3';config_module='mmengine.config'
    def checkpoint(self,model,path,metadata=None):
        return importlib.import_module('mmengine.runner').save_checkpoint({'state_dict':model.state_dict(),'meta':metadata or {}},str(path))
    def configure_updates(self,config,updates,accumulation=1):
        if updates<=0 or accumulation<=0:raise ValueError('positive updates/accumulation required')
        config.train_cfg=dict(type='IterBasedTrainLoop',max_iters=updates*accumulation,val_interval=updates*accumulation)
        config.optim_wrapper['accumulative_counts']=accumulation
        return config

class OneDLDetectionDriver(MMDetection3Driver):
    family='onedl';major=None
    # The inherited MM3 API is an explicit compatibility assumption. Identity
    # is independently checked from source/distribution by the heritage worker.

DRIVERS={'mmdet2':MMDetection2Driver,'mmdet3':MMDetection3Driver,'onedl':OneDLDetectionDriver}
def get_driver(family):
    if family not in DRIVERS:raise ValueError('unsupported MM driver '+str(family))
    return DRIVERS[family]()
