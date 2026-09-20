# Research design and reviewer mode

Use the existing versioned experiment/campaign/benchmark contracts. Baseline and intervention runs retain their own source, environment, checkpoint, dataset, transformation and evaluation identities.

```bash
cvrs research lint methodology.json --out review.json
cvrs diff baseline.json treatment.json
cvrs review run-or-capsule
```

The methodology linter flags declared mismatches in real-sample exposures, optimizer updates, data population, evaluation fields, floating assets, oracle prompts and test access during selection. It also reports shared scene/asset/parent metadata crossing splits. These are review findings—not accusations and not proof that unobserved leakage is absent.

## A minimal methodology record

```json
{
  "arms": [
    {"id": "R", "real_exposures": 100, "optimizer_updates": 100, "exposure_source": "measured"},
    {"id": "R+S", "real_exposures": 100, "optimizer_updates": 200, "exposure_source": "measured"}
  ],
  "declared_interventions": []
}
```

This correctly highlights additional optimization. It does not call the synthetic intervention unfair automatically: the researcher must define the estimand and proper control.

## Re-evaluation and comparison

Saved predictions can be re-evaluated without rerunning a model. Preserve image/taxonomy/metric/threshold/ignore/maximum-detection/tiling identity. Official metrics need the actual reference evaluator; custom tiny-object and semantic diagnostics remain labeled custom.

Prompt origin matters. Ground-truth categories supplied as text are an oracle condition, not automatically equivalent to unsupervised discovery. HBB AP, semantic mIoU and prompted-mask IoU are not one ranking.

## Registry

Original execution, reproduction attempt, independent review and re-evaluation are different record types. Signatures prove key control over bytes, not that a result is scientifically true. Same-machine reruns do not earn independent-reproduction status.

Use the versioned registry CLI for claim/evidence graphs. `bridge reproduce` exports instructions and references, never restricted assets by accident.
