"""Sanitized support bundles; no data, model weights or environment secrets."""
from pathlib import Path
import json,zipfile
from cvsubstrate.security import sanitize
from cvsubstrate.adoption.common import output_tree
from cvsubstrate.adoption.environments import doctor
from cvsubstrate.provenance.io import read_json,write_json,file_digest

ALLOWED={'environment.json','execution.json','result.json','failure.json','experiment.json','events.jsonl','request.json','error.json','metrics.json'}

def support_bundle(run,destination,max_bytes=2*1024*1024):
    root=Path(run).resolve()
    with output_tree(destination) as out:
        copied=[]
        for p in sorted(root.iterdir()):
            if p.name not in ALLOWED or p.is_symlink() or not p.is_file() or p.stat().st_size>max_bytes:continue
            text=p.read_text('utf-8')
            # Parse before redaction; keys containing credential/token are removed by sanitizer.
            try:value=read_json(p) if p.suffix!='.jsonl' else [json.loads(x) for x in text.splitlines() if x.strip()]
            except (ValueError,TypeError):value={'unparsed_text':text}
            clean=sanitize(value);
            def portable(x):
                import re
                if isinstance(x,str):return re.sub(r'/mnt/data/[^\s\"\']+','<WORKSPACE_PATH>',x)
                if isinstance(x,dict):return {k:portable(v) for k,v in x.items()}
                if isinstance(x,list):return [portable(v) for v in x]
                return x
            clean=portable(clean);write_json(out/(p.name+'.json'),clean);copied.append(p.name)
        write_json(out/'doctor.json',sanitize(doctor()))
        write_json(out/'support.json',{'included':copied,'excluded':['images','datasets','checkpoints','private keys','unlisted files','raw binary logs'],
             'warning':'Best-effort sanitization. Review the bundle before sharing.'})
    return {'status':'CREATED_REVIEW_REQUIRED','destination':str(destination),'included':copied}
