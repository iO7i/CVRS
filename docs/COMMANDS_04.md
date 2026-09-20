# Command reference — generated from 0.4 parsers

JSON specs have explicit versions. All optional workers accept an explicit interpreter; no implicit framework download is performed. Commands that overlap older versions retain legacy forms.

## `cvrs artifact`

```text
usage: cvrs artifact [-h]
```

## `cvrs artifact exists`

```text
usage: cvrs artifact exists [-h] --store STORE sha256
```

## `cvrs artifact get`

```text
usage: cvrs artifact get [-h] --store STORE --out OUT sha256
```

## `cvrs artifact put`

```text
usage: cvrs artifact put [-h] --store STORE source
```

## `cvrs artifact verify`

```text
usage: cvrs artifact verify [-h] --store STORE sha256
```

## `cvrs artifact-verify`

```text
usage: cvrs artifact-verify [-h] directory
```

## `cvrs audit-predictions`

```text
usage: cvrs audit-predictions [-h] [--box-atol BOX_ATOL]
                              [--score-atol SCORE_ATOL]
                              [--order {as_emitted,canonical_sort}]
                              [--out OUT]
                              left right
```

## `cvrs backbone`

```text
usage: cvrs backbone [-h]
```

## `cvrs backbone extract`

```text
usage: cvrs backbone extract [-h] --out OUT [--worker-python WORKER_PYTHON]
                             [--timeout TIMEOUT]
                             spec
```

## `cvrs benchmark`

```text
usage: cvrs benchmark [-h]
```

## `cvrs benchmark access-log`

```text
usage: cvrs benchmark access-log [-h] ledger
```

## `cvrs benchmark authorize-final`

```text
usage: cvrs benchmark authorize-final [-h] --ledger LEDGER [--out OUT] spec
```

## `cvrs benchmark final-eval`

```text
usage: cvrs benchmark final-eval [-h] --ledger LEDGER
                                 --approval-digest APPROVAL_DIGEST --out OUT
                                 [--worker-python WORKER_PYTHON]
                                 [--timeout TIMEOUT]
                                 [--evaluator-python EVALUATOR_PYTHON]
                                 benchmark experiment
```

## `cvrs benchmark list`

```text
usage: cvrs benchmark list [-h] --registry REGISTRY
```

## `cvrs benchmark orchestrate`

```text
usage: cvrs benchmark orchestrate [-h] --out OUT
                                  [--worker-python WORKER_PYTHON]
                                  [--timeout TIMEOUT] [--resume]
                                  [--retry-failed]
                                  spec
```

## `cvrs benchmark preregister`

```text
usage: cvrs benchmark preregister [-h] --ledger LEDGER [--out OUT] spec
```

## `cvrs benchmark register`

```text
usage: cvrs benchmark register [-h] --registry REGISTRY spec
```

## `cvrs benchmark submission-check`

```text
usage: cvrs benchmark submission-check [-h] [--out OUT] benchmark run
```

## `cvrs cache`

```text
usage: cvrs cache [-h]
```

## `cvrs cache exists`

```text
usage: cvrs cache exists [-h] --store STORE sha256
```

## `cvrs cache get`

```text
usage: cvrs cache get [-h] --store STORE --out OUT sha256
```

## `cvrs cache put`

```text
usage: cvrs cache put [-h] --store STORE source
```

## `cvrs cache verify`

```text
usage: cvrs cache verify [-h] --store STORE sha256
```

## `cvrs campaign budgets`

```text
usage: cvrs campaign budgets [-h] [--out OUT] spec
```

## `cvrs campaign compile`

```text
usage: cvrs campaign compile [-h] [--out OUT] spec
```

## `cvrs campaign plan`

```text
usage: cvrs campaign plan [-h] [--out OUT] spec
```

## `cvrs campaign report`

```text
usage: cvrs campaign report [-h] [--out OUT] campaign
```

## `cvrs campaign run`

