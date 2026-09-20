"""Loss-aware HBB, quadrilateral, mask and grounded-label interchange.

Native SDK serialization is separate from canonical semantics. Native views can
be edited; imports use the actual edited geometry, not a cached original record.
Masks are bounded on decoding and encoded in canonical column-major RLE.
"""
from __future__ import annotations
import math
from pathlib import Path
from typing import Any, Literal
from pydantic import Field, model_validator
from cvsubstrate.product.contracts import ProductContract
from cvsubstrate.contracts.frontier import MaskRLE
from cvsubstrate.provenance.io import digest, read_json, write_json
from cvsubstrate.errors import CVRSError


class RichObject(ProductContract):
    id: str = Field(min_length=1)
    category_id: int | None = None
    score: float = Field(ge=0, le=1)
    box: list[float] | None = None
    polygon: list[list[float]] | None = None
    mask: MaskRLE | None = None
    phrase: str | None = None
    prompt_digest: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def geometry(self):
        if self.box is None and self.polygon is None and self.mask is None:
            raise ValueError("at least one actual geometry representation is required")
        if self.box is not None:
            if len(self.box) != 4 or not all(math.isfinite(v) for v in self.box) or self.box[2] <= self.box[0] or self.box[3] <= self.box[1]:
                raise ValueError("invalid continuous xyxy box")
        if self.polygon is not None:
            from cvsubstrate.geometry.polygons import canonical_polygon
            if len(self.polygon) != 4:
                raise ValueError("OBB geometry needs four corners")
            canonical_polygon(self.polygon)
        return self


class RichFrame(ProductContract):
    sample_id: str = Field(min_length=1)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    image: str | None = None
    image_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    task: Literal["hbb_detection", "obb_detection", "instance_segmentation", "grounded_detection"]
    objects: list[RichObject]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def semantics(self):
        ids = [o.id for o in self.objects]
        if len(set(ids)) != len(ids):
            raise ValueError("object IDs must be unique per image")
        for o in self.objects:
            if o.mask and (o.mask.width != self.width or o.mask.height != self.height):
                raise ValueError("mask must use full original-image coordinates")
            if self.task == "obb_detection" and o.polygon is None:
                raise ValueError("OBB interchange requires actual polygon corners")
            if self.task == "instance_segmentation" and o.mask is None:
                raise ValueError("instance segmentation needs a mask for every instance")
            if self.task == "hbb_detection" and o.box is None:
                raise ValueError("HBB requires explicit boxes")
            if self.task == "grounded_detection" and not o.phrase:
                raise ValueError("grounding requires a phrase, not an invented closed-set class")
        return self


class RichInterchange(ProductContract):
    dataset_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    categories: dict[int, str] = Field(default_factory=dict)
    frames: list[RichFrame]
    licenses: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def references(self):
        ids = [f.sample_id for f in self.frames]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate sample IDs")
        if len(set(self.categories.values())) != len(self.categories):
            raise ValueError("category names must be unambiguous")
        for f in self.frames:
            for o in f.objects:
                if o.category_id is not None and o.category_id not in self.categories:
                    raise ValueError("unmapped category ID")
        return self


SCHEMAS = [RichObject, RichFrame, RichInterchange]


def _bbox(o: RichObject) -> list[float]:
    if o.box is not None:
        return o.box
    if o.polygon is not None:
        return [min(p[0] for p in o.polygon), min(p[1] for p in o.polygon),
                max(p[0] for p in o.polygon), max(p[1] for p in o.polygon)]
    from cvsubstrate.vision.masks import decode_mask
    import numpy as np
    if o.mask is None:
        raise ValueError("object has no geometry")
    mask = o.mask
    a = decode_mask(mask)
    yy, xx = np.nonzero(a)
    if not len(xx):
        # Empty masks are valid outputs; transport them with an explicit whole
        # image bounding window rather than silently dropping the instance.
        return [0, 0, mask.width, mask.height]
    return [int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1]


def _metadata(o: RichObject) -> dict:
    return {"id": o.id, "category_id": o.category_id, "phrase": o.phrase,
            "prompt_digest": o.prompt_digest, "attributes": o.attributes,
            "had_box": o.box is not None, "had_polygon": o.polygon is not None,
            "original_box": o.box}


