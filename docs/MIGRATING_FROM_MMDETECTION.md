# Moving an existing MMDetection project into CVRS

The migration path is **wrap first, rewrite never unless desired**.

## 1. Keep the working MMDetection environment unchanged

Do not upgrade its Python/PyTorch/MMCV/MMEngine merely to satisfy the controller. Record its interpreter path and source revision. CVRS launches a standalone stdlib bridge inside that environment.

## 2. Record a heritage reference

Create a `LegacyExperimentRef` with:

- OpenMMLab or explicitly supported fork identity;
- source revision;
- original config and SHA-256;
- checkpoint reference/SHA-256/trust and separate weight-license status;
- environment capsule;
- dataset/taxonomy identity when known.

`cvrs heritage inspect REF.json` performs static inspection only. It never executes the Python config.

`cvrs heritage adapter REF.json` emits an adapter fragment. The user must fill the category map explicitly.

## 3. Run natively

```sh
cvrs run experiment.json --worker-python /path/to/heritage/python
```

The old interpreter executes MMDetection's own `Config.fromfile`, `init_detector`, and `inference_detector`. The controller never imports MMCV/MMDetection.

## 4. Preserve both outputs

CVRS retains the native arrays and canonical output. A conversion audit reconciles image count, detection count, boxes, scores, and category mapping. No unmapped class is silently filtered.

## 5. Certify only what was demonstrated

- H0: catalogued
- H1: native config resolved
- H2: real inference executed
- H3: native/canonical output parity verified
- H4: published/reference metric reproduced on the exact reference data/protocol
- H5: training reproduced

```sh
cvrs heritage certify REF.json --run RUN_DIR --out certification.json
```

A subset run cannot earn H4 for a full COCO model-zoo score.

## 6. Compare with a modern backend without pretending training was fair

After a second backend run uses the same dataset/evaluation contract:

```sh
cvrs cross-compare OLD_RUN NEW_RUN
```

The report distinguishes common measurement protocol from matched training/pretraining/compute. It does not manufacture a leaderboard claim.
