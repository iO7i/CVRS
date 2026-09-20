"""Opt-in research contracts. These do not alter the identity of v1 core manifests.

Geometry, simulator observations and campaign policies are separate, explicitly
versioned records. Merely possessing a record does not certify a backend.
"""
from __future__ import annotations

import math
from typing import Annotated, Any, Literal
from pydantic import Field, field_validator, model_validator
from cvsubstrate.contracts.models import (
    Contract, Finite, ID, SHA256, PositiveInt, NonnegativeInt, Category,
    ExperimentSpec, LicenseInfo, relative_path,
)


class Quantity(Contract):
    status: Literal['unknown', 'declared', 'measured', 'simulator_reported', 'annotated', 'human_rated']
    value: Any = None
    unit: str | None = None
    method: str | None = None
    evidence: str | None = None

    @model_validator(mode='after')
    def meaningful(self):
        if self.status == 'unknown' and self.value is not None:
            raise ValueError('unknown quantity must be null, not zero or an estimate')
        if self.status != 'unknown' and self.value is None:
            raise ValueError('known quantity requires a value')
        if self.status != 'unknown' and isinstance(self.value, (int, float, list)) and not self.unit:
            raise ValueError('numeric quantities require explicit units (including dimensionless)')
        if self.status in {'measured', 'human_rated', 'annotated'} and not self.method:
            raise ValueError('measurements/annotations/ratings require a method or definition')
        return self


class CameraRecord(Contract):
    image_width: PositiveInt | None = None
    image_height: PositiveInt | None = None
    intrinsics: list[list[Finite]] | None = None
    camera_to_world: list[list[Finite]] | None = None
    coordinate_convention: str | None = None
    distance_unit: str | None = None

    @model_validator(mode='after')
    def matrices(self):
        if (self.image_width is None) != (self.image_height is None):
            raise ValueError('camera width and height must be supplied together')
        if self.intrinsics is not None:
            k = self.intrinsics
            if len(k) != 3 or any(len(row) != 3 for row in k):
                raise ValueError('intrinsics must be 3x3')
            if k[0][0] <= 0 or k[1][1] <= 0 or k[2] != [0.0, 0.0, 1.0]:
                raise ValueError('expected positive focal lengths and normalized pinhole intrinsics')
        if self.camera_to_world is not None:
            t = self.camera_to_world
            if len(t) != 4 or any(len(row) != 4 for row in t) or t[3] != [0.0, 0.0, 0.0, 1.0]:
                raise ValueError('camera_to_world must be an affine homogeneous 4x4 matrix')
            if not self.coordinate_convention or not self.distance_unit:
                raise ValueError('extrinsics require coordinate and distance-unit conventions')
        return self


class SyntheticObject(Contract):
    object_id: ID
    asset_id: str | None = None
    category: str | None = None
    attributes: dict[str, Quantity] = Field(default_factory=dict)

    @model_validator(mode='after')
    def fractions(self):
        for key in ('occlusion_fraction', 'truncation_fraction'):
            q = self.attributes.get(key)
            if q is not None and q.status != 'unknown':
                if isinstance(q.value, bool) or not isinstance(q.value, (int, float)) or not 0 <= q.value <= 1:
                    raise ValueError(f'{key} must be a fraction in [0,1]')
                if q.unit != 'fraction' or not q.method:
                    raise ValueError(f'{key} requires unit=fraction and an explicit definition')
        return self


class SyntheticRecord(Contract):
    sample_id: ID
    generator: str
    generator_version: str | None = None
    simulator: str | None = None
    simulator_version: str | None = None
    engine: str | None = None
    engine_version: str | None = None
    generation_revision: str | None = None
    generation_environment_digest: SHA256 | None = None
    raw_sidecar_digest: SHA256 | None = None
    scene_id: str | None = None
    scene_source: str | None = None
    asset_ids: list[str] = Field(default_factory=list)
    seed: NonnegativeInt | None = None
    camera: CameraRecord = Field(default_factory=CameraRecord)
    planned: dict[str, Quantity] = Field(default_factory=dict)
    observed: dict[str, Quantity] = Field(default_factory=dict)
    objects: list[SyntheticObject] = Field(default_factory=list)
    annotation_method: str | None = None
    licenses: LicenseInfo = Field(default_factory=LicenseInfo)
    notes: str | None = None

    @model_validator(mode='after')
    def object_ids(self):
        ids = [o.object_id for o in self.objects]
        if len(ids) != len(set(ids)):
            raise ValueError('duplicate synthetic object IDs')
        return self


class FieldMapping(Contract):
    pointer: str
    target: str
    group: Literal['planned', 'observed'] = 'observed'
    status: Literal['declared', 'measured', 'simulator_reported', 'annotated', 'human_rated'] = 'simulator_reported'
    unit: str | None = None
    method: str | None = None
    scale: Finite = 1.0
    offset: Finite = 0.0
    required: bool = False

    @field_validator('pointer')
    @classmethod
    def json_pointer(cls, v):
        if v and not v.startswith('/'):
            raise ValueError('mapping uses RFC6901 JSON pointers, not Python expressions')
        return v


