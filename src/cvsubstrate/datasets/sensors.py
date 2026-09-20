"""Explicit band/radiometry/sensor and temporal-lineage contracts."""
from __future__ import annotations
from typing import Literal
from pydantic import Field,model_validator
from cvsubstrate.contracts.models import Contract,ID,SHA256,Finite
from cvsubstrate.provenance.io import digest
class BandSpec(Contract):
    name: ID
    index: int=Field(ge=1)
    meaning: Literal['R','G','B','NIR','SWIR','SAR-VV','SAR-VH','custom']='custom'
    units: str
    wavelength_nm: Finite|None=None
    scale: Finite=1.0
    offset: Finite=0.0
    nodata: Finite|None=None
    normalization: Literal['none','range','mean_std']='none'
    minimum: Finite|None=None
    maximum: Finite|None=None
    mean: Finite|None=None
    std: Finite|None=None
    @model_validator(mode='after')
    def valid(self):
        if self.normalization=='range' and (self.minimum is None or self.maximum is None or self.minimum>=self.maximum):raise ValueError('range normalization requires ordered bounds')
        if self.normalization=='mean_std' and (self.mean is None or self.std is None or self.std<=0):raise ValueError('normalization needs positive std')
        if self.wavelength_nm is not None and self.wavelength_nm<=0:raise ValueError('wavelength must be positive')
        return self
class SensorSpec(Contract):
    id: ID
    kind: Literal['optical','multispectral','hyperspectral','SAR','custom']
    bands: list[BandSpec]=Field(min_length=1)
    model_channel_names: list[ID]
    output_dtype: Literal['float32']='float32'
    @model_validator(mode='after')
    def valid(self):
        names=[x.name for x in self.bands]
        if len(set(names))!=len(names) or len({x.index for x in self.bands})!=len(names):raise ValueError('duplicate band name/index')
        if self.model_channel_names!=names:raise ValueError('model input channel order differs from declared bands')
        return self
class GeoSceneSpec(Contract):
    id: ID
    raster_sha256: SHA256
    width: int=Field(gt=0)
    height: int=Field(gt=0)
    crs: str|None=None
    coordinate_kind: Literal['pixel','projected','geographic']='pixel'
    affine: list[Finite]=Field(min_length=6,max_length=6)
    sensor: SensorSpec
    capture_timestamp: str|None=None
    temporal_stack_id: ID|None=None
    temporal_index: int|None=Field(default=None,ge=0)
    parent_scene_ids: list[ID]=Field(default_factory=list)
    @model_validator(mode='after')
    def valid(self):
        a,b,c,d,e,f=self.affine
        if abs(a*e-b*d)<1e-15:raise ValueError('singular raster affine')
        if self.coordinate_kind!='pixel' and not self.crs:raise ValueError('world coordinates require CRS')
        if (self.temporal_stack_id is None)!=(self.temporal_index is None):raise ValueError('temporal stack and index must be paired')
        if self.capture_timestamp:
            from datetime import datetime
            t=datetime.fromisoformat(self.capture_timestamp.replace('Z','+00:00'))
            if t.tzinfo is None:raise ValueError('timestamp needs timezone')
        return self

def normalize_bands(values,valid,spec:SensorSpec):
    import numpy as np
    a=np.asarray(values,dtype=np.float32).copy();v=np.asarray(valid,dtype=bool).copy()
    if a.ndim!=3 or a.shape[0]!=len(spec.bands):raise ValueError('expected C,H,W in declared band order')
    if v.shape!=a.shape[1:]:raise ValueError('validity-mask dimensions mismatch')
    for i,b in enumerate(spec.bands):
        channel=a[i]
        if b.nodata is not None:v &= channel!=b.nodata
        v &= np.isfinite(channel)
        channel*=b.scale;channel+=b.offset
        if b.normalization=='range':channel-=b.minimum;channel/=b.maximum-b.minimum
        elif b.normalization=='mean_std':channel-=b.mean;channel/=b.std
        if not np.isfinite(channel[v]).all():raise ValueError('radiometry overflow/nonfinite normalized valid sample')
    a[:,~v]=0
    return a,v
SCHEMAS=[BandSpec,SensorSpec,GeoSceneSpec]
