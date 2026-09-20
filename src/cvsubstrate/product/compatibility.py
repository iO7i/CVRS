"""Evidence-bound badges and conservative public-surface snapshots.

Structural comparison is not behavioral certification. Receipts record what a
verified, unsigned bundle says; they cannot authenticate an operator or prove
that an arbitrary submitted program genuinely performed the claimed work.
"""
from __future__ import annotations
import ast
import html
from pathlib import Path
from cvsubstrate.product.contracts import CompatibilityReceipt
from cvsubstrate.provenance.io import read_json, write_json, digest, file_digest
from cvsubstrate.errors import CVRSError


def make_receipt(descriptor: dict, evidence: Path | None = None) -> dict:
    allowed = {'subject_id', 'protocol', 'task', 'operation', 'implementation', 'limitations'}
    if set(descriptor) - allowed:
        raise ValueError('descriptor cannot self-assign execution, verification or reproduction levels')
    receipt = CompatibilityReceipt.model_validate(descriptor)
    receipt.limitations.append('Implementation, execution, reference metrics and reproduction are separate. Evidence is unsigned unless independently signed.')
    if evidence is not None:
        from cvsubstrate.provenance.artifact_set import verify_directory
        from cvsubstrate.provenance.bundle import verify_bundle
        evidence = Path(evidence).resolve()
        verified = verify_directory(evidence) if (evidence/'integrity.json').is_file() else verify_bundle(evidence)
        if verified.get('status') != 'VERIFIED':
            raise CVRSError('INVALID_EVIDENCE', 'compatibility evidence does not pass its integrity manifest')
        native_path = evidence/'stack-receipt.json'
        product_path = evidence/'compatibility-execution.json'
        if native_path.is_file():
            observed = read_json(native_path)
            subject, operation = observed.get('family'), observed.get('operation')
            task = observed.get('task')
            # Native results may expose task identity even if the older outer receipt did not.
            if task is None and isinstance(observed.get('result'), dict):
                task = observed['result'].get('task')
            status = observed.get('status', 'SUCCEEDED')
            selected = native_path
        elif product_path.is_file():
            observed = read_json(product_path)
            subject, operation, task = (observed.get(x) for x in ('subject_id','operation','task'))
            status = observed.get('status')
            selected = product_path
            if not observed.get('worker_sha256') or not observed.get('result_artifacts'):
                raise ValueError('execution record needs worker identity and actual output artifact references')
            from cvsubstrate.provenance.io import safe_join
            for item in observed['result_artifacts']:
                p = safe_join(evidence, item['path'])
                if not p.is_file() or file_digest(p) != item['sha256']:
                    raise ValueError('execution result artifact missing or changed')
        else:
            raise ValueError('no recognized task-bound execution receipt; a passing integrity file alone is insufficient')
        if subject != receipt.subject_id or operation != receipt.operation or task != receipt.task:
            raise CVRSError('EVIDENCE_SCOPE_MISMATCH', 'bind the exact subject, operation and task; unknown task is not proof')
        if status not in {'SUCCEEDED', 'FAILED', 'BLOCKED'}:
            raise ValueError('unrecognized observed execution status')
        if receipt.implementation == 'UNSUPPORTED' and status == 'SUCCEEDED':
            raise ValueError('unsupported operation cannot receive a success badge')
        receipt.execution = status
        receipt.evidence.append({'receipt_sha256': file_digest(selected), 'manifest_sha256': file_digest(evidence/('integrity.json' if (evidence/'integrity.json').exists() else 'artifacts.json')),
                                 'receipt_name': selected.name, 'task': task, 'operation': operation,
                                 'meaning': 'Recorded execution with matching scope, not authenticated native compatibility'})
    payload = receipt.model_dump(mode='json')
    return {**payload, 'receipt_digest': digest(payload)}


