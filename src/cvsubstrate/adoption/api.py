"""Notebook-friendly public adoption facade. No ML imports at module import time."""
from pathlib import Path
from dataclasses import dataclass
from cvsubstrate.adoption.inspect import inspect_repository
from cvsubstrate.adoption.wrapping import wrap_repository,run_paper
from cvsubstrate.adoption.composition import run_composition
from cvsubstrate.adoption.methodology import lint_methodology,experiment_diff,reviewer_report

@dataclass(frozen=True)
class Experiment:
    path: Path
    def inspect(self):
        from cvsubstrate.provenance.io import read_json
        return read_json(Path(self.path))
    def run(self,output,*,worker_python=None,timeout=600):
        from cvsubstrate.execution.runner import run_experiment
        return Run(run_experiment(Path(self.path),Path(output),worker_python=worker_python,timeout=timeout))

@dataclass(frozen=True)
class Run:
    path: Path
    def verify(self):
        from cvsubstrate.provenance.bundle import verify_bundle
        return verify_bundle(Path(self.path))
    def metrics(self):
        from cvsubstrate.provenance.io import read_json
        return read_json(Path(self.path)/'metrics.json')
    def export_site(self,output):
        from cvsubstrate.publication.site import results_site
        return results_site([Path(self.path)],output)
    def export_bridge(self,bridge,payload,output,*,worker_python=None,allow_network=False):
        from cvsubstrate.bridges.service import run_bridge
        return run_bridge({'bridge':bridge,'operation':'export','payload':payload,'output_dir':str(output),
            'worker_python':worker_python,'trust_code':True,'allow_network':allow_network})
