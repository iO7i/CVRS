"""Controller-side inspection of measured native telemetry."""
import json, hashlib, sqlite3
from pathlib import Path
from cvsubstrate.provenance.io import write_json

def summarize_telemetry(database):
    from cvsubstrate.worker_shims.telemetry_runtime import TrainingLedger
    # Read-only connection; never create a SESSION_STARTED event during reporting.
    obj=TrainingLedger.__new__(TrainingLedger);obj.path=Path(database)
    obj.db=sqlite3.connect(obj.path.resolve().as_uri()+'?mode=ro',uri=True)
    identity=json.loads(obj.db.execute("SELECT v FROM meta WHERE k='identity'").fetchone()[0])
    obj.run_id=identity['run'];obj.rank=identity['rank'];obj.mixing_policy=identity['mixing_policy'];obj.world_size=identity.get('world_size');obj.sampler_shard=identity.get('sampler_shard')
    try:return obj.summary()
    finally:obj.db.close()

def aggregate_telemetry(paths, expected_ranks):
    rows=[summarize_telemetry(p) for p in paths]
    ranks=[r['rank'] for r in rows]
    if len(set(ranks))!=len(ranks) or set(ranks)!=set(expected_ranks):raise ValueError('complete unique rank coverage required')
    if len({r['run_id'] for r in rows})!=1:raise ValueError('different run IDs')
    totals={k:sum(r['source_exposures'][k] for r in rows) for k in ['real','synthetic','unknown']}
    steps={str(r['rank']):r['optimizer_step_calls'] for r in rows}
    return {'rank_reports':rows,'global_sample_exposures':totals,'optimizer_calls_by_rank':steps,
        'synchronized_updates':next(iter(steps.values())) if len(set(steps.values()))==1 else None,
        'synchronization_verified':False,
        'optimizer_note':'Do not sum synchronized DDP updates across ranks. Equal counts do not independently prove synchronization.',
        'source_accounting':'OBSERVED' if all(r['source_accounting']=='OBSERVED' for r in rows) else 'PARTIAL'}
