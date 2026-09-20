"""Portable claim + attempt + evidence snapshots built on the existing safe capsule."""
from pathlib import Path
import tempfile
from cvsubstrate.research.registry import ResearchRegistry,import_snapshot
from cvsubstrate.artifacts.capsule import create_capsule, archive_capsule, materialize_capsule

def export_registry_capsule(registry,out,archive=None):
    out=Path(out)
    with tempfile.TemporaryDirectory() as td:
        snapshot=Path(td)/'snapshot'
        with ResearchRegistry(Path(registry)) as reg:reg.export(snapshot)
        result=create_capsule(snapshot,out,external_references=[{'kind':'datasets_and_models','state':'NOT_AUTOMATICALLY_BUNDLED','reason':'Only explicitly imported evidence bytes are transported; asset licenses remain separate.'}])
    if archive:result['archive']=archive_capsule(out,Path(archive))
    return result

def import_registry_capsule(archive,out):
    with tempfile.TemporaryDirectory() as td:
        restored=Path(td)/'restored';materialize_capsule(Path(archive),restored)
        return import_snapshot(restored/'evidence',Path(out))
