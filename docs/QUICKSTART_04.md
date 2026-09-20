# Reproducible local quickstart

Run commands at repository root after dedicated-environment installation. No command below automatically fetches models/datasets. The source fixtures are synthetic software fixtures; importing a DOTA-shaped text file does not prove DOTA performance.

## Dependency-light

```bash
cvrs groundwork-fixtures ./demo
cvrs schema list
cvrs schema validate demo/large-plan.json --schema LargeImagePlan
cvrs migrate demo/size-envelope-legacy.json --out demo/migrated-envelope.json
cvrs graph run demo/graph.json --out demo/graph --cache demo/cache
cvrs graph run demo/graph.json --out demo/graph --cache demo/cache --resume
cvrs dataset import demo/dataset-coco.json --out demo/import-coco
cvrs dataset materialize demo/import-coco/dataset.json --image-root demo/base --out demo/portable-dataset
cvrs campaign compile demo/campaign.json --out demo/campaign-plan.json
cvrs campaign budgets demo/campaign.json
cvrs campaign sweep demo/campaign.json --axes demo/sweep-axes.json --out demo/sweep
cvrs benchmark register demo/benchmark.json --registry demo/registry
cvrs capsule create demo/import-coco --out demo/capsule
cvrs capsule archive demo/capsule --out demo/capsule.zip
cvrs capsule materialize demo/capsule.zip --out demo/restored-capsule
cvrs plugin scaffold my_dataset_adapter --kind dataset --out demo/my-plugin
```

## Optional image/CPU tools

```bash
# Select only dependencies you need; native frameworks can live in their own venv.
python -m pip install -e '.[native]'
cvrs distribution describe demo/base/dataset.json --image-stats --out demo/distribution.json
cvrs size-evaluate demo/fixture-predictions.jsonl --dataset demo/base/dataset.json --policy demo/size-policy.json --out demo/tiny.json
cvrs large plan demo/large-plan.json --out demo/tile-plan.json
cvrs run demo/base/real.json --out demo/run --timeout 120
cvrs large run demo/inference.json --policy demo/large-policy.json --out demo/large-run --timeout 120
```

The fixture generator writes the inference-only spec and policy shown above. Inspect their explicit data/geometry settings before applying them to another dataset.

## Tensor export, not pretrained-detector certification

```bash
cvrs deploy export demo/deployment.json --out demo/export --timeout 45
cvrs deploy infer demo/deployment.json --out demo/native-tensor --timeout 45
```

The fixture is a small trusted local Torch factory, not a model from the internet. To execute exported inference, derive a new DeploymentSpec referring to `demo/export/model.pt2` and its SHA-256, retaining the exact input arrays. `cvrs deploy compare-arrays` compares sealed native/exported runs. Output order/name maps must be explicit if runtimes rename tensors.

## Tests you choose to run

```bash
python -m pytest tests -m 'not native and not heritage'
python -m pytest tests/test_groundwork_04.py -m native
```

A full native suite includes repeated model training/campaigns and can exceed session time limits. Use `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1` and a suitable per-job timeout. No external heritage/scientific certification is inferred from these tests. See the recorded 0.4 test logs for exactly what this build executed.