```text
usage: cvrs campaign run [-h] --out OUT [--resume] [--retry-failed]
                         [--worker-python WORKER_PYTHON]
                         spec
```

## `cvrs campaign run-stages`

```text
usage: cvrs campaign run-stages [-h] --out OUT [--worker-python WORKER_PYTHON]
                                [--timeout TIMEOUT] [--resume]
                                [--retry-failed]
                                spec
```

## `cvrs campaign sweep`

```text
usage: cvrs campaign sweep [-h] --axes AXES --out OUT [--max-cases MAX_CASES]
                           spec
```

## `cvrs capabilities`

```text
usage: cvrs capabilities [-h]
                         [--adapter {native_torch,mmdetection,ultralytics,rfdetr}]
                         [--worker-python WORKER_PYTHON]
```

## `cvrs capsule`

```text
usage: cvrs capsule [-h] --out OUT [--packages PACKAGES [PACKAGES ...]]
                    [--declaration DECLARATION] [--base-image BASE_IMAGE]
```

## `cvrs capsule archive`

```text
usage: cvrs capsule archive [-h] --out OUT source
```

## `cvrs capsule create`

```text
usage: cvrs capsule create [-h] --out OUT [--references REFERENCES]
                           [--include [INCLUDE ...]]
                           source
```

## `cvrs capsule inspect`

```text
usage: cvrs capsule inspect [-h] source
```

## `cvrs capsule materialize`

```text
usage: cvrs capsule materialize [-h] --out OUT source
```

## `cvrs capsule validate`

```text
usage: cvrs capsule validate [-h] source
```

## `cvrs catalogue`

```text
usage: cvrs catalogue [-h] [--source-root SOURCE_ROOT] catalogue
```

## `cvrs checkpoint`

```text
usage: cvrs checkpoint [-h]
```

## `cvrs checkpoint convert`

```text
usage: cvrs checkpoint convert [-h] [--worker-python WORKER_PYTHON]
                               [--timeout TIMEOUT] --out OUT
                               spec
```

## `cvrs checkpoint inspect`

```text
usage: cvrs checkpoint inspect [-h] [--worker-python WORKER_PYTHON]
                               [--timeout TIMEOUT] [--out OUT]
                               spec
```

## `cvrs compare`

```text
usage: cvrs compare [-h] left right
```

## `cvrs cross-compare`

```text
usage: cvrs cross-compare [-h] [--out OUT] left right
```

## `cvrs dataset`

```text
usage: cvrs dataset [-h] [--metadata-only] {validate} manifest
```

## `cvrs dataset export-world`

```text
usage: cvrs dataset export-world [-h] --georeferences GEOREFERENCES
                                 [--format {geojson,json,csv}] --out OUT
                                 predictions
```

## `cvrs dataset geo-manifest`

```text
usage: cvrs dataset geo-manifest [-h] --out OUT spec
```

## `cvrs dataset import`

```text
usage: cvrs dataset import [-h] --out OUT spec
```

## `cvrs dataset inspect-geo`

```text
usage: cvrs dataset inspect-geo [-h] [--sidecar SIDECAR] [--out OUT] source
```

## `cvrs dataset materialize`

```text
usage: cvrs dataset materialize [-h] --image-root IMAGE_ROOT --out OUT
                                [--mode {copy,hardlink}]
                                manifest
```

## `cvrs demo`

```text
usage: cvrs demo [-h] [--worker-python WORKER_PYTHON] [--timeout TIMEOUT]
                 destination
```

## `cvrs deploy`

```text
usage: cvrs deploy [-h]
```

## `cvrs deploy compare-arrays`

```text
usage: cvrs deploy compare-arrays [-h] [--out OUT] [--atol ATOL] [--rtol RTOL]
                                  [--names NAMES]
                                  left right
```

## `cvrs deploy compare-detections`

```text
usage: cvrs deploy compare-detections [-h] [--out OUT] left right
```

