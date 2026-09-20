"""Cross-platform developer tasks; no Bash/Make required on Windows."""
from pathlib import Path
import sys,subprocess,tempfile,os
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('OMP_NUM_THREADS','1');os.environ.setdefault('MKL_NUM_THREADS','1')
def run(args):return subprocess.run([sys.executable,*args],cwd=ROOT,check=True).returncode

def main():
    task=sys.argv[1] if len(sys.argv)>1 else 'check'
    if task=='check':return run(['-m','pytest','-m','not native'])
    if task=='lint':return run(['-m','ruff','check','src','tests','tools'])
    if task=='typecheck':return run(['-m','mypy','src/cvsubstrate/adoption','src/cvsubstrate/bridges','src/cvsubstrate/publication','src/cvsubstrate/product','src/cvsubstrate/cli_product.py','--follow-imports=silent','--ignore-missing-imports'])
    if task=='reference':
        from cvsubstrate.cli_adoption import parser
        from cvsubstrate.schemas.registry import export_schemas
        (ROOT/'docs/public/commands.md').write_text('# Adoption commands\n\n```text\n'+parser().format_help()+'\n```\n\nFor a group: `cvrs paper --help`, `cvrs bridge --help`, etc. The earlier task commands remain available.\n')
        export_schemas(ROOT/'schemas')
        from cvsubstrate.publication.reference import generate_public_reference
        print(generate_public_reference(ROOT));return 0
    if task in {'docs','public-preview','demo'}:
        with tempfile.TemporaryDirectory(prefix='cvrs-dev-') as td:
            dest=str(Path(td)/'out')
            if task=='docs':
                run(['-m','cvsubstrate','docs','build',str(ROOT),'--out',dest]);return run(['-m','cvsubstrate','docs','link-check',dest])
            if task=='public-preview':return run(['-m','cvsubstrate','release','publish-bundle',str(ROOT),'--out',dest,'--preview'])
            return run(['-m','cvsubstrate','demo-all',dest])
    raise SystemExit('task: check | lint | typecheck | reference | docs | public-preview | demo')
if __name__=='__main__':raise SystemExit(main())
