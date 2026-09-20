"""Explicit, hash-bound external worker interface. No plugin auto-discovery/imports.

The worker is trusted executable code, launched in a chosen interpreter. This is
process/dependency isolation, NOT a sandbox. No package-install hooks are run.
"""
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
from typing import Literal
from cvsubstrate.contracts.models import Contract,ID,SHA256,WorkerRequest,WorkerResponse
from cvsubstrate.execution.process import run_command,invoke
from cvsubstrate.errors import CVRSError
from cvsubstrate.provenance.io import file_digest,read_json,write_json


class WorkerPlugin(Contract):
    id: ID
    script: str
    script_sha256: SHA256
    interpreter: str | None = None
    protocol_version: Literal['1.0'] = '1.0'
    trust_executable_code: bool = False
    implementation_revision: str | None = None
    environment_capsule_digest: SHA256 | None = None


def invoke_external(plugin:WorkerPlugin,request:WorkerRequest,worker_python=None,timeout=180.0,log=None):
    if not plugin.trust_executable_code:raise CVRSError('PLUGIN_TRUST','external worker requires explicit executable-code approval')
    script=Path(plugin.script)
    if not script.is_absolute():raise CVRSError('PLUGIN_PATH','external worker script must be an explicit absolute path')
    if not script.is_file() or script.is_symlink() or file_digest(script)!=plugin.script_sha256:
        raise CVRSError('PLUGIN_HASH','external worker missing, symlinked or changed')
    with tempfile.TemporaryDirectory(prefix='cvrs-plugin-') as td:
        req=Path(td)/'request.json';res=Path(td)/'response.json'
        write_json(req,request)
        command=[worker_python or plugin.interpreter or sys.executable,str(script),'--request',str(req),'--response',str(res)]
        run_command(command,timeout,log=log)
        if not res.is_file():raise CVRSError('PLUGIN_RESPONSE','external worker omitted its response')
        response=WorkerResponse.model_validate(read_json(res))
    if file_digest(script)!=plugin.script_sha256:raise CVRSError('PLUGIN_CHANGED','worker script changed during execution')
    if response.status!='SUCCEEDED':
        error=response.error or {'code':'PLUGIN_FAILED','message':'worker reported failure'}
        raise CVRSError(error['code'],error['message'])
    return response


def invoke_configured(adapter,request,worker_python=None,timeout=180.0,log=None):
    if adapter.name!='external':return invoke(adapter.name,request,worker_python,timeout,log)
    if set(adapter.config)!={'worker','backend_config'}:
        raise CVRSError('PLUGIN_CONFIG','external adapter requires only worker and backend_config namespaces')
    plugin=WorkerPlugin.model_validate(adapter.config['worker'])
    return invoke_external(plugin,request,worker_python,timeout,log)