class SidecarMapping(Contract):
    name: ID
    sample_id_pointer: str = '/sample_id'
    generator: str
    generator_version: str | None = None
    simulator: str | None = None
    engine: str | None = None
    fields: list[FieldMapping] = Field(min_length=1)
    identity_pointers: dict[str, str] = Field(default_factory=dict)
    note: str = 'Declarative mapping of a user export; not a certified native simulator integration.'

    @model_validator(mode='after')
    def unique_targets(self):
        keys = [(f.group, f.target) for f in self.fields]
        if len(keys) != len(set(keys)):
            raise ValueError('two fields cannot overwrite the same canonical quantity')
        if self.sample_id_pointer and not self.sample_id_pointer.startswith('/'):
            raise ValueError('sample ID must use a JSON pointer')
        return self


class GeoReference(Contract):
    crs: str
    affine: list[Finite] = Field(min_length=6, max_length=6)
    pixel_reference: Literal['corner'] = 'corner'
    axis_order: Literal['x_y'] = 'x_y'
    gsd_m: list[Finite] | None = None

    @model_validator(mode='after')
    def invertible(self):
        a, b, c, d, e, f = self.affine
        if not self.crs.strip():
            raise ValueError('CRS must be explicitly supplied')
        if abs(a * e - b * d) <= 1e-15 * max(abs(a * e), abs(b * d), 1e-300):
            raise ValueError('affine transform is singular')
        if self.gsd_m is not None and (len(self.gsd_m) != 2 or min(self.gsd_m) <= 0):
            raise ValueError('GSD must contain two positive measured/declared metre values')
        return self


class TilingPolicy(Contract):
    width: PositiveInt = 1024
    height: PositiveInt = 1024
    overlap_x: NonnegativeInt = 128
    overlap_y: NonnegativeInt = 128
    resize_width: PositiveInt | None = None
    resize_height: PositiveInt | None = None
    resize_method: Literal['bilinear'] = 'bilinear'
    edge_policy: Literal['anchor_last_crop'] = 'anchor_last_crop'
    pad_to_tile: bool = True
    padding_rgb: list[Annotated[int, Field(strict=True, ge=0, le=255)]] = Field(default_factory=lambda: [0, 0, 0], min_length=3, max_length=3)
    padding_prediction_policy: Literal['clip_to_valid_region', 'reject'] = 'clip_to_valid_region'
    merge: Literal['class_aware_greedy_nms'] = 'class_aware_greedy_nms'
    merge_iou: Annotated[float, Field(strict=True, ge=0, le=1)] = 0.5
    max_source_pixels: PositiveInt = 100_000_000
    max_tiles: PositiveInt = 10000

    @model_validator(mode='after')
    def dimensions(self):
        if self.overlap_x >= self.width or self.overlap_y >= self.height:
            raise ValueError('overlap must be smaller than tile dimension')
        if (self.resize_width is None) != (self.resize_height is None):
            raise ValueError('resize dimensions must be supplied together')
        return self


class OrientedAnnotation(Contract):
    polygon: list[list[Finite]] = Field(min_length=4, max_length=4)
    category_id: NonnegativeInt
    difficult: bool = False
    source_line: PositiveInt | None = None

    @model_validator(mode='after')
    def geometry(self):
        from cvsubstrate.geometry.polygons import canonical_polygon
        canonical_polygon(self.polygon)
        return self


class OrientedSample(Contract):
    id: ID
    image: str
    sha256: SHA256
    width: PositiveInt
    height: PositiveInt
    annotations: list[OrientedAnnotation] = Field(default_factory=list)
    domain: str = 'unknown'
    source_kind: Literal['real', 'synthetic', 'unknown'] = 'unknown'
    lineage_group: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    _path = field_validator('image')(relative_path)


class OrientedDataset(Contract):
    name: ID
    version: str
    categories: list[Category] = Field(min_length=1)
    samples: list[OrientedSample] = Field(min_length=1)
    role: Literal['train', 'dev', 'locked_test']
    purpose: Literal['software_fixture', 'research_dataset'] = 'research_dataset'
    licenses: LicenseInfo = Field(default_factory=LicenseInfo)
    convention: Literal['continuous_pixel_xy_clockwise_convex_quadrilateral'] = 'continuous_pixel_xy_clockwise_convex_quadrilateral'
    note: str = 'Out-of-image vertices are preserved, not silently clipped; report them during validation.'

    @model_validator(mode='after')
    def identities(self):
        ids = [s.id for s in self.samples]
        cats = [c.id for c in self.categories]
        if len(ids) != len(set(ids)) or len(cats) != len(set(cats)):
            raise ValueError('duplicate sample/category identifiers')
        if len({c.name for c in self.categories}) != len(cats):
            raise ValueError('duplicate category names')
        for s in self.samples:
            if any(a.category_id not in cats for a in s.annotations):
                raise ValueError('unknown category ID')
        return self