## `cvrs deploy compare-metrics`

```text
usage: cvrs deploy compare-metrics [-h] [--out OUT] left right
```

## `cvrs deploy decode`

```text
usage: cvrs deploy decode [-h] --out OUT run spec
```

## `cvrs deploy export`

```text
usage: cvrs deploy export [-h] --out OUT [--worker-python WORKER_PYTHON]
                          [--timeout TIMEOUT]
                          spec
```

## `cvrs deploy infer`

```text
usage: cvrs deploy infer [-h] --out OUT [--worker-python WORKER_PYTHON]
                         [--timeout TIMEOUT]
                         spec
```

## `cvrs distribution`

```text
usage: cvrs distribution [-h]
```

## `cvrs distribution compare`

```text
usage: cvrs distribution compare [-h] [--out OUT] left right
```

## `cvrs distribution describe`

```text
usage: cvrs distribution describe [-h] [--split SPLIT] [--metadata METADATA]
                                  [--image-stats] [--out OUT]
                                  dataset
```

## `cvrs distribution embeddings`

```text
usage: cvrs distribution embeddings [-h] --left-descriptor LEFT_DESCRIPTOR
                                    --right-descriptor RIGHT_DESCRIPTOR
                                    [--out OUT]
                                    left right
```

## `cvrs docs`

```text
usage: cvrs docs [-h]
```

## `cvrs docs generate`

```text
usage: cvrs docs generate [-h] --out OUT
```

## `cvrs doctor`

```text
usage: cvrs doctor [-h]
```

## `cvrs domain compare`

```text
usage: cvrs domain compare [-h] [--out OUT] left right
```

## `cvrs domain describe`

```text
usage: cvrs domain describe [-h] [--split SPLIT] [--sidecars SIDECARS]
                            [--out OUT]
                            dataset
```

## `cvrs dota diagnostic`

```text
usage: cvrs dota diagnostic [-h] --dataset DATASET [--iou IOU] [--score SCORE]
                            [--out OUT]
                            predictions
```

## `cvrs dota export`

```text
usage: cvrs dota export [-h] --dataset DATASET --out OUT predictions
```

## `cvrs dota import`

```text
usage: cvrs dota import [-h] --images IMAGES --labels LABELS
                        --categories CATEGORIES --name NAME
                        --dataset-version DATASET_VERSION
                        [--role {train,dev,locked_test}] --out OUT
```

## `cvrs dota reference`

```text
usage: cvrs dota reference [-h] --dataset DATASET --reference REFERENCE
                           --out OUT [--worker-python WORKER_PYTHON]
                           [--timeout TIMEOUT]
                           predictions
```

## `cvrs dota validate`

```text
usage: cvrs dota validate [-h] [--metadata-only] dataset
```

## `cvrs environment`

```text
usage: cvrs environment [-h]
```

## `cvrs environment capsule`

```text
usage: cvrs environment capsule [-h] --out OUT spec
```

## `cvrs environment capture`

```text
usage: cvrs environment capture [-h] [--out OUT] [--probe-hardware]
```

## `cvrs environment import`

```text
usage: cvrs environment import [-h]
                               --kind {pip,uv,conda,conda-explicit,docker}
                               [--out OUT]
                               source
```

## `cvrs evaluate`

```text
usage: cvrs evaluate [-h] [--evaluator-python EVALUATOR_PYTHON]
                     --dataset DATASET [--split SPLIT] --protocol PROTOCOL
                     [--out OUT]
                     predictions
```

## `cvrs experiment`

```text
usage: cvrs experiment [-h] {validate} spec
```

## `cvrs fixtures`

```text
usage: cvrs fixtures [-h] destination
```

## `cvrs geotiff inspect`

```text
usage: cvrs geotiff inspect [-h] source
```

## `cvrs geotiff window`

```text
usage: cvrs geotiff window [-h] --out OUT --window X Y WIDTH HEIGHT
                           --bands BANDS BANDS BANDS
                           --value-range VALUE_RANGE VALUE_RANGE
                           source
```

