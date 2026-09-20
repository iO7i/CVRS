"""Measured snapshots and loss-audited lock importers. No installation side effects."""
from __future__ import annotations
import importlib.metadata,platform,re,tomllib
from pathlib import Path
from cvsubstrate.contracts.groundwork import EnvironmentManifest
from cvsubstrate.provenance.io import file_digest
from cvsubstrate.security import sanitize
from cvsubstrate.errors import CVRSError

def capture(*,probe_hardware=False)->EnvironmentManifest:
    packages=sorted([{'name':d.metadata.get('Name','unknown'),'version':d.version,'source':'installed_metadata'} for d in importlib.metadata.distributions()],key=lambda x:x['name'].lower())
    hardware={'machine':platform.machine(),'processor':platform.processor(),'gpu':'not_probed'}
    if probe_hardware:
        import shutil,subprocess,csv,io
        tool=shutil.which('nvidia-smi')
        if tool:
            try:
                result=subprocess.run([tool,'--query-gpu=name,uuid,driver_version,memory.total','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10,check=True)
                hardware['nvidia_smi']=[dict(zip(['name','uuid','driver_version','memory_mib'],(x.strip() for x in row))) for row in csv.reader(io.StringIO(result.stdout))]
                hardware['gpu']='metadata_probed'
            except (OSError,subprocess.SubprocessError) as exc:hardware['gpu']={'status':'PROBE_FAILED','reason':type(exc).__name__}
        else:hardware['gpu']='nvidia-smi unavailable; no inference about other accelerators'
    return EnvironmentManifest(python=platform.python_version(),platform=platform.platform(),packages=packages,metadata_status='MEASURED',hardware=hardware,unresolved=['GPU metadata is not runtime execution certification; CUDA library identity comes from an actual worker environment'])

def import_environment(path:Path,kind:str)->EnvironmentManifest:
    path=Path(path);text=path.read_text('utf-8');packages=[];unresolved=[];python=None;container=None
    if kind=='pip':
        for line in text.splitlines():
            s=line.strip()
            if not s or s.startswith('#'):continue
            m=re.fullmatch(r'([A-Za-z0-9_.-]+)==([^\s;]+)',s)
            if m:packages.append({'name':m[1],'version':m[2],'source':'pip_exact'})
            else:unresolved.append(sanitize(s))
    elif kind=='uv':
        data=tomllib.loads(text);python=data.get('requires-python')
        for p in data.get('package',[]):
            packages.append(sanitize({'name':p['name'],'version':p.get('version'),'source':p.get('source'),
                'dependencies':p.get('dependencies',[]),'wheels':p.get('wheels',[]),'sdist':p.get('sdist'),'resolution_markers':p.get('resolution-markers',[])}))
        unresolved.append('uv resolution markers retained; no environment selected or installed')
    elif kind=='conda-explicit':
        for line in text.splitlines():
            s=line.strip()
            if not s or s.startswith('#') or s=='@EXPLICIT':continue
            packages.append({'artifact_url':sanitize(s),'source':'conda_explicit'})
        unresolved.append('URLs retained as provenance; package contents not downloaded')
    elif kind=='conda':
        try:import yaml
        except ImportError as exc:raise CVRSError('DEPENDENCY_UNAVAILABLE','conda YAML import requires PyYAML in the tooling environment') from exc
        d=yaml.safe_load(text)
        for dep in d.get('dependencies',[]):
            if isinstance(dep,str):
                pieces=dep.split('=');packages.append({'name':pieces[0],'version':pieces[1] if len(pieces)>1 else None,'build':pieces[2] if len(pieces)>2 else None,'source':'conda'})
                if pieces[0]=='python' and len(pieces)>1:python=pieces[1]
            elif isinstance(dep,dict) and 'pip' in dep:
                packages.extend({'requirement':sanitize(s),'source':'conda_pip'} for s in dep['pip'])
            else:unresolved.append('unrecognized conda dependency '+str(sanitize(dep)))
    elif kind=='docker':
        if not re.fullmatch(r'[^\s]+@sha256:[a-f0-9]{64}',text.strip()):raise ValueError('Docker importer needs image@sha256:digest')
        container=sanitize(text.strip())
    else:raise CVRSError('UNSUPPORTED_FORMAT','environment kind must be pip, uv, conda, conda-explicit or docker')
    return EnvironmentManifest(python=python,packages=packages,container_digest=container,
        imports=[{'kind':kind,'filename':path.name,'sha256':file_digest(path)}],metadata_status='DECLARED',unresolved=unresolved)