class OrientedPrediction(Contract):
    sample_id: ID
    polygons: list[list[list[Finite]]]
    scores: list[Annotated[float, Field(strict=True, ge=0, le=1)]]
    category_ids: list[NonnegativeInt]
    convention: Literal['continuous_pixel_xy_clockwise_convex_quadrilateral'] = 'continuous_pixel_xy_clockwise_convex_quadrilateral'

    @model_validator(mode='after')
    def arrays(self):
        from cvsubstrate.geometry.polygons import canonical_polygon
        if not len(self.polygons) == len(self.scores) == len(self.category_ids):
            raise ValueError('oriented prediction arrays must have the same length')
        for p in self.polygons:
            if len(p) != 4:
                raise ValueError('oriented detection requires quadrilaterals')
            canonical_polygon(p)
        return self


class TinyEvaluationPolicy(Contract):
    iou: Annotated[float, Field(strict=True, gt=0, le=1)] = 0.5
    size_edges: list[Finite] = Field(default_factory=lambda: [0.0, 16.0, 32.0, 64.0])
    size_statistic: Literal['sqrt_bbox_area_pixels'] = 'sqrt_bbox_area_pixels'
    density_edges: list[NonnegativeInt] = Field(default_factory=lambda: [0,1,5,20])
    border_distances_px: list[Finite] = Field(default_factory=lambda: [0.0,8.0,16.0])
    fppi_budgets: list[Finite] = Field(default_factory=lambda: [0.0, 0.1, 1.0, 10.0])
    fixed_score_threshold: Annotated[float, Field(strict=True, ge=0, le=1)] = 0.5
    max_detections_per_image: PositiveInt = 1000

    @model_validator(mode='after')
    def edges(self):
        for name in ('size_edges', 'fppi_budgets', 'density_edges', 'border_distances_px'):
            v = getattr(self, name)
            if not v or v != sorted(set(v)) or v[0] < 0:
                raise ValueError(f'{name} must be sorted unique nonnegative values')
        if self.density_edges[0] != 0:
            raise ValueError('density bins must begin at zero')
        if self.size_edges[0] != 0:
            raise ValueError('size bins must begin at zero and end with an unbounded bin')
        return self


class BackendTemplate(Contract):
    name: ID
    experiment: ExperimentSpec
    worker_python: str | None = None


Arm = Literal['R', 'S', 'R+S', 'S->R', 'R-replay', 'R->R']


class CampaignSpec(Contract):
    name: ID
    backends: list[BackendTemplate] = Field(min_length=1)
    arms: list[Arm] = Field(default_factory=lambda: ['R', 'S', 'R+S', 'S->R', 'R-replay', 'R->R'])
    seeds: list[NonnegativeInt] = Field(min_length=1)
    phase: Literal['exploratory', 'confirmatory'] = 'exploratory'
    selection_record_digest: SHA256 | None = None
    previous_seeds: list[NonnegativeInt] = Field(default_factory=list)
    updates: PositiveInt = 2
    pretrain_updates: PositiveInt = 2
    real_per_update: PositiveInt = 1
    synthetic_per_update: PositiveInt = 1
    timeout_seconds: Annotated[float, Field(strict=True, gt=0)] = 180.0
    primary_metric: str = '/aggregate/counts_by_iou/0/recall/value'
    control_claim: Literal['source_exposure_and_nominal_loss_matched_not_compute_equal'] = 'source_exposure_and_nominal_loss_matched_not_compute_equal'
    rationale: Annotated[str, Field(min_length=1)]

    @model_validator(mode='after')
    def scientific_constraints(self):
        if len(set(self.arms)) != len(self.arms) or len(set(self.seeds)) != len(self.seeds):
            raise ValueError('duplicate arms/seeds')
        if not self.arms:
            raise ValueError('campaign needs at least one arm')
        if len({b.name for b in self.backends}) != len(self.backends):
            raise ValueError('duplicate backend names')
        if self.phase == 'confirmatory':
            if len(self.seeds) < 3 or not self.selection_record_digest:
                raise ValueError('confirmatory campaigns require >=3 fresh seeds and a selection-record digest')
            if set(self.seeds) & set(self.previous_seeds):
                raise ValueError('confirmatory seeds were already used during selection')
        if self.real_per_update != self.synthetic_per_update and 'R->R' in self.arms:
            raise ValueError('R->R pretraining control requires equal real/synthetic samples per update')
        return self


class AccessApproval(Contract):
    dataset_digest: SHA256
    experiment_digest: SHA256
    split: str
    purpose: Literal['final_evaluation_no_training'] = 'final_evaluation_no_training'
    approved_by: Annotated[str, Field(min_length=1)]
    reason: Annotated[str, Field(min_length=1)]
    max_uses: PositiveInt = 1
    note: str = 'Local accountability policy; not cryptographic authorization or a filesystem sandbox.'


RESEARCH_SCHEMAS = [Quantity, CameraRecord, SyntheticObject, SyntheticRecord,
    FieldMapping, SidecarMapping, GeoReference, TilingPolicy, OrientedAnnotation,
    OrientedSample, OrientedDataset, OrientedPrediction, TinyEvaluationPolicy,
    BackendTemplate, CampaignSpec, AccessApproval]
