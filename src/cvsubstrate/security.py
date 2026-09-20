"""Portable metadata redaction. Not a sandbox or an authenticity mechanism."""
from __future__ import annotations
from pathlib import Path
import re
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
SECRET_KEY = re.compile(r'(?i)(password|passwd|secret|token|authorization|api[_-]?key|credential|private[_-]?key)')
BEARER = re.compile(r'(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+')
ASSIGNMENT = re.compile(r'(?i)\b((?:api[_-]?key|password|passwd|token|secret|authorization)\s*[=:]\s*)[^\s,;]+')
URL = re.compile(r'https?://[^\s\"<>]+')

def redact_url(value: str) -> str:
    p=urlsplit(value)
    host=p.hostname or ''
    if ':' in host and not host.startswith('['): host='['+host+']'
    if p.port: host+=':'+str(p.port)
    query=[(k,'[REDACTED]' if SECRET_KEY.search(k) or k.lower().startswith('x-amz-') else v) for k,v in parse_qsl(p.query,keep_blank_values=True)]
    return urlunsplit((p.scheme,host,p.path,urlencode(query),''))

def sanitize(value, *, portable_paths: bool = True):
    if isinstance(value,dict):
        return {k:('[REDACTED]' if SECRET_KEY.search(str(k)) else sanitize(v,portable_paths=portable_paths)) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [sanitize(v,portable_paths=portable_paths) for v in value]
    if not isinstance(value,str): return value
    text=URL.sub(lambda m:redact_url(m.group()),value)
    text=BEARER.sub(r'\1 [REDACTED]',text)
    text=ASSIGNMENT.sub(r'\1[REDACTED]',text)
    if portable_paths:
        home=str(Path.home())
        if home not in ('/','.'):
            text=text.replace(home,'<HOME>')
        text=re.sub(r'(?i)C:\\Users\\[^\\\s]+',r'<HOME>',text)
        text=re.sub(r'/home/[^/\s]+','<HOME>',text)
    return text
