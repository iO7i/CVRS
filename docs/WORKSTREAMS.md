# Subsequent multi-agent ownership

The lead integrator owns versioned contracts and approves interface changes before
parallel implementation. Use isolated worktrees and narrow diffs.

1. Heritage team: execute native legacy integration, prove revision/weights/config
   identity, preserve upstream behavior. It must not certify its own parity results.
2. Evaluation team: run the official COCO path, independently construct comparison
   fixtures, investigate area/crowd/tile edge cases, and define dataset protocols.
3. Native-adapter team: introduce one standard pretrained detector without changing
   core data/evaluation semantics. Preserve its preprocessing and native outputs.
4. Data/protocol team: real datasets with license/split lineage, matched controls,
   tile integration, measured source exposure, no sealed-test tuning.
5. Independent verification team: rerun all claims from clean environments, review
   negative tests and failure artifacts, report discrepancies without editing goldens
   to match the implementation.
6. Release/docs team: compatibility/evidence tables, actual installation matrix,
   redaction review, packaging, and user onboarding.

Human gates: licensing choice, scope, abstraction boundaries, compatibility promises,
scientific controls, expensive compute, public publishing, and external claims.
AI-generated geometry, matching, scheduler equivalence, checkpoint mapping, and
numeric conversions always require empirical evidence.
