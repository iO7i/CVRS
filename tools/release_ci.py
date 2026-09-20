"""Build approved publication artifacts on an unprivileged CI runner.

No upload, repository mutation, API token or OIDC token is needed by this script.
The downstream publisher consumes only these verified wheel/sdist files.
"""
from __future__ import annotations
import os
import shutil
import sys
import tempfile
from pathlib import Path
from cvsubstrate.product.launch import preflight, verify_artifacts
from cvsubstrate.provenance.io import write_json, digest, file_digest
from cvsubstrate.publication.build import publish_bundle
from cvsubstrate.foundation.identity import COMPONENT_VERSIONS


def artifacts(root: Path, output: Path):
    state=preflight(root,require_clean=True)
    if state['status']!='READY_FOR_OWNER_RELEASE_REVIEW':
        raise ValueError('release preflight blocked: '+str([x for x in state['checks'] if x['status']=='BLOCK']))
    tag=os.environ.get('CVRS_RELEASE_TAG')
    if tag!='v'+state['version']:raise ValueError('dispatch from the exact annotated/reviewed v<version> tag')
    if not os.environ.get('CVRS_RELEASE_REPOSITORY'):raise ValueError('CI repository identity is required')
    if output.exists():raise ValueError('publication output already exists')
    with tempfile.TemporaryDirectory() as td:
        bundle=Path(td)/'bundle'
        publish_bundle(root,bundle,preview=False)
        output.mkdir(parents=True);(output/'packages').mkdir()
        for p in (bundle/'dist').iterdir():
            if p.suffix=='.whl' or p.name.endswith('.tar.gz'):shutil.copyfile(p,output/'packages'/p.name)
        shutil.copyfile(bundle/'sbom/build-environment.cdx.json',output/'build-environment.cdx.json')
        notes=(root/'RELEASE_NOTES.md').read_text() if (root/'RELEASE_NOTES.md').exists() else '# '+tag+'\n\nSee the packaged source and explicit compatibility boundaries.\n'
        (output/'RELEASE_NOTES.md').write_text(notes)
        value={'schema_version':'1.0','distribution':state['distribution'],'version':state['version'],'tag':tag,
               'repository':state['repository'],'git_commit':os.environ.get('GITHUB_SHA'),'components':COMPONENT_VERSIONS,
               'origin':'unprivileged build; external attestation is a separate job',
               'artifacts':{p.relative_to(output).as_posix():{'bytes':p.stat().st_size,'sha256':file_digest(p)} for p in sorted(output.rglob('*')) if p.is_file()}}
        value['manifest_digest']=digest(value);write_json(output/'release-artifacts.json',value)
        (output/'SHA256SUMS').write_text(''.join(v['sha256']+'  '+k+'\n' for k,v in value['artifacts'].items())+file_digest(output/'release-artifacts.json')+'  release-artifacts.json\n')
        return verify_artifacts(output/'release-artifacts.json')


if __name__=='__main__':
    if len(sys.argv)!=3 or sys.argv[1]!='artifacts':raise SystemExit('python tools/release_ci.py artifacts OUTPUT')
    print(artifacts(Path(__file__).resolve().parents[1],Path(sys.argv[2]).resolve()))
