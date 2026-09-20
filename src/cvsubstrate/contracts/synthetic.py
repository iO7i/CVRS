"""Expanded generator-neutral observations; unknown, zero and planned are distinct."""
from typing import Any,Literal
from pydantic import Field,model_validator
from cvsubstrate.contracts.models import Contract,ID,SHA256,NonnegativeInt
from cvsubstrate.contracts.research import SyntheticRecord

class Observation(Contract):
    status:Literal['unknown','declared','measured','simulator_reported','annotated','derived','human_rated']='unknown'
    value:Any=None
    unit:str|None=None
    method:str|None=None
    input_digests:list[SHA256]=Field(default_factory=list)
    uncertainty:float|None=Field(default=None,ge=0)
    @model_validator(mode='after')
    def semantics(self):
        if self.status=='unknown' and self.value is not None:raise ValueError('unknown does not carry a guessed value')
        if self.status!='unknown' and self.value is None:raise ValueError('known observation requires a value')
        if self.status in {'measured','annotated','derived','human_rated'} and not self.method:raise ValueError('observation requires its method')
        if isinstance(self.value,(int,float)) and not isinstance(self.value,bool) and not self.unit:raise ValueError('numeric observations require units')
        if self.status=='derived' and not self.input_digests:raise ValueError('derived observations require input identities')
        if self.unit=='fraction' and self.value is not None and not 0<=self.value<=1:raise ValueError('fraction outside [0,1]')
        return self

class SyntheticSampleManifest(Contract):
    record:SyntheticRecord
    scene:dict[str,Observation]=Field(default_factory=dict)
    assets:list[dict[str,Any]]=Field(default_factory=list)
    lens:dict[str,Observation]=Field(default_factory=dict)
    sensor:dict[str,Observation]=Field(default_factory=dict)
    rendering:dict[str,Observation]=Field(default_factory=dict)
    weather:dict[str,Observation]=Field(default_factory=dict)
    illumination:dict[str,Observation]=Field(default_factory=dict)
    compression:dict[str,Observation]=Field(default_factory=dict)
    randomization:dict[str,Observation]=Field(default_factory=dict)
    annotations:dict[str,Observation]=Field(default_factory=dict)
    object_observations:dict[str,dict[str,Observation]]=Field(default_factory=dict)
    planned:dict[str,Observation]=Field(default_factory=dict)
    measurement_definitions:dict[str,str]=Field(default_factory=dict)

SYNTHETIC_SCHEMAS=[Observation,SyntheticSampleManifest]
