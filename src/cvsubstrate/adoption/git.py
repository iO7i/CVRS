"""Read-only source capture and explicit materialization into a NEW repository.

Git bundles and patches are executable-source inputs. No checkout in the user's
source repository, no remote fetch, no submodule initialization, no hook execution.
"""
from pathlib import Path
import subprocess,os,shutil
from cvsubstrate.adoption.common import output_tree,write_text
from cvsubstrate.provenance.io import write_json,read_json,file_digest,digest,safe_join
from cvsubstrate.provenance.artifact_set import verify_directory

def _git(root,*args,binary=False):
    env={**os.environ,'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':os.devnull,'GIT_TERMINAL_PROMPT':'0'}
    result=subprocess.run(['git','-c','core.hooksPath='+os.devnull,'-c','core.fsmonitor=false','-C',str(root),*args],
        capture_output=True,timeout=120,env=env)
    if result.returncode:raise ValueError('Git operation failed: '+result.stderr.decode('utf8','replace')[-1000:])
    return result.stdout if binary else result.stdout.decode('utf8','replace').strip()

def capture_source(repo,destination,*,include_untracked=False,max_bytes=64*1024*1024):
    repo=Path(repo).resolve();rev=_git(repo,'rev-parse','HEAD')
    with output_tree(destination) as out:
        _git(repo,'bundle','create',str(out/'source.bundle'),'HEAD')
        patch=_git(repo,'diff','--binary','HEAD','--',binary=True)
        if len(patch)>max_bytes:raise ValueError('source patch too large')
        (out/'working.patch').write_bytes(patch)
        untracked=_git(repo,'ls-files','--others','--exclude-standard','-z',binary=True).decode('utf8').split('\0')
        included={};total=len(patch)
        if include_untracked:
            for name in filter(None,untracked):
                p=safe_join(repo,name)
                if p.is_symlink() or not p.is_file():raise ValueError('untracked source must be a regular file')
                total+=p.stat().st_size
                if total>max_bytes:raise ValueError('untracked source exceeds budget')
                target=safe_join(out/'untracked',name);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
                included[name]=file_digest(target)
        modules=_git(repo,'submodule','status','--recursive')
        write_json(out/'source.json',{'revision':rev,'bundle_sha256':file_digest(out/'source.bundle'),
            'patch_sha256':file_digest(out/'working.patch'),'untracked':included,
            'untracked_omitted':[x for x in untracked if x and x not in included],
            'submodules':modules.splitlines(),'submodule_policy':'Referenced commits only; external sources must be supplied separately',
            'contains_git_history':True,'publication_warning':'Review repository history and patch for secrets before sharing'})
    return {'status':'CAPTURED','destination':str(destination),'revision':rev}

def materialize_source(capsule,destination,*,trust=False):
    if not trust:raise ValueError('explicit trust required for captured executable source/history')
    capsule=Path(capsule);v=verify_directory(capsule)
    if v['status']!='VERIFIED':raise ValueError('source capture integrity failed')
    meta=read_json(capsule/'source.json')
    with output_tree(destination,seal=False) as out:
        _git(out,'init','--quiet')
        _git(out,'fetch','--no-tags',str((capsule/'source.bundle').resolve()),'HEAD')
        _git(out,'checkout','--detach',meta['revision'])
        if (capsule/'working.patch').stat().st_size:
            _git(out,'apply','--check',str((capsule/'working.patch').resolve()))
            _git(out,'apply','--binary',str((capsule/'working.patch').resolve()))
        for name,expected in meta['untracked'].items():
            source=safe_join(capsule/'untracked',name)
            if file_digest(source)!=expected:raise ValueError('untracked file hash mismatch')
            target=safe_join(out,name)
            if target.exists():raise ValueError('untracked capture collides with tracked source')
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    return {'status':'MATERIALIZED','revision':meta['revision'],'destination':str(destination),
        'unresolved_submodules':meta['submodules'],'remote_fetch':False}
