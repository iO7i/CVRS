"""Small genuine Mask R-CNN used for CPU protocol conformance.

This is not a pretrained model, an alternative implementation of SAM, or an
accuracy benchmark. It gives the mask interface an executable native smoke path.
"""
def build_mask_detector(num_classes):
    from torchvision.models.detection import MaskRCNN
    from torchvision.models.detection.mask_rcnn import MaskRCNNHeads,MaskRCNNPredictor
    from torchvision.ops import MultiScaleRoIAlign
    from cvsubstrate.workers.native_torch import model_factory
    bbox=model_factory(num_classes)
    return MaskRCNN(bbox.backbone,num_classes=None,
        rpn_anchor_generator=bbox.rpn.anchor_generator,box_roi_pool=bbox.roi_heads.box_roi_pool,
        box_head=bbox.roi_heads.box_head,box_predictor=bbox.roi_heads.box_predictor,
        mask_roi_pool=MultiScaleRoIAlign(['0'],output_size=7,sampling_ratio=2),
        mask_head=MaskRCNNHeads(16,[16],dilation=1),mask_predictor=MaskRCNNPredictor(16,8,num_classes),
        min_size=64,max_size=96,image_mean=[0.,0.,0.],image_std=[1.,1.,1.],
        rpn_pre_nms_top_n_train=32,rpn_pre_nms_top_n_test=32,rpn_post_nms_top_n_train=16,rpn_post_nms_top_n_test=16,
        rpn_batch_size_per_image=16,box_batch_size_per_image=16,box_detections_per_img=8,box_score_thresh=0.)