def to_supervision_payload(value: dict | RichInterchange, *, max_mask_pixels: int = 64 * 1024 * 1024) -> dict:
    from cvsubstrate.vision.masks import decode_mask
    bundle = RichInterchange.model_validate(value)
    rows = []
    for f in bundle.frames:
        masks = [o.mask is not None for o in f.objects]
        polygons = [o.polygon is not None for o in f.objects]
        if any(masks) and not all(masks):
            raise CVRSError("MIXED_GEOMETRY", "a Supervision batch cannot silently invent missing instance masks")
        if any(polygons) and not all(polygons):
            raise CVRSError("MIXED_GEOMETRY", "split partial OBB/HBB batches into separately declared fields")
        if any(masks) and f.width * f.height * len(f.objects) > max_mask_pixels:
            raise CVRSError("MASK_BUDGET", "dense native Supervision masks exceed the explicit pixel budget")
        rows.append({"sample_id": f.sample_id, "width": f.width, "height": f.height,
            "image": f.image, "image_sha256": f.image_sha256, "task": f.task, "metadata": f.metadata,
            "xyxy": [_bbox(o) for o in f.objects], "confidence": [o.score for o in f.objects],
            "class_id": [o.category_id if o.category_id is not None else -1 for o in f.objects],
            "mask": [decode_mask(o.mask, max_mask_pixels).astype('uint8').tolist() for o in f.objects] if any(masks) else None,
            "xyxyxyxy": [o.polygon for o in f.objects] if any(polygons) else None,
            "cvrs_objects": [_metadata(o) for o in f.objects]})
    return {"format": "cvrs-supervision-rich/1", "records": rows,
            "categories": {str(k): v for k, v in bundle.categories.items()}, "dataset_digest": bundle.dataset_digest,
            "licenses": bundle.licenses, "provenance": bundle.provenance,
            "source_digest": digest(bundle), "losses": []}


def from_supervision_payload(payload: dict, *, max_mask_pixels: int = 64 * 1024 * 1024) -> RichInterchange:
    from cvsubstrate.vision.masks import encode_mask
    frames = []
    if payload.get("format") != "cvrs-supervision-rich/1":
        raise ValueError("unsupported Supervision interchange format")
    for r in payload["records"]:
        n = len(r["xyxy"])
        if any(len(r[k]) != n for k in ("confidence", "class_id", "cvrs_objects")):
            raise ValueError("native prediction counts do not reconcile")
        if any(r.get(k) is not None and len(r[k]) != n for k in ("mask", "xyxyxyxy")):
            raise ValueError("native geometry counts do not reconcile")
        if r.get("mask") is not None and r["width"] * r["height"] * n > max_mask_pixels:
            raise CVRSError("MASK_BUDGET", "native dense mask batch exceeds the explicit budget")
        objects = []
        for i in range(n):
            m = r["cvrs_objects"][i]
            category: int | None = int(r["class_id"][i])
            if category == -1 and m.get("category_id") is None:
                category = None
            box = r["xyxy"][i] if m["had_box"] else None
            polygon = r["xyxyxyxy"][i] if r.get("xyxyxyxy") is not None else None
            mask = encode_mask(r["mask"][i]) if r.get("mask") is not None else None
            objects.append(RichObject(id=m["id"], category_id=category, score=r["confidence"][i],
                box=box, polygon=polygon, mask=mask, phrase=m.get("phrase"), prompt_digest=m.get("prompt_digest"), attributes=m.get("attributes", {})))
        frames.append(RichFrame(**{k: r[k] for k in ("sample_id", "width", "height", "task", "image", "image_sha256", "metadata")}, objects=objects))
    return RichInterchange(dataset_digest=payload["dataset_digest"], categories=payload["categories"], frames=frames,
                           licenses=payload.get("licenses", {}), provenance=payload.get("provenance", {}))


