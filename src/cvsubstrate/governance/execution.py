"""Governed final evaluation: charge an approval before execution, retain failures."""
from pathlib import Path
from cvsubstrate.governance.ledger import Ledger
from cvsubstrate.provenance.bundle import verify_bundle
from cvsubstrate.execution.runner import run_experiment


def run_final_test(spec:Path,output:Path,ledger:Ledger,approval_digest:str,*,worker_python=None,timeout=180.):
    try:
        run=run_experiment(spec,output,worker_python=worker_python,timeout=timeout,
                           access_ledger=ledger,approval_digest=approval_digest)
    except Exception as exc:
        ledger.append('FINAL_TEST_ATTEMPT_FAILED',{'approval_digest':approval_digest,
            'error_code':getattr(exc,'code',type(exc).__name__),'reason':str(exc)})
        raise
    report={'run':str(run),'verification':verify_bundle(run),'approval_digest':approval_digest}
    ledger.append('FINAL_TEST_ATTEMPT_COMPLETED',report)
    return report