def render_badge(value: dict, destination: Path) -> dict:
    payload = dict(value); expected = payload.pop('receipt_digest', None)
    if expected != digest(payload):
        raise ValueError('compatibility receipt digest mismatch')
    receipt = CompatibilityReceipt.model_validate(payload)
    label = 'CVRS ' + receipt.protocol
    detail = 'adapter available' if receipt.execution == 'NOT_RUN' else 'execution recorded: ' + receipt.execution.lower()
    if receipt.implementation == 'UNSUPPORTED': detail = 'unsupported'
    color = '#31566b' if receipt.execution == 'SUCCEEDED' else '#6b5b32' if receipt.execution == 'NOT_RUN' else '#71424a'
    width = 145 + 7 * len(detail)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="28" role="img" aria-label="{html.escape(label+': '+detail,quote=True)}"><title>{html.escape(label+': '+detail)}</title><rect width="{width}" height="28" rx="5" fill="{color}"/><rect width="125" height="28" rx="5" fill="#253340"/><g font-family="Verdana,sans-serif" font-size="11" fill="white"><text x="10" y="18">{html.escape(label)}</text><text x="135" y="18">{html.escape(detail)}</text></g></svg>'''
    destination = Path(destination)
    if destination.exists(): raise ValueError('badge destination exists')
    destination.parent.mkdir(parents=True,exist_ok=True); destination.write_text(svg,encoding='utf-8')
    return {'status': 'RENDERED', 'output': str(destination), 'receipt_digest': expected,
            'limits': 'This badge does not assert scientific reproduction or independent certification.'}


def _symbol(source: Path, module: str, name: str, seen=None):
    seen = set() if seen is None else seen
    key = (module,name)
    if key in seen: return {'kind':'unresolved','reason':'reexport cycle'}
    seen.add(key)
    path = source/Path(*module.split('.')).with_suffix('.py')
    if not path.is_file(): path = source/Path(*module.split('.'))/'__init__.py'
    if not path.is_file(): return {'kind':'external','module':module,'name':name}
    tree = ast.parse(path.read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==name:
            return {'kind':'function', 'signature':ast.unparse(node.args), 'returns':ast.unparse(node.returns) if node.returns else None,
                    'async':isinstance(node,ast.AsyncFunctionDef)}
        if isinstance(node,ast.ClassDef) and node.name==name:
            methods={n.name:{'arguments':ast.unparse(n.args),'returns':ast.unparse(n.returns) if n.returns else None}
                     for n in node.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and (not n.name.startswith('_') or n.name=='__init__')}
            fields={n.target.id:{'annotation':ast.unparse(n.annotation),'default':ast.unparse(n.value) if n.value else None}
                    for n in node.body if isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name)}
            return {'kind':'class','bases':[ast.unparse(x) for x in node.bases], 'fields':fields,'methods':methods}
        if isinstance(node,ast.Assign) and any(isinstance(n,ast.Name) and n.id==name for n in node.targets):
            try:value=ast.literal_eval(node.value)
            except (ValueError,TypeError):value=ast.unparse(node.value)
            return {'kind':'constant','value':value}
        if isinstance(node,ast.ImportFrom) and not node.level and node.module is not None:
            imported_module = node.module
            for alias in node.names:
                if (alias.asname or alias.name)==name:return _symbol(source,imported_module,alias.name,seen)
    return {'kind':'unresolved','module':module,'name':name}



def _declared_facade_exports(tree: ast.Module) -> list[str] | None:
    """Read a literal export boundary without importing the inspected package.

    ``None`` retains the historical public-import rule: it is allowed only when
    no export list exists or for the exact comprehension shipped through 0.7.
    Other dynamic declarations must not silently widen or truncate a snapshot.
    """
    declarations: list[ast.Assign | ast.AnnAssign] = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == '__all__'
            for target in node.targets
        ):
            declarations.append(node)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == '__all__':
            declarations.append(node)

    # Do not misread append/+=/conditional/subscript changes as a complete list.
    for node in tree.body:
        if node in declarations:
            continue
        for part in ast.walk(node):
            if isinstance(part, ast.Name) and part.id == '__all__':
                raise ValueError('facade __all__ must be one self-contained literal declaration')
    if not declarations:
        return None
    if len(declarations) != 1:
        raise ValueError('facade __all__ must be declared exactly once')
    value = declarations[0].value
    legacy = ast.parse("[name for name in globals() if not name.startswith('_')]", mode='eval').body
    if value is None:
        raise ValueError('facade __all__ declaration has no value')
    if ast.dump(value) == ast.dump(legacy):
        return None
    try:
        names = ast.literal_eval(value)
    except (ValueError, TypeError, SyntaxError) as exc:
        raise ValueError('facade __all__ is dynamic; a literal list/tuple of names is required') from exc
    if not isinstance(names, (list, tuple)) or any(
        not isinstance(name, str) or not name.isidentifier() for name in names
    ):
        raise ValueError('facade __all__ must be a literal list/tuple of identifier strings')
    if len(set(names)) != len(names):
        raise ValueError('facade __all__ contains duplicate names')
    return list(names)


def freeze_api(root: Path, destination: Path) -> dict:
    root=Path(root).resolve();source=root/'src'
    facade=source/'cvsubstrate'/'v1.py'
    tree=ast.parse(facade.read_text(encoding='utf-8'))
    exports = _declared_facade_exports(tree)
    imports = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                imports[alias.asname or alias.name] = (node.module, alias.name)
    if exports is None:
        exports = [name for name in imports if not name.startswith('_')]
    missing = sorted(set(exports) - imports.keys())
    if missing:
        raise ValueError('facade exports lack an explicit import binding: ' + ', '.join(missing))
    symbols = {}
    for name in exports:
        module, original = imports[name]
        symbols[name] = {'origin': module + ':' + original, **_symbol(source, module, original)}
    # Snapshot only the finite advertised facade. New product APIs remain provisional.
    components=_symbol(source,'cvsubstrate.foundation.identity','COMPONENT_VERSIONS').get('value',{})
    schemas={}
    here=Path(__file__).resolve().parents[1]
    if (source/'cvsubstrate').resolve()==here:
        from cvsubstrate.schemas.registry import schema_registry
        for name,cls in schema_registry().items():schemas[name]=cls.model_json_schema()
    else:
        for path in sorted((root/'schemas').glob('*.json')):
            name = path.name.removesuffix('.schema.json') if path.name.endswith('.schema.json') else path.stem
            if name in schemas:
                raise ValueError('duplicate canonical schema identity in bundle: ' + name)
            schemas[name] = read_json(path)
        if not schemas:raise ValueError('snapshot of another source tree requires its generated schema bundle')
    result={'schema_version':'1.0','public_namespace':'cvsubstrate.v1','components':components,
            'symbols':symbols,'schemas':schemas,'policy':{'facade':'versioned finite API','native_drivers':'PROVISIONAL','product':'PROVISIONAL',
            'guarantee':'Structural compatibility contract; native SDK behavior needs integration evidence.'}}
    result['surface_digest']=digest(result)
    if Path(destination).exists():raise ValueError('use a new immutable API snapshot path')
    write_json(destination,result)
    return {'status':'SNAPSHOTTED','symbols':len(symbols),'schemas':len(schemas),'surface_digest':result['surface_digest'],'output':str(destination)}


def compare_api(previous: dict, current: dict) -> dict:
    for v in (previous,current):
        value=dict(v);stored=value.pop('surface_digest',None)
        if digest(value)!=stored:raise ValueError('API snapshot integrity mismatch')
    breaking=[];review=[];additions=[]
    for section in ('symbols','schemas','components'):
        before,after=previous.get(section,{}),current.get(section,{})
        for key in sorted(set(before)-set(after)):breaking.append({'section':section,'name':key,'change':'REMOVED'})
        for key in sorted(set(after)-set(before)):additions.append({'section':section,'name':key,'change':'ADDED'})
        for key in sorted(set(before)&set(after)):
            if before[key]!=after[key]:review.append({'section':section,'name':key,'change':'CHANGED_REVIEW_REQUIRED','before_digest':digest(before[key]),'after_digest':digest(after[key])})
    return {'status':'BREAKING' if breaking else 'REVIEW_REQUIRED' if review else 'STRUCTURALLY_COMPATIBLE',
            'breaking':breaking,'review':review,'additions':additions,'behavioral_compatibility':'NOT_INFERRED',
            'previous':previous['surface_digest'],'current':current['surface_digest']}
