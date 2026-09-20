"""Preregistration, seed accountability and one-use final-test approvals."""
from pathlib import Path
from cvsubstrate.contracts.research import AccessApproval, CampaignSpec
from cvsubstrate.errors import CVRSError
from cvsubstrate.governance.ledger import Ledger
from cvsubstrate.provenance.io import digest


def preregister(ledger: Ledger, campaign: CampaignSpec, plan_digest: str):
    data=campaign.model_dump(mode='json');identity=digest(data)
    def validate(rows):
        if any(r['event']=='CAMPAIGN_PREREGISTERED' and r['payload'].get('campaign_digest')==identity for r in rows):
            raise CVRSError('ALREADY_REGISTERED','campaign already preregistered in this ledger')
        if campaign.phase=='confirmatory':
            # Same dataset family: a fresh integer seed in another project is not
            # automatically disallowed. All history scope is explicit in payload.
            datasets={b.experiment.dataset_sha256 for b in campaign.backends}
            prior=set(campaign.previous_seeds)
            for r in rows:
                p=r['payload']
                if r['event']=='CAMPAIGN_PREREGISTERED' and datasets.intersection(p.get('dataset_digests',[])):
                    prior.update(p.get('seeds',[]))
            if prior.intersection(campaign.seeds):
                raise CVRSError('SEED_REUSE','confirmation reuses a recorded selection/exploration seed')
    return ledger.consume('CAMPAIGN_PREREGISTERED',{
        'campaign_digest':identity,'plan_digest':plan_digest,'phase':campaign.phase,
        'dataset_digests':sorted({b.experiment.dataset_sha256 for b in campaign.backends}),
        'seeds':campaign.seeds,'arms':campaign.arms,'selection_record_digest':campaign.selection_record_digest,
    },validate=validate)


def approve_final_test(ledger: Ledger, approval: AccessApproval):
    value=approval.model_dump(mode='json');identity=digest(value)
    def check(rows):
        if any(r['event']=='FINAL_TEST_APPROVED' and r['payload']['approval_digest']==identity for r in rows):
            raise CVRSError('ALREADY_APPROVED','approval is already recorded; do not reset its usage counter')
    return ledger.consume('FINAL_TEST_APPROVED',{'approval_digest':identity,'approval':value},validate=check)


def consume_final_test(ledger: Ledger, approval_digest: str, *, dataset_digest: str, experiment_digest: str, split: str):
    match={}
    def check(rows):
        approvals=[r for r in rows if r['event']=='FINAL_TEST_APPROVED' and r['payload'].get('approval_digest')==approval_digest]
        if len(approvals)!=1:
            raise CVRSError('TEST_APPROVAL','one recorded approval is required')
        a=AccessApproval.model_validate(approvals[0]['payload']['approval'])
        if (a.dataset_digest,a.experiment_digest,a.split)!=(dataset_digest,experiment_digest,split):
            raise CVRSError('TEST_APPROVAL_IDENTITY','approval is not bound to this exact experiment/data/split')
        uses=sum(r['event']=='FINAL_TEST_ACCESS' and r['payload'].get('approval_digest')==approval_digest for r in rows)
        if uses>=a.max_uses:
            raise CVRSError('TEST_ACCESS_EXHAUSTED','approval has no remaining uses')
        match.update(a.model_dump(mode='json'))
    record=ledger.consume('FINAL_TEST_ACCESS',{'approval_digest':approval_digest,'dataset_digest':dataset_digest,
        'experiment_digest':experiment_digest,'split':split,'scope':'attempt charged before worker execution'},validate=check)
    return match,record


def final_test_report(ledger: Ledger):
    rows=ledger.rows()
    accesses=[r for r in rows if r['event']=='FINAL_TEST_ACCESS']
    return {'status':'ACCOUNTING_ONLY','access_attempts':len(accesses),'accesses':accesses,
        'ledger':ledger.verify(),'limits':'Local API policy, not cryptographic secrecy; access outside this API is unobservable.'}
