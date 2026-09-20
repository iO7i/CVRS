# ADR-006

Status: adopted for technical foundation; license grant pending owner approval where relevant.

## Decision

Keep historical configs and checkpoints native initially.

## Rationale and consequences

Static inspection does not execute Python or fully resolve inheritance. Trusted upstream tooling resolves configs in a separate worker. No broad state-dict migration or false upstream endorsement.
