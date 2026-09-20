# ADR-005

Status: adopted for technical foundation; license grant pending owner approval where relevant.

## Decision

Reference evaluation and local diagnostics are distinct products.

## Rationale and consequences

Use the official pycocotools API for COCO metrics. No fallback when absent. Fixed-threshold diagnostics have different names and no AP claim. Metric compatibility does not prove fair training.
