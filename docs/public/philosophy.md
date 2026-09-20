# Why this is not OpenMMLab 3.0

OpenMMLab's scientific corpus remains valuable. CVRS does not claim ownership of it, official succession, or universal support for every MM task.

The project keeps model computation native and makes the boundaries explicit: which data, which exact model assets, which environment, which predictions, which evaluator, which evidence. A researcher can adopt prediction import first, then wrap execution later.

Isolation is useful when independently runnable components exchange outputs. It is not an automatic refactor of a jointly trained network or a fix for an internal dependency conflict. A mature adoption layer should explain when not to split a model.

FiftyOne, Supervision, TorchGeo, TerraTorch, W&B, MLflow, DVC, Code Ocean and OpenML solve substantial adjacent problems. CVRS integrates bounded exchanges rather than recreating their entire products.

No source-code line count, number of schemas, signed record or green badge substitutes for an actual scientifically relevant reproduction.
