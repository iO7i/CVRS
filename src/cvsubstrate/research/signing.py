"""Optional Ed25519 signatures; a key authenticates bytes, not scientific truth.

Keys are never automatically included in exports. Private key creation requires
an explicit destination; unencrypted keys require a separate acknowledgement.
Signature domain separation prevents reusing signatures across record types.
"""
from __future__ import annotations
import base64,hashlib,os
from pathlib import Path
from cvsubstrate.provenance.io import canonical_bytes,digest
from cvsubstrate.errors import DependencyUnavailable
DOMAIN=b'cvrs.registry.signature.v1\x00'

def _crypto():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
        from cryptography.hazmat.primitives import serialization
        return Ed25519PrivateKey,Ed25519PublicKey,serialization
    except ImportError as e:raise DependencyUnavailable('install the optional signing dependency') from e

def keygen(destination,*,password:bytes|None=None,allow_unencrypted=False):
    if not password and not allow_unencrypted:raise ValueError('pass a password or explicitly allow an unencrypted key')
    Private,_,ser=_crypto();key=Private.generate();p=Path(destination);p.parent.mkdir(parents=True,exist_ok=True)
    encoded=key.private_bytes(ser.Encoding.PEM,ser.PrivateFormat.PKCS8,ser.BestAvailableEncryption(password) if password else ser.NoEncryption())
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:f.write(encoded);f.flush();os.fsync(f.fileno())
    public=key.public_key().public_bytes(ser.Encoding.Raw,ser.PublicFormat.Raw)
    return {'algorithm':'Ed25519','public_key':public.hex(),'key_id':hashlib.sha256(public).hexdigest(),
            'private_key_written':str(p),'identity_verified':False}

def sign_payload(value,private_key_path,*,password=None):
    Private,_,ser=_crypto();key=ser.load_pem_private_key(Path(private_key_path).read_bytes(),password=password)
    if not isinstance(key,Private):raise ValueError('Ed25519 private key required')
    public=key.public_key().public_bytes(ser.Encoding.Raw,ser.PublicFormat.Raw);sha=digest(value)
    message=DOMAIN+bytes.fromhex(sha)
    return {'format':'cvrs-ed25519/1.0','algorithm':'Ed25519','payload_sha256':sha,'public_key':public.hex(),
        'key_id':hashlib.sha256(public).hexdigest(),'signature':base64.b64encode(key.sign(message)).decode('ascii')}

def verify_signature(value,envelope,*,trusted_keys=None):
    _,Public,_=_crypto()
    if envelope.get('format')!='cvrs-ed25519/1.0' or envelope.get('algorithm')!='Ed25519':raise ValueError('unsupported signature format')
    public=bytes.fromhex(envelope['public_key']);key_id=hashlib.sha256(public).hexdigest()
    if key_id!=envelope['key_id'] or digest(value)!=envelope['payload_sha256']:raise ValueError('signature subject/key identity mismatch')
    Public.from_public_bytes(public).verify(base64.b64decode(envelope['signature'],validate=True),DOMAIN+bytes.fromhex(envelope['payload_sha256']))
    return {'signature_valid':True,'key_id':key_id,'trusted_key':key_id in set(trusted_keys or []),
        'identity_verified':False,'scientific_claim_verified':False}
