"""One-use, input-bound final evaluation for every registered perception task.

This is local scientific accountability, not operating-system access control.
An attempt consumes its authorization before evaluation, including failed attempts.
"""
from pathlib import Path
from cvsubstrate.provenance.io import file_digest,digest
from cvsubstrate.contracts.research import AccessApproval
from cvsubstrate.governance.ledger import Ledger
from cvsubstrate.governance.policy import approve_final_test,consume_final_test


def task_evaluation_identity(spec):
    files={k:file_digest(Path(spec[k])) for k in ('dataset','predictions','protocol')}
    semantic={k:v for k,v in spec.items() if k not in {'dataset','predictions','protocol','authorization'}}
    return {'dataset_digest':files['dataset'],'experiment_digest':digest({'task_evaluation':semantic,'files':files}),
            'split':spec.get('split','locked_test'),'files':files}


def authorize_task_evaluation(spec,ledger_path,*,approved_by,reason,max_uses=1):
    identity=task_evaluation_identity(spec)
    approval=AccessApproval(dataset_digest=identity['dataset_digest'],experiment_digest=identity['experiment_digest'],
        split=identity['split'],approved_by=approved_by,reason=reason,max_uses=max_uses)
    record=approve_final_test(Ledger(Path(ledger_path)),approval)
    return {'approval_digest':record['payload']['approval_digest'],'identity':identity,'ledger':str(Path(ledger_path).resolve()),
            'meaning':'charged before attempted evaluation; not independent authorization or file confidentiality'}


def consume_task_authorization(spec):
    auth=spec.get('authorization')
    if not isinstance(auth,dict) or set(auth)!={'ledger','approval_digest'}:raise ValueError('exact task authorization ledger and approval_digest required')
    identity=task_evaluation_identity(spec)
    approval,event=consume_final_test(Ledger(Path(auth['ledger'])),auth['approval_digest'],
        dataset_digest=identity['dataset_digest'],experiment_digest=identity['experiment_digest'],split=identity['split'])
    return {'approval':approval,'access_event':event,'identity':identity}
