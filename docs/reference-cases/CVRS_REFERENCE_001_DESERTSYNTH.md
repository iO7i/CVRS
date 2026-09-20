# CVRS Reference Qualification 001 — Desert Vehicle Sim2Real

This concise compatibility case records an external research workflow exercised against CVRS 0.7.1a2. The complete evidence remains in the independent research repository; this document does not vendor that project.

## Workflow families exercised

- legacy academic MMDetection/CUDA stack;
- historical evidence ingestion;
- real remote read-only native execution;
- real state-changing optimizer execution and checkpoint lineage;
- protected-data governance;
- portable independent evidence reproduction.

## Qualification outcome

| Campaign | Result |
| --- | --- |
| A — archival reconstruction | `COMPLETE_WITH_LIMITATIONS` |
| B — production/read-only interoperability | `FAIL_CVRS` |
| C — state-changing execution | `PASS_CVRS_QUALIFICATION_ONLY` |
| D — evaluator/reproduction | `FAIL_CVRS_EVALUATOR` |
| E — portable verification | `PASS_PORTABLE_REPRODUCTION` |

## Known limitation retained

Native/legacy geometry outside canonical image bounds can block prediction or COCO-ground-truth import. CVRS rejects these records rather than silently clipping or re-inferring them. B and D remain failures by design; this case does not authorize a geometry patch.

## Evidence pointer

The external evidence-bound case is identified as `CVRS_REFERENCE_001` and is stored with its qualification matrix and Campaign E portable manifest in the DesertSynth repository under `reports/cvrs/reference-001/`. Hashes, protected-data status, and scientific/qualification separation are recorded there.

The CVRS structural receipt remains conservative: it records the available interface, but does not self-assign native execution, metric reproduction, or scientific validity.