## `cvrs graph`

```text
usage: cvrs graph [-h]
```

## `cvrs graph actions`

```text
usage: cvrs graph actions [-h]
```

## `cvrs graph plan`

```text
usage: cvrs graph plan [-h] spec
```

## `cvrs graph run`

```text
usage: cvrs graph run [-h] --out OUT [--resume] [--cache CACHE]
                      [--invalidate [INVALIDATE ...]]
                      spec
```

## `cvrs groundwork-fixtures`

```text
usage: cvrs groundwork-fixtures [-h] destination
```

## `cvrs heritage`

```text
usage: cvrs heritage [-h] [--run RUN] [--out OUT] [--tolerance TOLERANCE]
                     {inspect,inspect-config,adapter,certify} reference
```

## `cvrs heritage catalogue add`

```text
usage: cvrs heritage catalogue add [-h] --out OUT catalogue entry
```

## `cvrs heritage catalogue docs`

```text
usage: cvrs heritage catalogue docs [-h] --out OUT catalogue
```

## `cvrs heritage catalogue list`

```text
usage: cvrs heritage catalogue list [-h] catalogue
```

## `cvrs heritage catalogue search`

```text
usage: cvrs heritage catalogue search [-h] catalogue query
```

## `cvrs heritage catalogue validate`

```text
usage: cvrs heritage catalogue validate [-h] catalogue
```

## `cvrs heritage certify-training`

```text
usage: cvrs heritage certify-training [-h] --out OUT spec
```

## `cvrs heritage convert-predictions`

```text
usage: cvrs heritage convert-predictions [-h] --format FORMAT
                                         --mapping MAPPING [--dataset DATASET]
                                         [--split SPLIT]
                                         [--image-id-map IMAGE_ID_MAP]
                                         [--angle-convention ANGLE_CONVENTION]
                                         --out OUT
                                         native
```

## `cvrs heritage graph`

```text
usage: cvrs heritage graph [-h] --source-root SOURCE_ROOT [--out OUT] config
```

## `cvrs heritage import`

```text
usage: cvrs heritage import [-h] --out OUT spec
```

## `cvrs heritage profiles`

```text
usage: cvrs heritage profiles [-h]
```

## `cvrs heritage train-native`

```text
usage: cvrs heritage train-native [-h] --out OUT
                                  [--worker-python WORKER_PYTHON]
                                  [--timeout TIMEOUT]
                                  spec
```

## `cvrs heritage trusted-import`

```text
usage: cvrs heritage trusted-import [-h] --out OUT
                                    [--worker-python WORKER_PYTHON]
                                    [--timeout TIMEOUT]
                                    spec
```

## `cvrs heritage-graph`

```text
usage: cvrs heritage-graph [-h] --source-root SOURCE_ROOT config
```

## `cvrs heritage-import`

```text
usage: cvrs heritage-import [-h] --source-root SOURCE_ROOT --out OUT
                            --upstream UPSTREAM --revision REVISION
                            [--checkpoint CHECKPOINT] [--dataset DATASET]
                            config
```

## `cvrs import-coco`

```text
usage: cvrs import-coco [-h] --image-root IMAGE_ROOT --name NAME
                        [--role {train,dev,selection,locked_test}]
                        [--source {real,synthetic,unknown}] --out OUT
                        annotations
```

## `cvrs import-predictions`

```text
usage: cvrs import-predictions [-h] --dataset DATASET [--split SPLIT]
                               --mapping MAPPING
                               --format {mmdet2_bbox,mmdet3_instances}
                               --out OUT
                               native
```

## `cvrs large`

```text
usage: cvrs large [-h]
```

## `cvrs large merge`

```text
usage: cvrs large merge [-h] --policy POLICY [--out OUT] detections
```

## `cvrs large plan`

