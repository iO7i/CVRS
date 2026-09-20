# ADR-004

Status: adopted for technical foundation; license grant pending owner approval where relevant.

## Decision

Hash materialized specs and content separately from execution IDs.

## Rationale and consequences

Paths are locators; source/checkpoint/data hashes are identity. Preserve list order and defaults. Unsigned manifests demonstrate integrity relative to themselves, not authenticity.
