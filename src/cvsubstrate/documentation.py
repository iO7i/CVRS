"""Generate contract/API reference from declared public modules and schema metadata."""
from pathlib import Path
import ast
from cvsubstrate.schemas.registry import schema_registry,export_schemas
from cvsubstrate.provenance.io import write_json
from cvsubstrate.errors import CVRSError
PUBLIC_MODULES=['cvsubstrate.contracts.models','cvsubstrate.contracts.research','cvsubstrate.contracts.groundwork','cvsubstrate.contracts.synthetic',
    'cvsubstrate.adapters.sdk','cvsubstrate.adapters.conformance','cvsubstrate.artifacts.store','cvsubstrate.artifacts.capsule',
    'cvsubstrate.schemas.registry','cvsubstrate.experiments.dag','cvsubstrate.campaigns.dsl','cvsubstrate.benchmarks.registry',
    'cvsubstrate.evaluation.converters','cvsubstrate.geometry.merge','cvsubstrate.datasets.importers','cvsubstrate.backbones.service','cvsubstrate.deployment.service']

PUBLIC_MODULES += ['cvsubstrate.contracts.frontier','cvsubstrate.telemetry','cvsubstrate.streaming.raster','cvsubstrate.streaming.service','cvsubstrate.vision.masks','cvsubstrate.vision.grounding','cvsubstrate.vision.evaluation','cvsubstrate.vision.service','cvsubstrate.adapters.recipes','cvsubstrate.deployment.profiles','cvsubstrate.deployment.calibration','cvsubstrate.deployment.quantization','cvsubstrate.research.registry','cvsubstrate.research.capture','cvsubstrate.research.reevaluate','cvsubstrate.research.capsule']

PUBLIC_MODULES += ['cvsubstrate.foundation.identity', 'cvsubstrate.foundation.lifecycle', 'cvsubstrate.foundation.policy', 'cvsubstrate.foundation.compatibility', 'cvsubstrate.artifacts.managed', 'cvsubstrate.artifacts.dependencies', 'cvsubstrate.execution.session', 'cvsubstrate.heritage.closure', 'cvsubstrate.heritage.native_data', 'cvsubstrate.heritage.checkpoint_v1', 'cvsubstrate.heritage.model_index', 'cvsubstrate.campaigns.native', 'cvsubstrate.datasets.sensors', 'cvsubstrate.data.asset_lineage', 'cvsubstrate.streaming.tasks', 'cvsubstrate.vision.prompts', 'cvsubstrate.vision.trajectories', 'cvsubstrate.vision.ontology', 'cvsubstrate.vision.assets', 'cvsubstrate.vision.diagnostics', 'cvsubstrate.research.claims', 'cvsubstrate.research.federated', 'cvsubstrate.research.capture_v2', 'cvsubstrate.research.evaluators', 'cvsubstrate.research.signing', 'cvsubstrate.research.task_access']

def generate_reference(output:Path):
    out=Path(output)
    if out.exists():raise CVRSError('OUTPUT_EXISTS','reference generation needs a new directory')
    out.mkdir(parents=True);export_schemas(out/'schemas');classes=schema_registry()
    lines=['# Contract reference','','Generated from Pydantic schemas. Optional dependencies are not imported.','']
    for name,cls in sorted(classes.items()):
        schema=cls.model_json_schema();lines+=['## '+name,'',schema.get('description',''),'', '| Field | Required | Type/schema |','|---|---|---|']
        for field,p in schema.get('properties',{}).items():lines.append('| '+field+' | '+str(field in schema.get('required',[]))+' | `'+str(p.get('type',p.get('$ref',p.get('anyOf','see schema')))).replace('|','\\|')+'` |')
        lines.append('')
    (out/'SCHEMAS.md').write_text('\n'.join(lines),'utf-8');api=['# Public API inventory','','Stable finite imports are exposed through cvsubstrate.v1; native driver internals remain provisional. Historical readers are explicit and versioned.',''];base=Path(__file__).parent
    for module in PUBLIC_MODULES:
        path=base/('/'.join(module.split('.')[1:])+'.py');tree=ast.parse(path.read_text());api+=['## `'+module+'`','']
        for node in tree.body:
            if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and not node.name.startswith('_'):api+=['### `'+node.name+'`','',ast.get_docstring(node) or 'See the typed implementation and operation contract.','']
    (out/'API.md').write_text('\n'.join(api),'utf-8');write_json(out/'public-modules.json',PUBLIC_MODULES)
    return {'schemas':len(classes),'public_modules':len(PUBLIC_MODULES),'output':str(out)}
