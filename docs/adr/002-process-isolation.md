# ADR-002

Status: adopted for technical foundation; license grant pending owner approval where relevant.

## Decision

Framework workers use explicit separate Python interpreters.

## Rationale and consequences

A working legacy stack and a new Torch stack need not coexist. The controller exchanges validated file contracts. Processes are not security sandboxes. No generic shell commands or hidden fallback backends.
