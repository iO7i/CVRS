"""Execute a real CPU checkpoint continuation test; requires native dependencies."""
import argparse
from pathlib import Path
from cvsubstrate.data.manifest import load_manifest
from cvsubstrate.workers.native_torch import resume_selftest
p = argparse.ArgumentParser()
p.add_argument('dataset', type=Path)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
print(resume_selftest(load_manifest(a.dataset), a.dataset.resolve().parent, a.out))