def to_fiftyone_payload(value: dict | RichInterchange, *, max_mask_pixels: int = 64 * 1024 * 1024) -> dict:
    from cvsubstrate.vision.masks import decode_mask, encode_mask
    bundle = RichInterchange.model_validate(value)
    rows = []
    for f in bundle.frames:
        labels = []
        for obj in f.objects:
            meta = _metadata(obj)
            label = bundle.categories[obj.category_id] if obj.category_id is not None else obj.phrase
            if obj.polygon is not None:
                # Full OBB geometry is retained as a filled closed polyline.
                geometry = {"kind": "polyline", "points": [[[x/f.width, y/f.height] for x, y in obj.polygon]], "closed": True, "filled": True}
            else:
                x1, y1, x2, y2 = _bbox(obj)
                geometry = {"kind": "detection", "bounding_box": [x1/f.width, y1/f.height, (x2-x1)/f.width, (y2-y1)/f.height]}
            if obj.mask is not None:
                if f.width*f.height > max_mask_pixels:
                    raise CVRSError("MASK_BUDGET", "mask exceeds the explicit decode budget")
                a = decode_mask(obj.mask, max_mask_pixels)
                import numpy as np
                yy, xx = np.nonzero(a)
                x1, y1, x2, y2 = (int(xx.min()), int(yy.min()), int(xx.max())+1, int(yy.max())+1) if len(xx) else (0, 0, f.width, f.height)
                # Native Detection.mask is local to its bounding rectangle. Use
                # integer bounds so pixel identity survives, with no stretching.
                geometry = {"kind": "detection", "bounding_box": [x1/f.width, y1/f.height, (x2-x1)/f.width, (y2-y1)/f.height],
                            "mask": a[y1:y2, x1:x2].astype('uint8').tolist(),
                            "cvrs_mask_window": [x1, y1, x2, y2]}
                meta["aux_polygon"] = obj.polygon
            labels.append({"label": label, "confidence": obj.score, "cvrs": meta, **geometry})
        rows.append({"sample_id": f.sample_id, "width": f.width, "height": f.height, "image": f.image,
                     "image_sha256": f.image_sha256, "task": f.task, "metadata": f.metadata, "labels": labels})
    return {"format": "cvrs-fiftyone-rich/1", "records": rows, "categories": {str(k): v for k, v in bundle.categories.items()},
            "dataset_digest": bundle.dataset_digest, "licenses": bundle.licenses, "provenance": bundle.provenance,
            "source_digest": digest(bundle), "losses": []}


def from_fiftyone_payload(payload: dict, *, max_mask_pixels: int = 64 * 1024 * 1024) -> RichInterchange:
    from cvsubstrate.vision.masks import encode_mask
    if payload.get("format") != "cvrs-fiftyone-rich/1":
        raise ValueError("unsupported FiftyOne interchange format")
    categories = {int(k): v for k, v in payload["categories"].items()}
    inverse = {v: k for k, v in categories.items()}
    frames = []
    for r in payload["records"]:
        objects = []
        for item in r["labels"]:
            meta = item["cvrs"]
            category = inverse.get(item["label"])
            if category is None and meta.get("category_id") is not None:
                raise CVRSError("UNMAPPED_LABEL", "native label is absent from the explicit taxonomy")
            polygon = mask = box = None
            if item["kind"] == "polyline":
                if len(item["points"]) != 1 or len(item["points"][0]) != 4 or not item.get("closed"):
                    raise ValueError("only closed quadrilaterals qualify as OBB; arbitrary contours require a different task")
                polygon = [[x*r["width"], y*r["height"]] for x, y in item["points"][0]]
                if meta.get("had_box"):
                    # Native OBB format has no second independent box slot.
                    box = meta.get("original_box")
            elif item["kind"] == "detection":
                x, y, w, h = item["bounding_box"]
                native_box = [x*r["width"], y*r["height"], (x+w)*r["width"], (y+h)*r["height"]]
                if item.get("mask") is not None:
                    import numpy as np
                    if r["width"]*r["height"] > max_mask_pixels:
                        raise CVRSError("MASK_BUDGET", "native mask expansion exceeds the pixel budget")
                    window = [round(v) for v in native_box]
                    if any(abs(a-b) > 1e-6 for a,b in zip(window,native_box)):
                        raise CVRSError("LOSSY_MASK_RESIZE", "fractional native mask windows require an explicitly selected resampling policy")
                    x1,y1,x2,y2 = window
                    a = np.asarray(item["mask"])
                    if a.shape != (y2-y1,x2-x1) or min(x1,y1)<0 or x2>r["width"] or y2>r["height"]:
                        raise ValueError("mask window and dense pixel dimensions disagree")
                    full = np.zeros((r["height"],r["width"]),dtype=bool)
                    if not np.isin(a,[0,1]).all():
                        raise ValueError("native mask is not binary")
                    full[y1:y2,x1:x2] = a.astype(bool)
                    mask = encode_mask(full)
                    # Preserve a separate, declared detector box while native
                    # mask bounding_box remains the exact mask raster window.
                    box = meta.get("original_box") if meta.get("had_box") else None
                    polygon = meta.get("aux_polygon")
                else:
                    box = native_box
            else:
                raise ValueError("unknown native label representation")
            objects.append(RichObject(id=meta["id"], category_id=category, score=item["confidence"], box=box,
                polygon=polygon, mask=mask, phrase=(item["label"] if category is None else meta.get("phrase")), prompt_digest=meta.get("prompt_digest"), attributes=meta.get("attributes",{})))
        frames.append(RichFrame(**{k:r[k] for k in ("sample_id","width","height","image","image_sha256","task","metadata")},objects=objects))
    return RichInterchange(dataset_digest=payload["dataset_digest"],categories=categories,frames=frames,
                           licenses=payload.get("licenses",{}),provenance=payload.get("provenance",{}))