```text
usage: cvrs large plan [-h] [--out OUT] spec
```

## `cvrs large run`

```text
usage: cvrs large run [-h] --policy POLICY --out OUT
                      [--worker-python WORKER_PYTHON] [--timeout TIMEOUT]
                      [--evaluator-python EVALUATOR_PYTHON]
                      spec
```

## `cvrs ledger approve`

```text
usage: cvrs ledger approve [-h] --approval APPROVAL ledger
```

## `cvrs ledger final-run`

```text
usage: cvrs ledger final-run [-h] --ledger LEDGER
                             --approval-digest APPROVAL_DIGEST --out OUT
                             [--worker-python WORKER_PYTHON]
                             [--timeout TIMEOUT]
                             spec
```

## `cvrs ledger test-report`

```text
usage: cvrs ledger test-report [-h] ledger
```

## `cvrs ledger verify`

```text
usage: cvrs ledger verify [-h] [--expected-head EXPECTED_HEAD] ledger
```

## `cvrs licenses`

```text
usage: cvrs licenses [-h] --out OUT spec
```

## `cvrs migrate`

```text
usage: cvrs migrate [-h] --out OUT [--schema SCHEMA] source
```

## `cvrs migrate-run`

```text
usage: cvrs migrate-run [-h] --out OUT source
```

## `cvrs model`

```text
usage: cvrs model [-h]
```

## `cvrs model capabilities`

```text
usage: cvrs model capabilities [-h] [--worker-python WORKER_PYTHON]
                               [--timeout TIMEOUT]
                               {ultralytics,rfdetr}
```

## `cvrs model export`

```text
usage: cvrs model export [-h] --out OUT [--worker-python WORKER_PYTHON]
                         [--timeout TIMEOUT]
                         spec
```

## `cvrs model predict`

```text
usage: cvrs model predict [-h] --out OUT [--worker-python WORKER_PYTHON]
                          [--timeout TIMEOUT]
                          spec
```

## `cvrs model predict-obb`

```text
usage: cvrs model predict-obb [-h] --out OUT [--worker-python WORKER_PYTHON]
                              [--timeout TIMEOUT]
                              spec
```

## `cvrs model train-native`

```text
usage: cvrs model train-native [-h] --out OUT [--worker-python WORKER_PYTHON]
                               [--timeout TIMEOUT]
                               spec
```

## `cvrs model train-obb`

```text
usage: cvrs model train-obb [-h] --out OUT [--worker-python WORKER_PYTHON]
                            [--timeout TIMEOUT]
                            spec
```

## `cvrs plugin`

```text
usage: cvrs plugin [-h]
```

## `cvrs plugin conformance`

```text
usage: cvrs plugin conformance [-h] [--trust-code]
                               [--worker-python WORKER_PYTHON]
                               [--timeout TIMEOUT] --fixtures FIXTURES
                               --out OUT
                               descriptor
```

## `cvrs plugin inspect`

```text
usage: cvrs plugin inspect [-h] --registry REGISTRY name
```

## `cvrs plugin list`

```text
usage: cvrs plugin list [-h] --registry REGISTRY
```

## `cvrs plugin negotiate`

```text
usage: cvrs plugin negotiate [-h] spec
```

## `cvrs plugin register`

```text
usage: cvrs plugin register [-h] --registry REGISTRY descriptor
```

## `cvrs plugin run`

```text
usage: cvrs plugin run [-h] [--trust-code] [--worker-python WORKER_PYTHON]
                       [--timeout TIMEOUT] --operation OPERATION
                       --payload PAYLOAD --out OUT
                       descriptor
```

## `cvrs plugin scaffold`

```text
usage: cvrs plugin scaffold [-h] [--kind KIND] --out OUT name
```

## `cvrs plugin validate`

```text
usage: cvrs plugin validate [-h] [--trust-code]
                            [--worker-python WORKER_PYTHON]
                            [--timeout TIMEOUT]
                            descriptor
```

