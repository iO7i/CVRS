# Contributing

Use Python 3.11+ for the controller and separate native environments for models. Install `.[dev,adoption]`, then run `python tools/dev.py check`. GPU/data-dependent tests are not required for a documentation-only change.

## Add an adapter

Generate `cvrs adapter new`, declare only implemented operations, wrap the original native code, normalize one explicit task, and add malformed/empty-output fixtures. Use a separately configured interpreter for conformance. Do not fabricate successful native results in a structural test.

## Add a dataset or evaluator

Preserve label/coordinate/ignore semantics and a reference protocol. Record any conversion loss. Keep large or restricted datasets out of Git; generate minimal format fixtures locally.

## Add a paper recipe

Cite primary project/paper sources, name the inspected date, distinguish commands from candidates, and leave unknown revisions/assets unresolved. Never mark a recipe executed from README inspection.

## Change a schema or core protocol

Open an RFC, specify the compatibility impact, add an immutable historical fixture and explicit migration behavior, then update generated references. Do not equate a package version with a benchmark version.

## Submission

Describe source/license provenance, optional dependencies, trust boundary and actual evidence. Failed experiments are useful. Passing a mock transport test does not certify MMDetection/SAM/etc.

The original-code license must be approved by the owner before accepting public contributions under it. No contribution agreement is silently invented here.
