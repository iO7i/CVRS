# Slice 02 examples

1. Copy `heritage-reference.template.json` and replace every identity placeholder with observed values.
2. Run `cvrs heritage inspect` and `cvrs heritage adapter`.
3. Create an `ExperimentSpec` pointing at the same dataset manifest/evaluation protocol used by the contemporary backend.
4. Run with `--worker-python` set to the historical environment.
5. Run the contemporary backend separately.
6. Use `cvrs reference-parity` for the pinned COCO evaluator audit and `cvrs cross-compare` for the common-measurement report.

Templates are not execution evidence.
