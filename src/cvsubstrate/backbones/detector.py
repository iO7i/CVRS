"""Actual torchvision detector assembled around a local feature provider.

This is a research adapter, not a reproduced published foundation detector.
Explicit normalization/resize settings prevent hidden preprocessing guesses.
"""
from collections import OrderedDict
from cvsubstrate.contracts.groundwork import BackboneDescriptor

def build_detector(descriptor,num_classes):
    import torch
    from torch import nn
    from torchvision.ops import FeaturePyramidNetwork,MultiScaleRoIAlign
    from torchvision.models.detection import FasterRCNN
    from torchvision.models.detection.anchor_utils import AnchorGenerator
    from cvsubstrate.worker_shims.backbone_impl import create_provider
    d=BackboneDescriptor.model_validate(descriptor).model_dump(mode='json');p=d['input_contract']
    if not {'mean','std','min_size','max_size','anchor_sizes'}<=set(p):raise ValueError('foundation detector needs explicit mean/std/min_size/max_size/anchor_sizes')
    encoder=create_provider(d);channels=encoder.channels
    sizes=tuple(tuple(int(x) for x in v) for v in p['anchor_sizes'])
    if len(sizes)!=len(channels):raise ValueError('one explicit anchor-size tuple per feature map required')
    out_channels=int(p.get('fpn_channels',128))
    class Backbone(nn.Module):
        def __init__(self):
            super().__init__();self.encoder=encoder;self.fpn=FeaturePyramidNetwork(channels,out_channels);self.out_channels=out_channels
        def forward(self,x):return self.fpn(self.encoder(x))
    model=FasterRCNN(Backbone(),num_classes=num_classes,min_size=int(p['min_size']),max_size=int(p['max_size']),
        image_mean=p['mean'],image_std=p['std'],rpn_anchor_generator=AnchorGenerator(sizes=sizes,aspect_ratios=tuple((0.5,1.0,2.0) for _ in sizes)),
        box_roi_pool=MultiScaleRoIAlign(featmap_names=[str(i) for i in range(len(channels))],output_size=7,sampling_ratio=2))
    model.cvrs_pretrained_backbone_loaded=encoder.pretrained_loaded
    return model
