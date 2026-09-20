"""Bind imported metadata to a portable local dataset without changing source data."""
from pathlib import Path
import shutil,os
from cvsubstrate.contracts.models import DatasetManifest
from cvsubstrate.data.manifest import validate_manifest
from cvsubstrate.provenance.io import read_json,write_json,safe_join,file_digest,digest
from cvsubstrate.provenance.artifact_set import seal_directory,assert_not_inside_sealed
from cvsubstrate.errors import CVRSError

def materialize_dataset(manifest,image_root,output,*,mode='copy'):
    if mode not in {'copy','hardlink'}:raise ValueError('copy or explicitly chosen hardlink required')
    m=manifest if isinstance(manifest,DatasetManifest) else DatasetManifest.model_validate(read_json(manifest) if isinstance(manifest,(str,Path)) else manifest)
    root=Path(image_root).resolve();out=Path(output).resolve();assert_not_inside_sealed(out)
    if out.exists() or out.is_relative_to(root):raise CVRSError('OUTPUT_EXISTS','materialize into a fresh directory outside source images')
    validate_manifest(m,root,allow_noncrowd_ignore=True);out.mkdir(parents=True)
    seen=set()
    for sample in m.samples:
        if sample.image in seen:continue
        seen.add(sample.image);src=safe_join(root,sample.image);dst=safe_join(out,sample.image);dst.parent.mkdir(parents=True,exist_ok=True)
        if sample.image in {'dataset.json','materialization.json','integrity.json'}:raise ValueError('reserved artifact path collides with image')
        if mode=='copy':shutil.copyfile(src,dst)
        else:os.link(src,dst)
        if file_digest(dst)!=sample.sha256:raise CVRSError('SOURCE_CHANGED','image changed during materialization')
    write_json(out/'dataset.json',m);write_json(out/'materialization.json',{'dataset_digest':digest(m),'mode':mode,
        'source_modified':False,'images':len(seen),'note':'Hardlinks share source bytes; modifying either side invalidates hashes. Copy is the portable default.'})
    seal_directory(out);return {'status':'MATERIALIZED','dataset':str(out/'dataset.json'),'dataset_digest':digest(m),'images':len(seen)}
