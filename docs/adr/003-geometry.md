# ADR-003

Status: adopted for technical foundation; license grant pending owner approval where relevant.

## Decision

Continuous original-image xyxy is the first certified geometry.

## Rationale and consequences

Keep category IDs stable and record transforms. Reject invalid boxes rather than silently clipping. OBB and full geospatial transforms are deferred until independent numerical references exist.
