"""Versioned public adapter contracts and explicit registry.

Importing a plugin is trusted code execution. Discovery lists metadata only and
never imports arbitrary installed entry points automatically.
"""
from __future__ import annotations
from typing import Protocol,runtime_checkable,Any
import importlib,importlib.util,re
from pathlib import Path
from cvsubstrate.contracts.groundwork import PluginDescriptor,CapabilityRequirement
from cvsubstrate.provenance.io import read_json,write_json,digest,atomic_bytes
from cvsubstrate.errors import CVRSError

@runtime_checkable
class ModelAdapter(Protocol):
    def capabilities(self)->dict: ...
    def validate(self,request:dict)->dict: ...
    def predict(self,request:dict)->dict: ...
    def train(self,request:dict)->dict: ...

@runtime_checkable
class DatasetAdapter(Protocol):
    def capabilities(self)->dict: ...
    def read(self,request:dict)->dict: ...

@runtime_checkable
class EvaluatorAdapter(Protocol):
    def capabilities(self)->dict: ...
    def evaluate(self,request:dict)->dict: ...

@runtime_checkable
class ExporterAdapter(Protocol):
    def capabilities(self)->dict: ...
    def export(self,request:dict)->dict: ...

@runtime_checkable
class SimulatorMetadataAdapter(Protocol):
    def capabilities(self)->dict: ...
    def convert(self,request:dict)->dict: ...

@runtime_checkable
class BackboneAdapter(Protocol):
    def capabilities(self)->dict: ...
    def extract(self,request:dict)->dict: ...

class PluginRegistry:
    def __init__(self,path:Path|None=None):
        self.path=Path(path) if path else None
        self.entries={}
        if self.path and self.path.exists():
            for value in read_json(self.path).get('plugins',[]):self.register(PluginDescriptor.model_validate(value),persist=False)
    def register(self,plugin:PluginDescriptor,*,persist=True):
        if plugin.id in self.entries:raise CVRSError('PLUGIN_DUPLICATE','plugin ID already registered')
        if not re.fullmatch(r'[A-Za-z_][\w.]*:[A-Za-z_]\w*',plugin.target):raise ValueError('target must be module:Class')
        self.entries[plugin.id]=plugin
        if persist and self.path:write_json(self.path,{'protocol_version':'1.0','plugins':[p.model_dump(mode='json') for p in self.entries.values()]})
    def list(self):return [p.model_dump(mode='json') for p in self.entries.values()]
    def inspect(self,name):
        if name not in self.entries:raise CVRSError('PLUGIN_UNKNOWN',name)
        p=self.entries[name]
        return {**p.model_dump(mode='json'),'descriptor_digest':digest(p),'metadata_only':True}
    def load(self,name):
        if name not in self.entries:raise CVRSError('PLUGIN_UNKNOWN',name)
        p=self.entries[name]
        if not p.trust_code:raise CVRSError('PLUGIN_TRUST','explicit trust_code needed to import executable plugin')
        module,attr=p.target.split(':',1)
        return getattr(importlib.import_module(module),attr)()

def negotiate(requirement:CapabilityRequirement,*,model:dict,dataset:dict,evaluator:dict|None=None):
    problems=[]
    for field,wanted in [('tasks',requirement.task),('operations',requirement.operation),('input_formats',requirement.input_format),('output_formats',requirement.output_format)]:
        if wanted not in model.get(field,[]):problems.append({'component':'model','field':field,'required':wanted,'available':model.get(field,[])})
    missing=set(requirement.dataset_fields)-set(dataset.get('fields',[]))
    if missing:problems.append({'component':'dataset','missing_fields':sorted(missing)})
    if requirement.task not in dataset.get('tasks',[]):problems.append({'component':'dataset','missing_task':requirement.task})
    if evaluator:
        if requirement.task not in evaluator.get('tasks',[]) or requirement.output_format not in evaluator.get('input_formats',[]):problems.append({'component':'evaluator','reason':'task/output format mismatch'})
    if requirement.precision and requirement.precision not in model.get('precisions',[]):problems.append({'component':'model','missing_precision':requirement.precision})
    return {'status':'SATISFIABLE' if not problems else 'UNSATISFIABLE','problems':problems,'note':'Declared compatibility only; no model was executed.'}

def validate_plugin(plugin:Any,descriptor:PluginDescriptor):
    checks=[]
    cap=plugin.capabilities()
    checks.append({'check':'capabilities_mapping','pass':isinstance(cap,dict)})
    checks.append({'check':'version','pass':cap.get('protocol_version')=='1.0'})
    for op in descriptor.operations:
        checks.append({'check':'callable_'+op,'pass':callable(getattr(plugin,op,None))})
    from cvsubstrate.provenance.io import canonical_bytes
    canonical_bytes(cap)
    return {'status':'PASS' if all(c['pass'] for c in checks) else 'FAIL','checks':checks,'scope':'Structural SDK conformance; numerical and real-model conformance require fixtures/native runs.'}

def scaffold(destination:Path,name:str,kind='dataset'):
    if kind not in {'dataset','model','evaluator','exporter','simulator_metadata','backbone','artifact_store','merge'}:raise ValueError('unsupported plugin kind')
    if not re.fullmatch('[a-z][a-z0-9_]*',name):raise ValueError('Python identifier required')
    out=Path(destination)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','plugin destination exists')
    out.mkdir(parents=True);(out/name).mkdir()
    code='# Example validation-only plugin; implement native operations explicitly.\nclass Plugin:\n    def capabilities(self):\n        return {"protocol_version":"1.0","tasks":[],"operations":["validate"],"example_only":True}\n    def validate(self,request):\n        import json\n        if not isinstance(request,dict): raise ValueError("request must be a mapping")\n        json.dumps(request,allow_nan=False)\n        return {"status":"VALID","request_keys":sorted(request)}\n'
    atomic_bytes(out/name/'__init__.py',code.encode())
    descriptor=PluginDescriptor(id=name,kind=kind,target=name+':Plugin',operations=['validate'])
    write_json(out/'plugin.json',descriptor)
    atomic_bytes(out/'pyproject.toml',f'[build-system]\nrequires=["setuptools>=77"]\nbuild-backend="setuptools.build_meta"\n[project]\nname="{name.replace("_","-")}"\nversion="0.0.1"\nrequires-python=">=3.11"\n'.encode())
    atomic_bytes(out/'README.md',b'# External plugin starter\nInstall this project into the adapter interpreter. Set trust_code explicitly before plugin import. This example validates JSON only, not a model. Extend only the operations you actually implement.\n')
    return {'status':'CREATED','path':str(out),'advertised_operations':['validate']}


@runtime_checkable
class ManagedAdapter(Protocol):
    def capabilities(self)->dict: ...
    def close(self)->None: ...

from cvsubstrate.artifacts.store import ArtifactStore