## `cvrs protocol`

```text
usage: cvrs protocol [-h] [--out OUT] {plan} spec
```

## `cvrs recover`

```text
usage: cvrs recover [-h] --reason REASON [--acknowledge-process-stopped] run
```

## `cvrs reference-parity`

```text
usage: cvrs reference-parity [-h] --dataset DATASET [--split SPLIT]
                             --protocol PROTOCOL [--tolerance TOLERANCE]
                             [--out OUT]
                             predictions
```

## `cvrs release`

```text
usage: cvrs release [-h]
```

## `cvrs release build`

```text
usage: cvrs release build [-h] --out OUT [--wheel] root
```

## `cvrs release counts`

```text
usage: cvrs release counts [-h] [--out OUT] root
```

## `cvrs release prepare`

```text
usage: cvrs release prepare [-h] --out OUT --version VERSION --note NOTE root
```

## `cvrs release sbom`

```text
usage: cvrs release sbom [-h] [--out OUT] root
```

## `cvrs release verify`

```text
usage: cvrs release verify [-h] [--out OUT] root
```

## `cvrs report`

```text
usage: cvrs report [-h] run
```

## `cvrs report create`

```text
usage: cvrs report create [-h] [--title TITLE] [--limitation LIMITATION]
                          --out OUT
                          kind records [records ...]
```

## `cvrs research-fixtures`

```text
usage: cvrs research-fixtures [-h] destination
```

## `cvrs run`

```text
usage: cvrs run [-h] [--out OUT] [--worker-python WORKER_PYTHON]
                [--timeout TIMEOUT] [--authorization AUTHORIZATION]
                [--evaluator-python EVALUATOR_PYTHON]
                spec
```

## `cvrs run-tiled`

```text
usage: cvrs run-tiled [-h] --policy POLICY --out OUT
                      [--worker-python WORKER_PYTHON] [--timeout TIMEOUT]
                      spec
```

## `cvrs schema`

```text
usage: cvrs schema [-h]
```

## `cvrs schema export`

```text
usage: cvrs schema export [-h] --out OUT
```

## `cvrs schema inspect`

```text
usage: cvrs schema inspect [-h] name
```

## `cvrs schema list`

```text
usage: cvrs schema list [-h]
```

## `cvrs schema validate`

```text
usage: cvrs schema validate [-h] [--schema SCHEMA] artifact
```

## `cvrs schemas`

```text
usage: cvrs schemas [-h] destination
```

## `cvrs size-evaluate`

```text
usage: cvrs size-evaluate [-h] --dataset DATASET --policy POLICY
                          [--split SPLIT] [--iou IOU] [--threshold THRESHOLD]
                          [--gsd GSD] [--out OUT]
                          predictions
```

## `cvrs slice`

```text
usage: cvrs slice [-h]
```

## `cvrs slice select`

```text
usage: cvrs slice select [-h] [--split SPLIT] --policy POLICY
                         [--metadata METADATA] [--out OUT]
                         dataset
```

## `cvrs synthetic ingest`

```text
usage: cvrs synthetic ingest [-h] --mapping MAPPING --out OUT source
```

## `cvrs synthetic map`

```text
usage: cvrs synthetic map [-h] --mapping MAPPING --out OUT source
```

## `cvrs synthetic migrate`

```text
usage: cvrs synthetic migrate [-h] --sample-id SAMPLE_ID --out OUT source
```

## `cvrs synthetic validate`

```text
usage: cvrs synthetic validate [-h] record
```

## `cvrs synthetic validate-sample`

```text
usage: cvrs synthetic validate-sample [-h] source
```

## `cvrs tiny-evaluate`

```text
usage: cvrs tiny-evaluate [-h] --dataset DATASET [--split SPLIT]
                          [--policy POLICY] [--out OUT]
                          predictions
```

## `cvrs verify`

```text
usage: cvrs verify [-h] [--dataset DATASET] run
```