def audit_roundtrip(original: dict | RichInterchange, restored: dict | RichInterchange, *, coordinate_tolerance=1e-9) -> dict:
    """Compare by stable object IDs, including pixels/phrases and metadata."""
    from cvsubstrate.vision.masks import mask_intersection, mask_area
    a,b = RichInterchange.model_validate(original), RichInterchange.model_validate(restored)
    issues=[]; checked=0
    if (a.dataset_digest,a.categories,a.licenses,a.provenance)!=(b.dataset_digest,b.categories,b.licenses,b.provenance):
        issues.append({"field":"dataset/taxonomy/license/provenance"})
    aa={x.sample_id:x for x in a.frames};bb={x.sample_id:x for x in b.frames}
    if aa.keys()!=bb.keys():issues.append({"field":"sample_ids"})
    for sid in aa.keys() & bb.keys():
        x,y=aa[sid],bb[sid]
        if (x.width,x.height,x.task,x.metadata,x.image,x.image_sha256)!=(y.width,y.height,y.task,y.metadata,y.image,y.image_sha256):issues.append({"sample":sid,"field":"frame"})
        xx={o.id:o for o in x.objects};yy={o.id:o for o in y.objects}
        if xx.keys()!=yy.keys():issues.append({"sample":sid,"field":"object_ids"})
        for oid in xx.keys() & yy.keys():
            u,v=xx[oid],yy[oid];checked+=1
            if (u.category_id,u.score,u.phrase,u.prompt_digest,u.attributes)!=(v.category_id,v.score,v.phrase,v.prompt_digest,v.attributes):issues.append({"sample":sid,"object":oid,"field":"labels/scores/metadata"})
            for field in ("box","polygon"):
                left,right=getattr(u,field),getattr(v,field)
                if (left is None)!=(right is None):issues.append({"sample":sid,"object":oid,"field":field});continue
                if left is not None:
                    la=[n for p in left for n in p] if field=="polygon" else left
                    lb=[n for p in right for n in p] if field=="polygon" else right
                    if len(la)!=len(lb) or any(abs(i-j)>coordinate_tolerance for i,j in zip(la,lb)):issues.append({"sample":sid,"object":oid,"field":field})
            if (u.mask is None)!=(v.mask is None):issues.append({"sample":sid,"object":oid,"field":"mask"})
            elif u.mask is not None and (mask_area(u.mask)!=mask_area(v.mask) or mask_intersection(u.mask,v.mask)!=mask_area(u.mask)):
                issues.append({"sample":sid,"object":oid,"field":"mask_pixels"})
    return {"status":"PRESERVED" if not issues else "CHANGED", "objects_checked":checked,
            "coordinate_tolerance":coordinate_tolerance,"source_digest":digest(a),"restored_digest":digest(b),"differences":issues}


def exchange(value: dict, target: str, direction: str) -> dict:
    if target not in {"supervision","fiftyone"} or direction not in {"export","import"}:
        raise ValueError("unknown exchange target/direction")
    fn={('supervision','export'):to_supervision_payload,('supervision','import'):from_supervision_payload,
        ('fiftyone','export'):to_fiftyone_payload,('fiftyone','import'):from_fiftyone_payload}[(target,direction)]
    result=fn(value)
    if isinstance(result, RichInterchange):
        return result.model_dump(mode='json')
    if isinstance(result, dict):
        return result
    raise TypeError("interchange conversion returned an unsupported value")
