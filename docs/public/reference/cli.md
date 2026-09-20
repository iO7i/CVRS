# Command reference

Generated from parser declarations. Commands never execute during documentation generation.

## cvrs

```text
usage: cvrs [-h]
            {env,stack,paper,recipe,research,exchange,site,docs,release,adapter} ...

Managed environments, guided adoption and owner-controlled release preparation

positional arguments:
  {env,stack,paper,recipe,research,exchange,site,docs,release,adapter}

options:
  -h, --help            show this help message and exit
```

## cvrs adapter

```text
usage: cvrs adapter [-h] {badge,receipt} ...

positional arguments:
  {badge,receipt}

options:
  -h, --help       show this help message and exit
```

## cvrs adapter badge

```text
usage: cvrs adapter badge [-h] [--out OUT] [--store STORE] [--spec SPEC]
                          [--plan PLAN] [--python PYTHON]
                          [--environment ENVIRONMENT] [--pack PACK]
                          [--operation OPERATION] [--actor ACTOR]
                          [--approval APPROVAL] [--approve APPROVE]
                          [--replacement REPLACEMENT]
                          [--worker-python WORKER_PYTHON] [--format FORMAT]
                          [--field FIELD] [--repository REPOSITORY]
                          [--version VERSION] [--previous PREVIOUS]
                          [--status STATUS] [--task TASK] [--subject SUBJECT]
                          [--evidence EVIDENCE] [--reason REASON]
                          [--files [FILES ...]] [--trust] [--verify] [--apply]
                          [--preview] [--force]
                          [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs adapter check

```text
usage: cvrs adapter check [-h] descriptor

positional arguments:
  descriptor

options:
  -h, --help  show this help message and exit
```

## cvrs adapter new

```text
usage: cvrs adapter new [-h] --out OUT [--native-vision] name

positional arguments:
  name

options:
  -h, --help       show this help message and exit
  --out OUT
  --native-vision
```

## cvrs adapter receipt

```text
usage: cvrs adapter receipt [-h] [--out OUT] [--store STORE] [--spec SPEC]
                            [--plan PLAN] [--python PYTHON]
                            [--environment ENVIRONMENT] [--pack PACK]
                            [--operation OPERATION] [--actor ACTOR]
                            [--approval APPROVAL] [--approve APPROVE]
                            [--replacement REPLACEMENT]
                            [--worker-python WORKER_PYTHON] [--format FORMAT]
                            [--field FIELD] [--repository REPOSITORY]
                            [--version VERSION] [--previous PREVIOUS]
                            [--status STATUS] [--task TASK]
                            [--subject SUBJECT] [--evidence EVIDENCE]
                            [--reason REASON] [--files [FILES ...]] [--trust]
                            [--verify] [--apply] [--preview] [--force]
                            [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs adapter-recipes

```text
usage: cvrs adapter-recipes [-h] {list,show,scaffold} ...

positional arguments:
  {list,show,scaffold}

options:
  -h, --help            show this help message and exit
```

## cvrs adapter-recipes list

```text
usage: cvrs adapter-recipes list [-h]

options:
  -h, --help  show this help message and exit
```

## cvrs adapter-recipes scaffold

```text
usage: cvrs adapter-recipes scaffold [-h] out

positional arguments:
  out

options:
  -h, --help  show this help message and exit
```

## cvrs adapter-recipes show

```text
usage: cvrs adapter-recipes show [-h] name

positional arguments:
  name

options:
  -h, --help  show this help message and exit
```

## cvrs artifact

```text
usage: cvrs artifact [-h] {put,get,verify,exists} ...

positional arguments:
  {put,get,verify,exists}

options:
  -h, --help            show this help message and exit
```

## cvrs artifact exists

```text
usage: cvrs artifact exists [-h] --store STORE sha256

positional arguments:
  sha256

options:
  -h, --help     show this help message and exit
  --store STORE
```

## cvrs artifact get

```text
usage: cvrs artifact get [-h] --store STORE --out OUT sha256

positional arguments:
  sha256

options:
  -h, --help     show this help message and exit
  --store STORE
  --out OUT
```

## cvrs artifact put

```text
usage: cvrs artifact put [-h] --store STORE source

positional arguments:
  source

options:
  -h, --help     show this help message and exit
  --store STORE
```

## cvrs artifact verify

```text
usage: cvrs artifact verify [-h] --store STORE sha256

positional arguments:
  sha256

options:
  -h, --help     show this help message and exit
  --store STORE
```

## cvrs artifact-verify

```text
usage: cvrs artifact-verify [-h] directory

positional arguments:
  directory

options:
  -h, --help  show this help message and exit
```

## cvrs assets

```text
usage: cvrs assets [-h] {status,acknowledge,fetch,prune} ...

positional arguments:
  {status,acknowledge,fetch,prune}

options:
  -h, --help            show this help message and exit
```

## cvrs assets acknowledge

```text
usage: cvrs assets acknowledge [-h] --cache CACHE --actor ACTOR
                               --purpose PURPOSE
                               descriptor

positional arguments:
  descriptor

options:
  -h, --help         show this help message and exit
  --cache CACHE
  --actor ACTOR
  --purpose PURPOSE
```

## cvrs assets fetch

```text
usage: cvrs assets fetch [-h] --cache CACHE [--allow-network]
                         [--max-bytes MAX_BYTES]
                         descriptor

positional arguments:
  descriptor

options:
  -h, --help            show this help message and exit
  --cache CACHE
  --allow-network
  --max-bytes MAX_BYTES
```

## cvrs assets prune

```text
usage: cvrs assets prune [-h] --cache CACHE [--keep [KEEP ...]] [--apply]

options:
  -h, --help         show this help message and exit
  --cache CACHE
  --keep [KEEP ...]
  --apply
```

## cvrs assets status

```text
usage: cvrs assets status [-h] --cache CACHE descriptor

positional arguments:
  descriptor

options:
  -h, --help     show this help message and exit
  --cache CACHE
```

## cvrs audit-predictions

```text
usage: cvrs audit-predictions [-h] [--box-atol BOX_ATOL]
                              [--score-atol SCORE_ATOL]
                              [--order {as_emitted,canonical_sort}]
                              [--out OUT]
                              left right

positional arguments:
  left
  right

options:
  -h, --help            show this help message and exit
  --box-atol BOX_ATOL
  --score-atol SCORE_ATOL
  --order {as_emitted,canonical_sort}
  --out OUT
```

## cvrs backbone

```text
usage: cvrs backbone [-h] {extract} ...

positional arguments:
  {extract}

options:
  -h, --help  show this help message and exit
```

## cvrs backbone extract

```text
usage: cvrs backbone extract [-h] --out OUT [--worker-python WORKER_PYTHON]
                             [--timeout TIMEOUT]
                             spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
```

## cvrs benchmark

```text
usage: cvrs benchmark [-h]
                      {register,list,preregister,authorize-final,final-eval,access-log,submission-check,orchestrate} ...

positional arguments:
  {register,list,preregister,authorize-final,final-eval,access-log,submission-check,orchestrate}

options:
  -h, --help            show this help message and exit
```

## cvrs benchmark access-log

```text
usage: cvrs benchmark access-log [-h] ledger

positional arguments:
  ledger

options:
  -h, --help  show this help message and exit
```

## cvrs benchmark authorize-final

```text
usage: cvrs benchmark authorize-final [-h] --ledger LEDGER [--out OUT] spec

positional arguments:
  spec

options:
  -h, --help       show this help message and exit
  --ledger LEDGER
  --out OUT
```

## cvrs benchmark final-eval

```text
usage: cvrs benchmark final-eval [-h] --ledger LEDGER
                                 --approval-digest APPROVAL_DIGEST --out OUT
                                 [--worker-python WORKER_PYTHON]
                                 [--timeout TIMEOUT]
                                 [--evaluator-python EVALUATOR_PYTHON]
                                 benchmark experiment

positional arguments:
  benchmark
  experiment

options:
  -h, --help            show this help message and exit
  --ledger LEDGER
  --approval-digest APPROVAL_DIGEST
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
  --evaluator-python EVALUATOR_PYTHON
```

## cvrs benchmark list

```text
usage: cvrs benchmark list [-h] --registry REGISTRY

options:
  -h, --help           show this help message and exit
  --registry REGISTRY
```

## cvrs benchmark orchestrate

```text
usage: cvrs benchmark orchestrate [-h] --out OUT
                                  [--worker-python WORKER_PYTHON]
                                  [--timeout TIMEOUT] [--resume]
                                  [--retry-failed]
                                  spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
  --resume
  --retry-failed
```

## cvrs benchmark preregister

```text
usage: cvrs benchmark preregister [-h] --ledger LEDGER [--out OUT] spec

positional arguments:
  spec

options:
  -h, --help       show this help message and exit
  --ledger LEDGER
  --out OUT
```

## cvrs benchmark register

```text
usage: cvrs benchmark register [-h] --registry REGISTRY spec

positional arguments:
  spec

options:
  -h, --help           show this help message and exit
  --registry REGISTRY
```

## cvrs benchmark submission-check

```text
usage: cvrs benchmark submission-check [-h] [--out OUT] benchmark run

positional arguments:
  benchmark
  run

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs bridge

```text
usage: cvrs bridge [-h]
                   {list,run,bundle-detections,codeocean,benchmark,reproduce,simulator,semantic-evaluate,tracking} ...

positional arguments:
  {list,run,bundle-detections,codeocean,benchmark,reproduce,simulator,semantic-evaluate,tracking}

options:
  -h, --help            show this help message and exit
```

## cvrs bridge benchmark

```text
usage: cvrs bridge benchmark [-h] --out OUT spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs bridge bundle-detections

```text
usage: cvrs bridge bundle-detections [-h] --image-root IMAGE_ROOT --out OUT
                                     dataset predictions

positional arguments:
  dataset
  predictions

options:
  -h, --help            show this help message and exit
  --image-root IMAGE_ROOT
  --out OUT
```

## cvrs bridge codeocean

```text
usage: cvrs bridge codeocean [-h] --argv ARGV [--environment ENVIRONMENT]
                             --out OUT
                             capsule

positional arguments:
  capsule

options:
  -h, --help            show this help message and exit
  --argv ARGV           JSON list, not a shell command
  --environment ENVIRONMENT
  --out OUT
```

## cvrs bridge list

```text
usage: cvrs bridge list [-h]

options:
  -h, --help  show this help message and exit
```

## cvrs bridge reproduce

```text
usage: cvrs bridge reproduce [-h] --out OUT run

positional arguments:
  run

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs bridge run

```text
usage: cvrs bridge run [-h] [--trust] [--allow-network] job

positional arguments:
  job

options:
  -h, --help       show this help message and exit
  --trust
  --allow-network
```

## cvrs bridge semantic-evaluate

```text
usage: cvrs bridge semantic-evaluate [-h] --classes CLASSES
                                     [--ignore-index IGNORE_INDEX]
                                     [--reduce-zero-label] --out OUT
                                     pairs

positional arguments:
  pairs

options:
  -h, --help            show this help message and exit
  --classes CLASSES
  --ignore-index IGNORE_INDEX
  --reduce-zero-label
  --out OUT
```

## cvrs bridge simulator

```text
usage: cvrs bridge simulator [-h] [--mapping MAPPING] --out OUT kind source

positional arguments:
  kind
  source

options:
  -h, --help         show this help message and exit
  --mapping MAPPING
  --out OUT
```

## cvrs bridge tracking

```text
usage: cvrs bridge tracking [-h] [--target {wandb,mlflow}] [--project PROJECT]
                            --out OUT
                            run

positional arguments:
  run

options:
  -h, --help            show this help message and exit
  --target {wandb,mlflow}
  --project PROJECT
  --out OUT
```

## cvrs cache

```text
usage: cvrs cache [-h] {put,get,verify,exists} ...

positional arguments:
  {put,get,verify,exists}

options:
  -h, --help            show this help message and exit
```

## cvrs cache exists

```text
usage: cvrs cache exists [-h] --store STORE sha256

positional arguments:
  sha256

options:
  -h, --help     show this help message and exit
  --store STORE
```

## cvrs cache get

```text
usage: cvrs cache get [-h] --store STORE --out OUT sha256

positional arguments:
  sha256

options:
  -h, --help     show this help message and exit
  --store STORE
  --out OUT
```

## cvrs cache put

```text
usage: cvrs cache put [-h] --store STORE source

positional arguments:
  source

options:
  -h, --help     show this help message and exit
  --store STORE
```

## cvrs cache verify

```text
usage: cvrs cache verify [-h] --store STORE sha256

positional arguments:
  sha256

options:
  -h, --help     show this help message and exit
  --store STORE
```

## cvrs campaign

```text
usage: cvrs campaign [-h] {compile,budgets,run-stages,sweep} ...

positional arguments:
  {compile,budgets,run-stages,sweep}

options:
  -h, --help            show this help message and exit
```

## cvrs campaign budgets

```text
usage: cvrs campaign budgets [-h] [--out OUT] spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs campaign compile

```text
usage: cvrs campaign compile [-h] [--out OUT] spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs campaign plan

```text
usage: cvrs campaign plan [-h] [--out OUT] spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs campaign report

```text
usage: cvrs campaign report [-h] [--out OUT] campaign

positional arguments:
  campaign

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs campaign run

```text
usage: cvrs campaign run [-h] --out OUT [--resume] [--retry-failed]
                         [--worker-python WORKER_PYTHON]
                         spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --resume
  --retry-failed
  --worker-python WORKER_PYTHON
```

## cvrs campaign run-stages

```text
usage: cvrs campaign run-stages [-h] --out OUT [--worker-python WORKER_PYTHON]
                                [--timeout TIMEOUT] [--resume]
                                [--retry-failed]
                                spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
  --resume
  --retry-failed
```

## cvrs campaign sweep

```text
usage: cvrs campaign sweep [-h] --axes AXES --out OUT [--max-cases MAX_CASES]
                           spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --axes AXES
  --out OUT
  --max-cases MAX_CASES
```

## cvrs capabilities

```text
usage: cvrs capabilities [-h]
                         [--adapter {native_torch,mmdetection,ultralytics,rfdetr}]
                         [--worker-python WORKER_PYTHON]

options:
  -h, --help            show this help message and exit
  --adapter {native_torch,mmdetection,ultralytics,rfdetr}
  --worker-python WORKER_PYTHON
```

## cvrs capsule

```text
usage: cvrs capsule [-h] {create,validate,inspect,archive,materialize} ...

positional arguments:
  {create,validate,inspect,archive,materialize}

options:
  -h, --help            show this help message and exit
```

## cvrs capsule archive

```text
usage: cvrs capsule archive [-h] --out OUT source

positional arguments:
  source

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs capsule create

```text
usage: cvrs capsule create [-h] --out OUT [--references REFERENCES]
                           [--dependencies DEPENDENCIES]
                           [--include [INCLUDE ...]]
                           source

positional arguments:
  source

options:
  -h, --help            show this help message and exit
  --out OUT
  --references REFERENCES
  --dependencies DEPENDENCIES
  --include [INCLUDE ...]
```

## cvrs capsule inspect

```text
usage: cvrs capsule inspect [-h] source

positional arguments:
  source

options:
  -h, --help  show this help message and exit
```

## cvrs capsule materialize

```text
usage: cvrs capsule materialize [-h] --out OUT source

positional arguments:
  source

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs capsule validate

```text
usage: cvrs capsule validate [-h] source

positional arguments:
  source

options:
  -h, --help  show this help message and exit
```

## cvrs catalogue

```text
usage: cvrs catalogue [-h] [--source-root SOURCE_ROOT] catalogue

positional arguments:
  catalogue

options:
  -h, --help            show this help message and exit
  --source-root SOURCE_ROOT
```

## cvrs checkpoint

```text
usage: cvrs checkpoint [-h] {inspect,convert} ...

positional arguments:
  {inspect,convert}

options:
  -h, --help         show this help message and exit
```

## cvrs checkpoint convert

```text
usage: cvrs checkpoint convert [-h] [--worker-python WORKER_PYTHON]
                               [--timeout TIMEOUT] --out OUT
                               spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
  --out OUT
```

## cvrs checkpoint inspect

```text
usage: cvrs checkpoint inspect [-h] [--worker-python WORKER_PYTHON]
                               [--timeout TIMEOUT] [--out OUT]
                               spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
  --out OUT
```

## cvrs closure

```text
usage: cvrs closure [-h]
                    {policy,compatibility,identity,dependencies,gc,config,model-index,checkpoint,telemetry,environment-diff,lineage,slice,assets,native-campaign,stream,prompts,authorize-evaluation,reevaluate,compare,keygen,registry,capture-comparison} ...

positional arguments:
  {policy,compatibility,identity,dependencies,gc,config,model-index,checkpoint,telemetry,environment-diff,lineage,slice,assets,native-campaign,stream,prompts,authorize-evaluation,reevaluate,compare,keygen,registry,capture-comparison}

options:
  -h, --help            show this help message and exit
```

## cvrs closure assets

```text
usage: cvrs closure assets [-h] --root ROOT spec

positional arguments:
  spec

options:
  -h, --help   show this help message and exit
  --root ROOT
```

## cvrs closure authorize-evaluation

```text
usage: cvrs closure authorize-evaluation [-h] --ledger LEDGER
                                         --approved-by APPROVED_BY
                                         --reason REASON [--max-uses MAX_USES]
                                         spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --ledger LEDGER
  --approved-by APPROVED_BY
  --reason REASON
  --max-uses MAX_USES
```

## cvrs closure capture-comparison

```text
usage: cvrs closure capture-comparison [-h] --registry REGISTRY spec

positional arguments:
  spec

options:
  -h, --help           show this help message and exit
  --registry REGISTRY
```

## cvrs closure checkpoint

```text
usage: cvrs closure checkpoint [-h] [--out OUT]
                               [--worker-python WORKER_PYTHON]
                               {diff,transform} left right

positional arguments:
  {diff,transform}
  left
  right

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
```

## cvrs closure compare

```text
usage: cvrs closure compare [-h] left right

positional arguments:
  left
  right

options:
  -h, --help  show this help message and exit
```

## cvrs closure compatibility

```text
usage: cvrs closure compatibility [-h] --root ROOT manifest

positional arguments:
  manifest

options:
  -h, --help   show this help message and exit
  --root ROOT
```

## cvrs closure config

```text
usage: cvrs closure config [-h] --root ROOT [--out OUT]
                           [--environment ENVIRONMENT]
                           config

positional arguments:
  config

options:
  -h, --help            show this help message and exit
  --root ROOT
  --out OUT
  --environment ENVIRONMENT
```

## cvrs closure dependencies

```text
usage: cvrs closure dependencies [-h] [--root ROOT] [--bindings BINDINGS] spec

positional arguments:
  spec

options:
  -h, --help           show this help message and exit
  --root ROOT
  --bindings BINDINGS
```

## cvrs closure environment-diff

```text
usage: cvrs closure environment-diff [-h] recipe observation

positional arguments:
  recipe
  observation

options:
  -h, --help   show this help message and exit
```

## cvrs closure gc

```text
usage: cvrs closure gc [-h] [--age AGE] [--apply-plan APPLY_PLAN] [--pin PIN]
                       [--hashes [HASHES ...]] [--unpin UNPIN]
                       store

positional arguments:
  store

options:
  -h, --help            show this help message and exit
  --age AGE
  --apply-plan APPLY_PLAN
  --pin PIN
  --hashes [HASHES ...]
  --unpin UNPIN
```

## cvrs closure identity

```text
usage: cvrs closure identity [-h] kind artifact

positional arguments:
  kind
  artifact

options:
  -h, --help  show this help message and exit
```

## cvrs closure keygen

```text
usage: cvrs closure keygen [-h] [--unencrypted] destination

positional arguments:
  destination

options:
  -h, --help     show this help message and exit
  --unencrypted
```

## cvrs closure lineage

```text
usage: cvrs closure lineage [-h] spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
```

## cvrs closure model-index

```text
usage: cvrs closure model-index [-h] --root ROOT index

positional arguments:
  index

options:
  -h, --help   show this help message and exit
  --root ROOT
```

## cvrs closure native-campaign

```text
usage: cvrs closure native-campaign [-h] [--out OUT] [--workers WORKERS]
                                    [--resume] [--timeout TIMEOUT]
                                    {plan,run} spec

positional arguments:
  {plan,run}
  spec

options:
  -h, --help         show this help message and exit
  --out OUT
  --workers WORKERS
  --resume
  --timeout TIMEOUT
```

## cvrs closure policy

```text
usage: cvrs closure policy [-h]

options:
  -h, --help  show this help message and exit
```

## cvrs closure prompts

```text
usage: cvrs closure prompts [-h] [--backend BACKEND] [--out OUT]
                            [--worker-python WORKER_PYTHON]
                            {negotiate,trajectory,continue} spec

positional arguments:
  {negotiate,trajectory,continue}
  spec

options:
  -h, --help            show this help message and exit
  --backend BACKEND
  --out OUT
  --worker-python WORKER_PYTHON
```

## cvrs closure reevaluate

```text
usage: cvrs closure reevaluate [-h] --out OUT [--worker-python WORKER_PYTHON]
                               spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
```

## cvrs closure registry

```text
usage: cvrs closure registry [-h] [--kind KIND] [--input INPUT] [--id ID]
                             [--out OUT] [--key KEY]
                             [--trusted-key TRUSTED_KEY] [--require-signature]
                             [--key-password-env KEY_PASSWORD_ENV]
                             [--minimum-level MINIMUM_LEVEL]
                             [--filters FILTERS]
                             {add,edge,status,query,verify,export,merge,site,sign,migrate}
                             root

positional arguments:
  {add,edge,status,query,verify,export,merge,site,sign,migrate}
  root

options:
  -h, --help            show this help message and exit
  --kind KIND
  --input INPUT
  --id ID
  --out OUT
  --key KEY
  --trusted-key TRUSTED_KEY
  --require-signature
  --key-password-env KEY_PASSWORD_ENV
  --minimum-level MINIMUM_LEVEL
  --filters FILTERS
```

## cvrs closure slice

```text
usage: cvrs closure slice [-h] records predicate

positional arguments:
  records
  predicate

options:
  -h, --help  show this help message and exit
```

## cvrs closure stream

```text
usage: cvrs closure stream [-h] --out OUT [--worker-python WORKER_PYTHON]
                           [--resume] [--max-tiles MAX_TILES]
                           [--timeout TIMEOUT]
                           spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
  --resume
  --max-tiles MAX_TILES
  --timeout TIMEOUT
```

## cvrs closure telemetry

```text
usage: cvrs closure telemetry [-h] --world-size WORLD_SIZE files [files ...]

positional arguments:
  files

options:
  -h, --help            show this help message and exit
  --world-size WORLD_SIZE
```

## cvrs compare

```text
usage: cvrs compare [-h] left right

positional arguments:
  left
  right

options:
  -h, --help  show this help message and exit
```

## cvrs composition

```text
usage: cvrs composition [-h] {plan,run} ...

positional arguments:
  {plan,run}

options:
  -h, --help  show this help message and exit
```

## cvrs composition plan

```text
usage: cvrs composition plan [-h] spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
```

## cvrs composition run

```text
usage: cvrs composition run [-h] --out OUT [--trust] spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
  --out OUT
  --trust
```

## cvrs cross-compare

```text
usage: cvrs cross-compare [-h] [--out OUT] left right

positional arguments:
  left
  right

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs dataset

```text
usage: cvrs dataset [-h]
                    {import,materialize,inspect-geo,geo-manifest,export-world} ...

positional arguments:
  {import,materialize,inspect-geo,geo-manifest,export-world}

options:
  -h, --help            show this help message and exit
```

## cvrs dataset export-world

```text
usage: cvrs dataset export-world [-h] --georeferences GEOREFERENCES
                                 [--format {geojson,json,csv}] --out OUT
                                 predictions

positional arguments:
  predictions

options:
  -h, --help            show this help message and exit
  --georeferences GEOREFERENCES
  --format {geojson,json,csv}
  --out OUT
```

## cvrs dataset geo-manifest

```text
usage: cvrs dataset geo-manifest [-h] --out OUT spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs dataset import

```text
usage: cvrs dataset import [-h] --out OUT spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs dataset inspect-geo

```text
usage: cvrs dataset inspect-geo [-h] [--sidecar SIDECAR] [--out OUT] source

positional arguments:
  source

options:
  -h, --help         show this help message and exit
  --sidecar SIDECAR
  --out OUT
```

## cvrs dataset materialize

```text
usage: cvrs dataset materialize [-h] --image-root IMAGE_ROOT --out OUT
                                [--mode {copy,hardlink}]
                                manifest

positional arguments:
  manifest

options:
  -h, --help            show this help message and exit
  --image-root IMAGE_ROOT
  --out OUT
  --mode {copy,hardlink}
```

## cvrs demo

```text
usage: cvrs demo [-h] [--worker-python WORKER_PYTHON] [--timeout TIMEOUT]
                 destination

positional arguments:
  destination

options:
  -h, --help            show this help message and exit
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
```

## cvrs demo-all

```text
usage: cvrs demo-all [-h] [--python PYTHON] [--timeout TIMEOUT] destination

positional arguments:
  destination

options:
  -h, --help         show this help message and exit
  --python PYTHON
  --timeout TIMEOUT
```

## cvrs deploy

```text
usage: cvrs deploy [-h]
                   {export,infer,compare-arrays,compare-detections,compare-metrics,decode} ...

positional arguments:
  {export,infer,compare-arrays,compare-detections,compare-metrics,decode}

options:
  -h, --help            show this help message and exit
```

## cvrs deploy compare-arrays

```text
usage: cvrs deploy compare-arrays [-h] [--out OUT] [--atol ATOL] [--rtol RTOL]
                                  [--names NAMES]
                                  left right

positional arguments:
  left
  right

options:
  -h, --help     show this help message and exit
  --out OUT
  --atol ATOL
  --rtol RTOL
  --names NAMES
```

## cvrs deploy compare-detections

```text
usage: cvrs deploy compare-detections [-h] [--out OUT] left right

positional arguments:
  left
  right

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs deploy compare-metrics

```text
usage: cvrs deploy compare-metrics [-h] [--out OUT] left right

positional arguments:
  left
  right

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs deploy decode

```text
usage: cvrs deploy decode [-h] --out OUT run spec

positional arguments:
  run
  spec

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs deploy export

```text
usage: cvrs deploy export [-h] --out OUT [--worker-python WORKER_PYTHON]
                          [--timeout TIMEOUT]
                          spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
```

## cvrs deploy infer

```text
usage: cvrs deploy infer [-h] --out OUT [--worker-python WORKER_PYTHON]
                         [--timeout TIMEOUT]
                         spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
```

## cvrs detector-deploy

```text
usage: cvrs detector-deploy [-h] {profile,infer,export-mm} ...

positional arguments:
  {profile,infer,export-mm}

options:
  -h, --help            show this help message and exit
```

## cvrs detector-deploy export-mm

```text
usage: cvrs detector-deploy export-mm [-h] --out OUT
                                      [--worker-python WORKER_PYTHON]
                                      [--timeout TIMEOUT]
                                      spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
```

## cvrs detector-deploy infer

```text
usage: cvrs detector-deploy infer [-h] --out OUT
                                  [--worker-python WORKER_PYTHON]
                                  [--timeout TIMEOUT]
                                  spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
```

## cvrs detector-deploy profile

```text
usage: cvrs detector-deploy profile [-h] spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
```

## cvrs diff

```text
usage: cvrs diff [-h] [--out OUT] left right

positional arguments:
  left
  right

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs distribution

```text
usage: cvrs distribution [-h] {describe,compare,embeddings} ...

positional arguments:
  {describe,compare,embeddings}

options:
  -h, --help            show this help message and exit
```

## cvrs distribution compare

```text
usage: cvrs distribution compare [-h] [--out OUT] left right

positional arguments:
  left
  right

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs distribution describe

```text
usage: cvrs distribution describe [-h] [--split SPLIT] [--metadata METADATA]
                                  [--image-stats] [--out OUT]
                                  dataset

positional arguments:
  dataset

options:
  -h, --help           show this help message and exit
  --split SPLIT
  --metadata METADATA
  --image-stats
  --out OUT
```

## cvrs distribution embeddings

```text
usage: cvrs distribution embeddings [-h] --left-descriptor LEFT_DESCRIPTOR
                                    --right-descriptor RIGHT_DESCRIPTOR
                                    [--out OUT]
                                    left right

positional arguments:
  left
  right

options:
  -h, --help            show this help message and exit
  --left-descriptor LEFT_DESCRIPTOR
  --right-descriptor RIGHT_DESCRIPTOR
  --out OUT
```

## cvrs docs

```text
usage: cvrs docs [-h] {portal,version-site} ...

positional arguments:
  {portal,version-site}

options:
  -h, --help            show this help message and exit
```

## cvrs docs build

```text
usage: cvrs docs build [-h] --out OUT root

positional arguments:
  root

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs docs generate

```text
usage: cvrs docs generate [-h] --out OUT

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs docs link-check

```text
usage: cvrs docs link-check [-h] site

positional arguments:
  site

options:
  -h, --help  show this help message and exit
```

## cvrs docs portal

```text
usage: cvrs docs portal [-h] [--out OUT] [--store STORE] [--spec SPEC]
                        [--plan PLAN] [--python PYTHON]
                        [--environment ENVIRONMENT] [--pack PACK]
                        [--operation OPERATION] [--actor ACTOR]
                        [--approval APPROVAL] [--approve APPROVE]
                        [--replacement REPLACEMENT]
                        [--worker-python WORKER_PYTHON] [--format FORMAT]
                        [--field FIELD] [--repository REPOSITORY]
                        [--version VERSION] [--previous PREVIOUS]
                        [--status STATUS] [--task TASK] [--subject SUBJECT]
                        [--evidence EVIDENCE] [--reason REASON]
                        [--files [FILES ...]] [--trust] [--verify] [--apply]
                        [--preview] [--force]
                        [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs docs serve

```text
usage: cvrs docs serve [-h] [--port PORT] site

positional arguments:
  site

options:
  -h, --help   show this help message and exit
  --port PORT
```

## cvrs docs version-site

```text
usage: cvrs docs version-site [-h] [--out OUT] [--store STORE] [--spec SPEC]
                              [--plan PLAN] [--python PYTHON]
                              [--environment ENVIRONMENT] [--pack PACK]
                              [--operation OPERATION] [--actor ACTOR]
                              [--approval APPROVAL] [--approve APPROVE]
                              [--replacement REPLACEMENT]
                              [--worker-python WORKER_PYTHON]
                              [--format FORMAT] [--field FIELD]
                              [--repository REPOSITORY] [--version VERSION]
                              [--previous PREVIOUS] [--status STATUS]
                              [--task TASK] [--subject SUBJECT]
                              [--evidence EVIDENCE] [--reason REASON]
                              [--files [FILES ...]] [--trust] [--verify]
                              [--apply] [--preview] [--force]
                              [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs doctor

```text
usage: cvrs doctor [-h] [--python PYTHON]

options:
  -h, --help       show this help message and exit
  --python PYTHON
```

## cvrs domain

```text
usage: cvrs domain [-h] {describe,compare} ...

positional arguments:
  {describe,compare}

options:
  -h, --help          show this help message and exit
```

## cvrs domain compare

```text
usage: cvrs domain compare [-h] [--out OUT] left right

positional arguments:
  left
  right

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs domain describe

```text
usage: cvrs domain describe [-h] [--split SPLIT] [--sidecars SIDECARS]
                            [--out OUT]
                            dataset

positional arguments:
  dataset

options:
  -h, --help           show this help message and exit
  --split SPLIT
  --sidecars SIDECARS
  --out OUT
```

## cvrs dota

```text
usage: cvrs dota [-h] {import,validate,export,diagnostic,reference} ...

positional arguments:
  {import,validate,export,diagnostic,reference}

options:
  -h, --help            show this help message and exit
```

## cvrs dota diagnostic

```text
usage: cvrs dota diagnostic [-h] --dataset DATASET [--iou IOU] [--score SCORE]
                            [--out OUT]
                            predictions

positional arguments:
  predictions

options:
  -h, --help         show this help message and exit
  --dataset DATASET
  --iou IOU
  --score SCORE
  --out OUT
```

## cvrs dota export

```text
usage: cvrs dota export [-h] --dataset DATASET --out OUT predictions

positional arguments:
  predictions

options:
  -h, --help         show this help message and exit
  --dataset DATASET
  --out OUT
```

## cvrs dota import

```text
usage: cvrs dota import [-h] --images IMAGES --labels LABELS
                        --categories CATEGORIES --name NAME
                        --dataset-version DATASET_VERSION
                        [--role {train,dev,locked_test}] --out OUT

options:
  -h, --help            show this help message and exit
  --images IMAGES
  --labels LABELS
  --categories CATEGORIES
  --name NAME
  --dataset-version DATASET_VERSION
  --role {train,dev,locked_test}
  --out OUT
```

## cvrs dota reference

```text
usage: cvrs dota reference [-h] --dataset DATASET --reference REFERENCE
                           --out OUT [--worker-python WORKER_PYTHON]
                           [--timeout TIMEOUT]
                           predictions

positional arguments:
  predictions

options:
  -h, --help            show this help message and exit
  --dataset DATASET
  --reference REFERENCE
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
```

## cvrs dota validate

```text
usage: cvrs dota validate [-h] [--metadata-only] dataset

positional arguments:
  dataset

options:
  -h, --help       show this help message and exit
  --metadata-only
```

## cvrs env

```text
usage: cvrs env [-h]
                {activate,apply,create,diff,doctor,freeze,managed,observe,plan,repair,upgrade} ...

positional arguments:
  {activate,apply,create,diff,doctor,freeze,managed,observe,plan,repair,upgrade}

options:
  -h, --help            show this help message and exit
```

## cvrs env activate

```text
usage: cvrs env activate [-h] [--out OUT] [--store STORE] [--spec SPEC]
                         [--plan PLAN] [--python PYTHON]
                         [--environment ENVIRONMENT] [--pack PACK]
                         [--operation OPERATION] [--actor ACTOR]
                         [--approval APPROVAL] [--approve APPROVE]
                         [--replacement REPLACEMENT]
                         [--worker-python WORKER_PYTHON] [--format FORMAT]
                         [--field FIELD] [--repository REPOSITORY]
                         [--version VERSION] [--previous PREVIOUS]
                         [--status STATUS] [--task TASK] [--subject SUBJECT]
                         [--evidence EVIDENCE] [--reason REASON]
                         [--files [FILES ...]] [--trust] [--verify] [--apply]
                         [--preview] [--force]
                         [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs env apply

```text
usage: cvrs env apply [-h] [--out OUT] [--store STORE] [--spec SPEC]
                      [--plan PLAN] [--python PYTHON]
                      [--environment ENVIRONMENT] [--pack PACK]
                      [--operation OPERATION] [--actor ACTOR]
                      [--approval APPROVAL] [--approve APPROVE]
                      [--replacement REPLACEMENT]
                      [--worker-python WORKER_PYTHON] [--format FORMAT]
                      [--field FIELD] [--repository REPOSITORY]
                      [--version VERSION] [--previous PREVIOUS]
                      [--status STATUS] [--task TASK] [--subject SUBJECT]
                      [--evidence EVIDENCE] [--reason REASON]
                      [--files [FILES ...]] [--trust] [--verify] [--apply]
                      [--preview] [--force]
                      [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs env create

```text
usage: cvrs env create [-h] [--out OUT] [--store STORE] [--spec SPEC]
                       [--plan PLAN] [--python PYTHON]
                       [--environment ENVIRONMENT] [--pack PACK]
                       [--operation OPERATION] [--actor ACTOR]
                       [--approval APPROVAL] [--approve APPROVE]
                       [--replacement REPLACEMENT]
                       [--worker-python WORKER_PYTHON] [--format FORMAT]
                       [--field FIELD] [--repository REPOSITORY]
                       [--version VERSION] [--previous PREVIOUS]
                       [--status STATUS] [--task TASK] [--subject SUBJECT]
                       [--evidence EVIDENCE] [--reason REASON]
                       [--files [FILES ...]] [--trust] [--verify] [--apply]
                       [--preview] [--force]
                       [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs env diff

```text
usage: cvrs env diff [-h] [--out OUT] [--store STORE] [--spec SPEC]
                     [--plan PLAN] [--python PYTHON]
                     [--environment ENVIRONMENT] [--pack PACK]
                     [--operation OPERATION] [--actor ACTOR]
                     [--approval APPROVAL] [--approve APPROVE]
                     [--replacement REPLACEMENT]
                     [--worker-python WORKER_PYTHON] [--format FORMAT]
                     [--field FIELD] [--repository REPOSITORY]
                     [--version VERSION] [--previous PREVIOUS]
                     [--status STATUS] [--task TASK] [--subject SUBJECT]
                     [--evidence EVIDENCE] [--reason REASON]
                     [--files [FILES ...]] [--trust] [--verify] [--apply]
                     [--preview] [--force]
                     [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs env doctor

```text
usage: cvrs env doctor [-h] [--out OUT] [--store STORE] [--spec SPEC]
                       [--plan PLAN] [--python PYTHON]
                       [--environment ENVIRONMENT] [--pack PACK]
                       [--operation OPERATION] [--actor ACTOR]
                       [--approval APPROVAL] [--approve APPROVE]
                       [--replacement REPLACEMENT]
                       [--worker-python WORKER_PYTHON] [--format FORMAT]
                       [--field FIELD] [--repository REPOSITORY]
                       [--version VERSION] [--previous PREVIOUS]
                       [--status STATUS] [--task TASK] [--subject SUBJECT]
                       [--evidence EVIDENCE] [--reason REASON]
                       [--files [FILES ...]] [--trust] [--verify] [--apply]
                       [--preview] [--force]
                       [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs env explain

```text
usage: cvrs env explain [-h] [--marker-environment MARKER_ENVIRONMENT]
                        repos [repos ...]

positional arguments:
  repos

options:
  -h, --help            show this help message and exit
  --marker-environment MARKER_ENVIRONMENT
```

## cvrs env freeze

```text
usage: cvrs env freeze [-h] [--out OUT] [--store STORE] [--spec SPEC]
                       [--plan PLAN] [--python PYTHON]
                       [--environment ENVIRONMENT] [--pack PACK]
                       [--operation OPERATION] [--actor ACTOR]
                       [--approval APPROVAL] [--approve APPROVE]
                       [--replacement REPLACEMENT]
                       [--worker-python WORKER_PYTHON] [--format FORMAT]
                       [--field FIELD] [--repository REPOSITORY]
                       [--version VERSION] [--previous PREVIOUS]
                       [--status STATUS] [--task TASK] [--subject SUBJECT]
                       [--evidence EVIDENCE] [--reason REASON]
                       [--files [FILES ...]] [--trust] [--verify] [--apply]
                       [--preview] [--force]
                       [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs env hpc

```text
usage: cvrs env hpc [-h] --out OUT [--scheduler {slurm,pbs,lsf}] [--cpus CPUS]
                    [--memory-gb MEMORY_GB] [--gpus GPUS]
                    [--walltime WALLTIME] [--container CONTAINER]
                    [--python PYTHON]
                    spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --scheduler {slurm,pbs,lsf}
  --cpus CPUS
  --memory-gb MEMORY_GB
  --gpus GPUS
  --walltime WALLTIME
  --container CONTAINER
  --python PYTHON
```

## cvrs env list

```text
usage: cvrs env list [-h]

options:
  -h, --help  show this help message and exit
```

## cvrs env managed

```text
usage: cvrs env managed [-h] [--out OUT] [--store STORE] [--spec SPEC]
                        [--plan PLAN] [--python PYTHON]
                        [--environment ENVIRONMENT] [--pack PACK]
                        [--operation OPERATION] [--actor ACTOR]
                        [--approval APPROVAL] [--approve APPROVE]
                        [--replacement REPLACEMENT]
                        [--worker-python WORKER_PYTHON] [--format FORMAT]
                        [--field FIELD] [--repository REPOSITORY]
                        [--version VERSION] [--previous PREVIOUS]
                        [--status STATUS] [--task TASK] [--subject SUBJECT]
                        [--evidence EVIDENCE] [--reason REASON]
                        [--files [FILES ...]] [--trust] [--verify] [--apply]
                        [--preview] [--force]
                        [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs env observe

```text
usage: cvrs env observe [-h] [--out OUT] [--store STORE] [--spec SPEC]
                        [--plan PLAN] [--python PYTHON]
                        [--environment ENVIRONMENT] [--pack PACK]
                        [--operation OPERATION] [--actor ACTOR]
                        [--approval APPROVAL] [--approve APPROVE]
                        [--replacement REPLACEMENT]
                        [--worker-python WORKER_PYTHON] [--format FORMAT]
                        [--field FIELD] [--repository REPOSITORY]
                        [--version VERSION] [--previous PREVIOUS]
                        [--status STATUS] [--task TASK] [--subject SUBJECT]
                        [--evidence EVIDENCE] [--reason REASON]
                        [--files [FILES ...]] [--trust] [--verify] [--apply]
                        [--preview] [--force]
                        [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs env plan

```text
usage: cvrs env plan [-h] [--out OUT] [--store STORE] [--spec SPEC]
                     [--plan PLAN] [--python PYTHON]
                     [--environment ENVIRONMENT] [--pack PACK]
                     [--operation OPERATION] [--actor ACTOR]
                     [--approval APPROVAL] [--approve APPROVE]
                     [--replacement REPLACEMENT]
                     [--worker-python WORKER_PYTHON] [--format FORMAT]
                     [--field FIELD] [--repository REPOSITORY]
                     [--version VERSION] [--previous PREVIOUS]
                     [--status STATUS] [--task TASK] [--subject SUBJECT]
                     [--evidence EVIDENCE] [--reason REASON]
                     [--files [FILES ...]] [--trust] [--verify] [--apply]
                     [--preview] [--force]
                     [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs env repair

```text
usage: cvrs env repair [-h] [--out OUT] [--store STORE] [--spec SPEC]
                       [--plan PLAN] [--python PYTHON]
                       [--environment ENVIRONMENT] [--pack PACK]
                       [--operation OPERATION] [--actor ACTOR]
                       [--approval APPROVAL] [--approve APPROVE]
                       [--replacement REPLACEMENT]
                       [--worker-python WORKER_PYTHON] [--format FORMAT]
                       [--field FIELD] [--repository REPOSITORY]
                       [--version VERSION] [--previous PREVIOUS]
                       [--status STATUS] [--task TASK] [--subject SUBJECT]
                       [--evidence EVIDENCE] [--reason REASON]
                       [--files [FILES ...]] [--trust] [--verify] [--apply]
                       [--preview] [--force]
                       [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs env scaffold

```text
usage: cvrs env scaffold [-h] [--pins PINS] [--python-version PYTHON_VERSION]
                         [--base-image BASE_IMAGE]
                         pack destination

positional arguments:
  pack
  destination

options:
  -h, --help            show this help message and exit
  --pins PINS
  --python-version PYTHON_VERSION
  --base-image BASE_IMAGE
```

## cvrs env upgrade

```text
usage: cvrs env upgrade [-h] [--out OUT] [--store STORE] [--spec SPEC]
                        [--plan PLAN] [--python PYTHON]
                        [--environment ENVIRONMENT] [--pack PACK]
                        [--operation OPERATION] [--actor ACTOR]
                        [--approval APPROVAL] [--approve APPROVE]
                        [--replacement REPLACEMENT]
                        [--worker-python WORKER_PYTHON] [--format FORMAT]
                        [--field FIELD] [--repository REPOSITORY]
                        [--version VERSION] [--previous PREVIOUS]
                        [--status STATUS] [--task TASK] [--subject SUBJECT]
                        [--evidence EVIDENCE] [--reason REASON]
                        [--files [FILES ...]] [--trust] [--verify] [--apply]
                        [--preview] [--force]
                        [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs environment

```text
usage: cvrs environment [-h] {capture,import,capsule} ...

positional arguments:
  {capture,import,capsule}

options:
  -h, --help            show this help message and exit
```

## cvrs environment capsule

```text
usage: cvrs environment capsule [-h] --out OUT spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs environment capture

```text
usage: cvrs environment capture [-h] [--out OUT] [--probe-hardware]

options:
  -h, --help        show this help message and exit
  --out OUT
  --probe-hardware
```

## cvrs environment import

```text
usage: cvrs environment import [-h]
                               --kind {pip,uv,conda,conda-explicit,docker}
                               [--out OUT]
                               source

positional arguments:
  source

options:
  -h, --help            show this help message and exit
  --kind {pip,uv,conda,conda-explicit,docker}
  --out OUT
```

## cvrs evaluate

```text
usage: cvrs evaluate [-h] [--evaluator-python EVALUATOR_PYTHON]
                     --dataset DATASET [--split SPLIT] --protocol PROTOCOL
                     [--out OUT]
                     predictions

positional arguments:
  predictions

options:
  -h, --help            show this help message and exit
  --evaluator-python EVALUATOR_PYTHON
  --dataset DATASET
  --split SPLIT
  --protocol PROTOCOL
  --out OUT
```

## cvrs exchange

```text
usage: cvrs exchange [-h]
                     {audit,decode,export,fiftyone-import,import,native,tracking} ...

positional arguments:
  {audit,decode,export,fiftyone-import,import,native,tracking}

options:
  -h, --help            show this help message and exit
```

## cvrs exchange audit

```text
usage: cvrs exchange audit [-h] [--out OUT] [--store STORE] [--spec SPEC]
                           [--plan PLAN] [--python PYTHON]
                           [--environment ENVIRONMENT] [--pack PACK]
                           [--operation OPERATION] [--actor ACTOR]
                           [--approval APPROVAL] [--approve APPROVE]
                           [--replacement REPLACEMENT]
                           [--worker-python WORKER_PYTHON] [--format FORMAT]
                           [--field FIELD] [--repository REPOSITORY]
                           [--version VERSION] [--previous PREVIOUS]
                           [--status STATUS] [--task TASK] [--subject SUBJECT]
                           [--evidence EVIDENCE] [--reason REASON]
                           [--files [FILES ...]] [--trust] [--verify]
                           [--apply] [--preview] [--force]
                           [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs exchange decode

```text
usage: cvrs exchange decode [-h] [--out OUT] [--store STORE] [--spec SPEC]
                            [--plan PLAN] [--python PYTHON]
                            [--environment ENVIRONMENT] [--pack PACK]
                            [--operation OPERATION] [--actor ACTOR]
                            [--approval APPROVAL] [--approve APPROVE]
                            [--replacement REPLACEMENT]
                            [--worker-python WORKER_PYTHON] [--format FORMAT]
                            [--field FIELD] [--repository REPOSITORY]
                            [--version VERSION] [--previous PREVIOUS]
                            [--status STATUS] [--task TASK]
                            [--subject SUBJECT] [--evidence EVIDENCE]
                            [--reason REASON] [--files [FILES ...]] [--trust]
                            [--verify] [--apply] [--preview] [--force]
                            [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs exchange export

```text
usage: cvrs exchange export [-h] [--out OUT] [--store STORE] [--spec SPEC]
                            [--plan PLAN] [--python PYTHON]
                            [--environment ENVIRONMENT] [--pack PACK]
                            [--operation OPERATION] [--actor ACTOR]
                            [--approval APPROVAL] [--approve APPROVE]
                            [--replacement REPLACEMENT]
                            [--worker-python WORKER_PYTHON] [--format FORMAT]
                            [--field FIELD] [--repository REPOSITORY]
                            [--version VERSION] [--previous PREVIOUS]
                            [--status STATUS] [--task TASK]
                            [--subject SUBJECT] [--evidence EVIDENCE]
                            [--reason REASON] [--files [FILES ...]] [--trust]
                            [--verify] [--apply] [--preview] [--force]
                            [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs exchange fiftyone-import

```text
usage: cvrs exchange fiftyone-import [-h] [--out OUT] [--store STORE]
                                     [--spec SPEC] [--plan PLAN]
                                     [--python PYTHON]
                                     [--environment ENVIRONMENT] [--pack PACK]
                                     [--operation OPERATION] [--actor ACTOR]
                                     [--approval APPROVAL] [--approve APPROVE]
                                     [--replacement REPLACEMENT]
                                     [--worker-python WORKER_PYTHON]
                                     [--format FORMAT] [--field FIELD]
                                     [--repository REPOSITORY]
                                     [--version VERSION] [--previous PREVIOUS]
                                     [--status STATUS] [--task TASK]
                                     [--subject SUBJECT] [--evidence EVIDENCE]
                                     [--reason REASON] [--files [FILES ...]]
                                     [--trust] [--verify] [--apply]
                                     [--preview] [--force]
                                     [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs exchange import

```text
usage: cvrs exchange import [-h] [--out OUT] [--store STORE] [--spec SPEC]
                            [--plan PLAN] [--python PYTHON]
                            [--environment ENVIRONMENT] [--pack PACK]
                            [--operation OPERATION] [--actor ACTOR]
                            [--approval APPROVAL] [--approve APPROVE]
                            [--replacement REPLACEMENT]
                            [--worker-python WORKER_PYTHON] [--format FORMAT]
                            [--field FIELD] [--repository REPOSITORY]
                            [--version VERSION] [--previous PREVIOUS]
                            [--status STATUS] [--task TASK]
                            [--subject SUBJECT] [--evidence EVIDENCE]
                            [--reason REASON] [--files [FILES ...]] [--trust]
                            [--verify] [--apply] [--preview] [--force]
                            [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs exchange native

```text
usage: cvrs exchange native [-h] [--out OUT] [--store STORE] [--spec SPEC]
                            [--plan PLAN] [--python PYTHON]
                            [--environment ENVIRONMENT] [--pack PACK]
                            [--operation OPERATION] [--actor ACTOR]
                            [--approval APPROVAL] [--approve APPROVE]
                            [--replacement REPLACEMENT]
                            [--worker-python WORKER_PYTHON] [--format FORMAT]
                            [--field FIELD] [--repository REPOSITORY]
                            [--version VERSION] [--previous PREVIOUS]
                            [--status STATUS] [--task TASK]
                            [--subject SUBJECT] [--evidence EVIDENCE]
                            [--reason REASON] [--files [FILES ...]] [--trust]
                            [--verify] [--apply] [--preview] [--force]
                            [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs exchange tracking

```text
usage: cvrs exchange tracking [-h] [--out OUT] [--store STORE] [--spec SPEC]
                              [--plan PLAN] [--python PYTHON]
                              [--environment ENVIRONMENT] [--pack PACK]
                              [--operation OPERATION] [--actor ACTOR]
                              [--approval APPROVAL] [--approve APPROVE]
                              [--replacement REPLACEMENT]
                              [--worker-python WORKER_PYTHON]
                              [--format FORMAT] [--field FIELD]
                              [--repository REPOSITORY] [--version VERSION]
                              [--previous PREVIOUS] [--status STATUS]
                              [--task TASK] [--subject SUBJECT]
                              [--evidence EVIDENCE] [--reason REASON]
                              [--files [FILES ...]] [--trust] [--verify]
                              [--apply] [--preview] [--force]
                              [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs experiment

```text
usage: cvrs experiment [-h] {validate} spec

positional arguments:
  {validate}
  spec

options:
  -h, --help  show this help message and exit
```

## cvrs fixtures

```text
usage: cvrs fixtures [-h] destination

positional arguments:
  destination

options:
  -h, --help   show this help message and exit
```

## cvrs geotiff

```text
usage: cvrs geotiff [-h] {inspect,window} ...

positional arguments:
  {inspect,window}

options:
  -h, --help        show this help message and exit
```

## cvrs geotiff inspect

```text
usage: cvrs geotiff inspect [-h] source

positional arguments:
  source

options:
  -h, --help  show this help message and exit
```

## cvrs geotiff window

```text
usage: cvrs geotiff window [-h] --out OUT --window X Y WIDTH HEIGHT
                           --bands BANDS BANDS BANDS
                           --value-range VALUE_RANGE VALUE_RANGE
                           source

positional arguments:
  source

options:
  -h, --help            show this help message and exit
  --out OUT
  --window X Y WIDTH HEIGHT
  --bands BANDS BANDS BANDS
  --value-range VALUE_RANGE VALUE_RANGE
```

## cvrs graph

```text
usage: cvrs graph [-h] {actions,plan,run} ...

positional arguments:
  {actions,plan,run}

options:
  -h, --help          show this help message and exit
```

## cvrs graph actions

```text
usage: cvrs graph actions [-h]

options:
  -h, --help  show this help message and exit
```

## cvrs graph plan

```text
usage: cvrs graph plan [-h] spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
```

## cvrs graph run

```text
usage: cvrs graph run [-h] --out OUT [--resume] [--cache CACHE]
                      [--invalidate [INVALIDATE ...]]
                      spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --resume
  --cache CACHE
  --invalidate [INVALIDATE ...]
```

## cvrs groundwork-fixtures

```text
usage: cvrs groundwork-fixtures [-h] destination

positional arguments:
  destination

options:
  -h, --help   show this help message and exit
```

## cvrs heritage

```text
usage: cvrs heritage [-h]
                     {profiles,train-native,certify-training,import,graph,convert-predictions,trusted-import,catalogue} ...

positional arguments:
  {profiles,train-native,certify-training,import,graph,convert-predictions,trusted-import,catalogue}

options:
  -h, --help            show this help message and exit
```

## cvrs heritage catalogue

```text
usage: cvrs heritage catalogue [-h] {list,search,validate,add,docs} ...

positional arguments:
  {list,search,validate,add,docs}

options:
  -h, --help            show this help message and exit
```

## cvrs heritage catalogue add

```text
usage: cvrs heritage catalogue add [-h] --out OUT catalogue entry

positional arguments:
  catalogue
  entry

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs heritage catalogue docs

```text
usage: cvrs heritage catalogue docs [-h] --out OUT catalogue

positional arguments:
  catalogue

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs heritage catalogue list

```text
usage: cvrs heritage catalogue list [-h] catalogue

positional arguments:
  catalogue

options:
  -h, --help  show this help message and exit
```

## cvrs heritage catalogue search

```text
usage: cvrs heritage catalogue search [-h] catalogue query

positional arguments:
  catalogue
  query

options:
  -h, --help  show this help message and exit
```

## cvrs heritage catalogue validate

```text
usage: cvrs heritage catalogue validate [-h] catalogue

positional arguments:
  catalogue

options:
  -h, --help  show this help message and exit
```

## cvrs heritage certify-training

```text
usage: cvrs heritage certify-training [-h] --out OUT spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs heritage convert-predictions

```text
usage: cvrs heritage convert-predictions [-h] --format FORMAT
                                         --mapping MAPPING [--dataset DATASET]
                                         [--split SPLIT]
                                         [--image-id-map IMAGE_ID_MAP]
                                         [--angle-convention ANGLE_CONVENTION]
                                         --out OUT
                                         native

positional arguments:
  native

options:
  -h, --help            show this help message and exit
  --format FORMAT
  --mapping MAPPING
  --dataset DATASET
  --split SPLIT
  --image-id-map IMAGE_ID_MAP
  --angle-convention ANGLE_CONVENTION
  --out OUT
```

## cvrs heritage graph

```text
usage: cvrs heritage graph [-h] --source-root SOURCE_ROOT [--out OUT] config

positional arguments:
  config

options:
  -h, --help            show this help message and exit
  --source-root SOURCE_ROOT
  --out OUT
```

## cvrs heritage import

```text
usage: cvrs heritage import [-h] --out OUT spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs heritage profiles

```text
usage: cvrs heritage profiles [-h]

options:
  -h, --help  show this help message and exit
```

## cvrs heritage train-native

```text
usage: cvrs heritage train-native [-h] --out OUT
                                  [--worker-python WORKER_PYTHON]
                                  [--timeout TIMEOUT]
                                  spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
```

## cvrs heritage trusted-import

```text
usage: cvrs heritage trusted-import [-h] --out OUT
                                    [--worker-python WORKER_PYTHON]
                                    [--timeout TIMEOUT]
                                    spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
```

## cvrs heritage-graph

```text
usage: cvrs heritage-graph [-h] --source-root SOURCE_ROOT config

positional arguments:
  config

options:
  -h, --help            show this help message and exit
  --source-root SOURCE_ROOT
```

## cvrs heritage-import

```text
usage: cvrs heritage-import [-h] --source-root SOURCE_ROOT --out OUT
                            --upstream UPSTREAM --revision REVISION
                            [--checkpoint CHECKPOINT] [--dataset DATASET]
                            config

positional arguments:
  config

options:
  -h, --help            show this help message and exit
  --source-root SOURCE_ROOT
  --out OUT
  --upstream UPSTREAM
  --revision REVISION
  --checkpoint CHECKPOINT
  --dataset DATASET
```

## cvrs hf

```text
usage: cvrs hf [-h] {inspect,local-lock} ...

positional arguments:
  {inspect,local-lock}

options:
  -h, --help            show this help message and exit
```

## cvrs hf inspect

```text
usage: cvrs hf inspect [-h] [--revision REVISION] [--repo-type REPO_TYPE]
                       [--allow-network] [--out OUT]
                       repo

positional arguments:
  repo

options:
  -h, --help            show this help message and exit
  --revision REVISION
  --repo-type REPO_TYPE
  --allow-network
  --out OUT
```

## cvrs hf local-lock

```text
usage: cvrs hf local-lock [-h] [--repo-id REPO_ID] [--revision REVISION]
                          --out OUT
                          directory

positional arguments:
  directory

options:
  -h, --help           show this help message and exit
  --repo-id REPO_ID
  --revision REVISION
  --out OUT
```

## cvrs identity

```text
usage: cvrs identity [-h] {configure,derive} ...

positional arguments:
  {configure,derive}

options:
  -h, --help          show this help message and exit
```

## cvrs identity configure

```text
usage: cvrs identity configure [-h] [--license-text LICENSE_TEXT]
                               root settings

positional arguments:
  root
  settings

options:
  -h, --help            show this help message and exit
  --license-text LICENSE_TEXT
```

## cvrs identity derive

```text
usage: cvrs identity derive [-h] [--license-text LICENSE_TEXT] --out OUT
                            root settings

positional arguments:
  root
  settings

options:
  -h, --help            show this help message and exit
  --license-text LICENSE_TEXT
  --out OUT
```

## cvrs import-coco

```text
usage: cvrs import-coco [-h] --image-root IMAGE_ROOT --name NAME
                        [--role {train,dev,selection,locked_test}]
                        [--source {real,synthetic,unknown}] --out OUT
                        annotations

positional arguments:
  annotations

options:
  -h, --help            show this help message and exit
  --image-root IMAGE_ROOT
  --name NAME
  --role {train,dev,selection,locked_test}
  --source {real,synthetic,unknown}
  --out OUT
```

## cvrs import-predictions

```text
usage: cvrs import-predictions [-h] --dataset DATASET [--split SPLIT]
                               --mapping MAPPING
                               --format {mmdet2_bbox,mmdet3_instances}
                               --out OUT
                               native

positional arguments:
  native

options:
  -h, --help            show this help message and exit
  --dataset DATASET
  --split SPLIT
  --mapping MAPPING
  --format {mmdet2_bbox,mmdet3_instances}
  --out OUT
```

## cvrs init

```text
usage: cvrs init [-h] [--profile PROFILE] [--name NAME] destination

positional arguments:
  destination

options:
  -h, --help         show this help message and exit
  --profile PROFILE
  --name NAME
```

## cvrs inspect-repo

```text
usage: cvrs inspect-repo [-h] [--out OUT] repo

positional arguments:
  repo

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs large

```text
usage: cvrs large [-h] {plan,run,merge} ...

positional arguments:
  {plan,run,merge}

options:
  -h, --help        show this help message and exit
```

## cvrs large merge

```text
usage: cvrs large merge [-h] --policy POLICY [--out OUT] detections

positional arguments:
  detections

options:
  -h, --help       show this help message and exit
  --policy POLICY
  --out OUT
```

## cvrs large plan

```text
usage: cvrs large plan [-h] [--out OUT] spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs large run

```text
usage: cvrs large run [-h] --policy POLICY --out OUT
                      [--worker-python WORKER_PYTHON] [--timeout TIMEOUT]
                      [--evaluator-python EVALUATOR_PYTHON]
                      spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --policy POLICY
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
  --evaluator-python EVALUATOR_PYTHON
```

## cvrs ledger

```text
usage: cvrs ledger [-h] {verify,test-report,approve,final-run} ...

positional arguments:
  {verify,test-report,approve,final-run}

options:
  -h, --help            show this help message and exit
```

## cvrs ledger approve

```text
usage: cvrs ledger approve [-h] --approval APPROVAL ledger

positional arguments:
  ledger

options:
  -h, --help           show this help message and exit
  --approval APPROVAL
```

## cvrs ledger final-run

```text
usage: cvrs ledger final-run [-h] --ledger LEDGER
                             --approval-digest APPROVAL_DIGEST --out OUT
                             [--worker-python WORKER_PYTHON]
                             [--timeout TIMEOUT]
                             spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --ledger LEDGER
  --approval-digest APPROVAL_DIGEST
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
```

## cvrs ledger test-report

```text
usage: cvrs ledger test-report [-h] ledger

positional arguments:
  ledger

options:
  -h, --help  show this help message and exit
```

## cvrs ledger verify

```text
usage: cvrs ledger verify [-h] [--expected-head EXPECTED_HEAD] ledger

positional arguments:
  ledger

options:
  -h, --help            show this help message and exit
  --expected-head EXPECTED_HEAD
```

## cvrs licenses

```text
usage: cvrs licenses [-h] {audit} ...

positional arguments:
  {audit}

options:
  -h, --help  show this help message and exit
```

## cvrs licenses audit

```text
usage: cvrs licenses audit [-h] [--out OUT] spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs methodology

```text
usage: cvrs methodology [-h] {lint} ...

positional arguments:
  {lint}

options:
  -h, --help  show this help message and exit
```

## cvrs methodology lint

```text
usage: cvrs methodology lint [-h] [--out OUT] spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs migrate

```text
usage: cvrs migrate [-h] --out OUT [--schema SCHEMA] source

positional arguments:
  source

options:
  -h, --help       show this help message and exit
  --out OUT
  --schema SCHEMA
```

## cvrs migrate-run

```text
usage: cvrs migrate-run [-h] --out OUT source

positional arguments:
  source

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs model

```text
usage: cvrs model [-h]
                  {capabilities,predict,train-native,export,predict-obb,train-obb} ...

positional arguments:
  {capabilities,predict,train-native,export,predict-obb,train-obb}

options:
  -h, --help            show this help message and exit
```

## cvrs model capabilities

```text
usage: cvrs model capabilities [-h] [--worker-python WORKER_PYTHON]
                               [--timeout TIMEOUT]
                               {ultralytics,rfdetr}

positional arguments:
  {ultralytics,rfdetr}

options:
  -h, --help            show this help message and exit
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
```

## cvrs model export

```text
usage: cvrs model export [-h] --out OUT [--worker-python WORKER_PYTHON]
                         [--timeout TIMEOUT]
                         spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
```

## cvrs model predict

```text
usage: cvrs model predict [-h] --out OUT [--worker-python WORKER_PYTHON]
                          [--timeout TIMEOUT]
                          spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
```

## cvrs model predict-obb

```text
usage: cvrs model predict-obb [-h] --out OUT [--worker-python WORKER_PYTHON]
                              [--timeout TIMEOUT]
                              spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
```

## cvrs model train-native

```text
usage: cvrs model train-native [-h] --out OUT [--worker-python WORKER_PYTHON]
                               [--timeout TIMEOUT]
                               spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
```

## cvrs model train-obb

```text
usage: cvrs model train-obb [-h] --out OUT [--worker-python WORKER_PYTHON]
                            [--timeout TIMEOUT]
                            spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
```

## cvrs new

```text
usage: cvrs new [-h] {project} ...

positional arguments:
  {project}

options:
  -h, --help  show this help message and exit
```

## cvrs new project

```text
usage: cvrs new project [-h] [--profile PROFILE] [--name NAME] destination

positional arguments:
  destination

options:
  -h, --help         show this help message and exit
  --profile PROFILE
  --name NAME
```

## cvrs paper

```text
usage: cvrs paper [-h] {approve,execute,prepare,readiness} ...

positional arguments:
  {approve,execute,prepare,readiness}

options:
  -h, --help            show this help message and exit
```

## cvrs paper approve

```text
usage: cvrs paper approve [-h] [--out OUT] [--store STORE] [--spec SPEC]
                          [--plan PLAN] [--python PYTHON]
                          [--environment ENVIRONMENT] [--pack PACK]
                          [--operation OPERATION] [--actor ACTOR]
                          [--approval APPROVAL] [--approve APPROVE]
                          [--replacement REPLACEMENT]
                          [--worker-python WORKER_PYTHON] [--format FORMAT]
                          [--field FIELD] [--repository REPOSITORY]
                          [--version VERSION] [--previous PREVIOUS]
                          [--status STATUS] [--task TASK] [--subject SUBJECT]
                          [--evidence EVIDENCE] [--reason REASON]
                          [--files [FILES ...]] [--trust] [--verify] [--apply]
                          [--preview] [--force]
                          [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs paper execute

```text
usage: cvrs paper execute [-h] [--out OUT] [--store STORE] [--spec SPEC]
                          [--plan PLAN] [--python PYTHON]
                          [--environment ENVIRONMENT] [--pack PACK]
                          [--operation OPERATION] [--actor ACTOR]
                          [--approval APPROVAL] [--approve APPROVE]
                          [--replacement REPLACEMENT]
                          [--worker-python WORKER_PYTHON] [--format FORMAT]
                          [--field FIELD] [--repository REPOSITORY]
                          [--version VERSION] [--previous PREVIOUS]
                          [--status STATUS] [--task TASK] [--subject SUBJECT]
                          [--evidence EVIDENCE] [--reason REASON]
                          [--files [FILES ...]] [--trust] [--verify] [--apply]
                          [--preview] [--force]
                          [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs paper import

```text
usage: cvrs paper import [-h] --out OUT [--python PYTHON] repo

positional arguments:
  repo

options:
  -h, --help       show this help message and exit
  --out OUT
  --python PYTHON
```

## cvrs paper prepare

```text
usage: cvrs paper prepare [-h] [--out OUT] [--store STORE] [--spec SPEC]
                          [--plan PLAN] [--python PYTHON]
                          [--environment ENVIRONMENT] [--pack PACK]
                          [--operation OPERATION] [--actor ACTOR]
                          [--approval APPROVAL] [--approve APPROVE]
                          [--replacement REPLACEMENT]
                          [--worker-python WORKER_PYTHON] [--format FORMAT]
                          [--field FIELD] [--repository REPOSITORY]
                          [--version VERSION] [--previous PREVIOUS]
                          [--status STATUS] [--task TASK] [--subject SUBJECT]
                          [--evidence EVIDENCE] [--reason REASON]
                          [--files [FILES ...]] [--trust] [--verify] [--apply]
                          [--preview] [--force]
                          [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs paper readiness

```text
usage: cvrs paper readiness [-h] [--out OUT] [--store STORE] [--spec SPEC]
                            [--plan PLAN] [--python PYTHON]
                            [--environment ENVIRONMENT] [--pack PACK]
                            [--operation OPERATION] [--actor ACTOR]
                            [--approval APPROVAL] [--approve APPROVE]
                            [--replacement REPLACEMENT]
                            [--worker-python WORKER_PYTHON] [--format FORMAT]
                            [--field FIELD] [--repository REPOSITORY]
                            [--version VERSION] [--previous PREVIOUS]
                            [--status STATUS] [--task TASK]
                            [--subject SUBJECT] [--evidence EVIDENCE]
                            [--reason REASON] [--files [FILES ...]] [--trust]
                            [--verify] [--apply] [--preview] [--force]
                            [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs paper run

```text
usage: cvrs paper run [-h] [--operation OPERATION] --out OUT [--trust] spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --operation OPERATION
  --out OUT
  --trust
```

## cvrs paper validate

```text
usage: cvrs paper validate [-h] spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
```

## cvrs plugin

```text
usage: cvrs plugin [-h]
                   {list,inspect,register,scaffold,validate,conformance,run,negotiate} ...

positional arguments:
  {list,inspect,register,scaffold,validate,conformance,run,negotiate}

options:
  -h, --help            show this help message and exit
```

## cvrs plugin conformance

```text
usage: cvrs plugin conformance [-h] [--trust-code]
                               [--worker-python WORKER_PYTHON]
                               [--timeout TIMEOUT] --fixtures FIXTURES
                               --out OUT
                               descriptor

positional arguments:
  descriptor

options:
  -h, --help            show this help message and exit
  --trust-code
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
  --fixtures FIXTURES
  --out OUT
```

## cvrs plugin inspect

```text
usage: cvrs plugin inspect [-h] --registry REGISTRY name

positional arguments:
  name

options:
  -h, --help           show this help message and exit
  --registry REGISTRY
```

## cvrs plugin list

```text
usage: cvrs plugin list [-h] --registry REGISTRY

options:
  -h, --help           show this help message and exit
  --registry REGISTRY
```

## cvrs plugin negotiate

```text
usage: cvrs plugin negotiate [-h] spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
```

## cvrs plugin register

```text
usage: cvrs plugin register [-h] --registry REGISTRY descriptor

positional arguments:
  descriptor

options:
  -h, --help           show this help message and exit
  --registry REGISTRY
```

## cvrs plugin run

```text
usage: cvrs plugin run [-h] [--trust-code] [--worker-python WORKER_PYTHON]
                       [--timeout TIMEOUT] --operation OPERATION
                       --payload PAYLOAD --out OUT
                       descriptor

positional arguments:
  descriptor

options:
  -h, --help            show this help message and exit
  --trust-code
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
  --operation OPERATION
  --payload PAYLOAD
  --out OUT
```

## cvrs plugin scaffold

```text
usage: cvrs plugin scaffold [-h] [--kind KIND] --out OUT name

positional arguments:
  name

options:
  -h, --help   show this help message and exit
  --kind KIND
  --out OUT
```

## cvrs plugin validate

```text
usage: cvrs plugin validate [-h] [--trust-code]
                            [--worker-python WORKER_PYTHON]
                            [--timeout TIMEOUT]
                            descriptor

positional arguments:
  descriptor

options:
  -h, --help            show this help message and exit
  --trust-code
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
```

## cvrs profile

```text
usage: cvrs profile [-h] --argv ARGV --out OUT [--trust] [--timeout TIMEOUT]
                    [--gpu-metrics] [--phase-events PHASE_EVENTS]

options:
  -h, --help            show this help message and exit
  --argv ARGV
  --out OUT
  --trust
  --timeout TIMEOUT
  --gpu-metrics
  --phase-events PHASE_EVENTS
```

## cvrs protocol

```text
usage: cvrs protocol [-h] [--out OUT] {plan} spec

positional arguments:
  {plan}
  spec

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs quantize

```text
usage: cvrs quantize [-h] {validate,run,prepare,regression} ...

positional arguments:
  {validate,run,prepare,regression}

options:
  -h, --help            show this help message and exit
```

## cvrs quantize prepare

```text
usage: cvrs quantize prepare [-h] --out OUT spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs quantize regression

```text
usage: cvrs quantize regression [-h] --limits LIMITS baseline quantized

positional arguments:
  baseline
  quantized

options:
  -h, --help       show this help message and exit
  --limits LIMITS
```

## cvrs quantize run

```text
usage: cvrs quantize run [-h] --out OUT [--worker-python WORKER_PYTHON]
                         [--timeout TIMEOUT]
                         spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
```

## cvrs quantize validate

```text
usage: cvrs quantize validate [-h] spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
```

## cvrs quickstart

```text
usage: cvrs quickstart [-h] [--python PYTHON] [--timeout TIMEOUT] destination

positional arguments:
  destination

options:
  -h, --help         show this help message and exit
  --python PYTHON
  --timeout TIMEOUT
```

## cvrs recipe

```text
usage: cvrs recipe [-h] {check,contribute,index,search} ...

positional arguments:
  {check,contribute,index,search}

options:
  -h, --help            show this help message and exit
```

## cvrs recipe assets

```text
usage: cvrs recipe assets [-h] recipe bindings

positional arguments:
  recipe
  bindings

options:
  -h, --help  show this help message and exit
```

## cvrs recipe check

```text
usage: cvrs recipe check [-h] [--out OUT] [--store STORE] [--spec SPEC]
                         [--plan PLAN] [--python PYTHON]
                         [--environment ENVIRONMENT] [--pack PACK]
                         [--operation OPERATION] [--actor ACTOR]
                         [--approval APPROVAL] [--approve APPROVE]
                         [--replacement REPLACEMENT]
                         [--worker-python WORKER_PYTHON] [--format FORMAT]
                         [--field FIELD] [--repository REPOSITORY]
                         [--version VERSION] [--previous PREVIOUS]
                         [--status STATUS] [--task TASK] [--subject SUBJECT]
                         [--evidence EVIDENCE] [--reason REASON]
                         [--files [FILES ...]] [--trust] [--verify] [--apply]
                         [--preview] [--force]
                         [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs recipe contribute

```text
usage: cvrs recipe contribute [-h] [--out OUT] [--store STORE] [--spec SPEC]
                              [--plan PLAN] [--python PYTHON]
                              [--environment ENVIRONMENT] [--pack PACK]
                              [--operation OPERATION] [--actor ACTOR]
                              [--approval APPROVAL] [--approve APPROVE]
                              [--replacement REPLACEMENT]
                              [--worker-python WORKER_PYTHON]
                              [--format FORMAT] [--field FIELD]
                              [--repository REPOSITORY] [--version VERSION]
                              [--previous PREVIOUS] [--status STATUS]
                              [--task TASK] [--subject SUBJECT]
                              [--evidence EVIDENCE] [--reason REASON]
                              [--files [FILES ...]] [--trust] [--verify]
                              [--apply] [--preview] [--force]
                              [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs recipe index

```text
usage: cvrs recipe index [-h] [--out OUT] [--store STORE] [--spec SPEC]
                         [--plan PLAN] [--python PYTHON]
                         [--environment ENVIRONMENT] [--pack PACK]
                         [--operation OPERATION] [--actor ACTOR]
                         [--approval APPROVAL] [--approve APPROVE]
                         [--replacement REPLACEMENT]
                         [--worker-python WORKER_PYTHON] [--format FORMAT]
                         [--field FIELD] [--repository REPOSITORY]
                         [--version VERSION] [--previous PREVIOUS]
                         [--status STATUS] [--task TASK] [--subject SUBJECT]
                         [--evidence EVIDENCE] [--reason REASON]
                         [--files [FILES ...]] [--trust] [--verify] [--apply]
                         [--preview] [--force]
                         [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs recipe inspect

```text
usage: cvrs recipe inspect [-h] name

positional arguments:
  name

options:
  -h, --help  show this help message and exit
```

## cvrs recipe list

```text
usage: cvrs recipe list [-h]

options:
  -h, --help  show this help message and exit
```

## cvrs recipe materialize

```text
usage: cvrs recipe materialize [-h] --out OUT name

positional arguments:
  name

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs recipe search

```text
usage: cvrs recipe search [-h] [--out OUT] [--store STORE] [--spec SPEC]
                          [--plan PLAN] [--python PYTHON]
                          [--environment ENVIRONMENT] [--pack PACK]
                          [--operation OPERATION] [--actor ACTOR]
                          [--approval APPROVAL] [--approve APPROVE]
                          [--replacement REPLACEMENT]
                          [--worker-python WORKER_PYTHON] [--format FORMAT]
                          [--field FIELD] [--repository REPOSITORY]
                          [--version VERSION] [--previous PREVIOUS]
                          [--status STATUS] [--task TASK] [--subject SUBJECT]
                          [--evidence EVIDENCE] [--reason REASON]
                          [--files [FILES ...]] [--trust] [--verify] [--apply]
                          [--preview] [--force]
                          [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs recover

```text
usage: cvrs recover [-h] --reason REASON [--acknowledge-process-stopped] run

positional arguments:
  run

options:
  -h, --help            show this help message and exit
  --reason REASON
  --acknowledge-process-stopped
```

## cvrs reference-parity

```text
usage: cvrs reference-parity [-h] --dataset DATASET [--split SPLIT]
                             --protocol PROTOCOL [--tolerance TOLERANCE]
                             [--out OUT]
                             predictions

positional arguments:
  predictions

options:
  -h, --help            show this help message and exit
  --dataset DATASET
  --split SPLIT
  --protocol PROTOCOL
  --tolerance TOLERANCE
  --out OUT
```

## cvrs release

```text
usage: cvrs release [-h]
                    {api-diff,citation-pack,contribution-check,freeze-api,launch-plan,preflight,security-apply,security-plan,verify-artifacts,workflows} ...

positional arguments:
  {api-diff,citation-pack,contribution-check,freeze-api,launch-plan,preflight,security-apply,security-plan,verify-artifacts,workflows}

options:
  -h, --help            show this help message and exit
```

## cvrs release api-diff

```text
usage: cvrs release api-diff [-h] [--out OUT] [--store STORE] [--spec SPEC]
                             [--plan PLAN] [--python PYTHON]
                             [--environment ENVIRONMENT] [--pack PACK]
                             [--operation OPERATION] [--actor ACTOR]
                             [--approval APPROVAL] [--approve APPROVE]
                             [--replacement REPLACEMENT]
                             [--worker-python WORKER_PYTHON] [--format FORMAT]
                             [--field FIELD] [--repository REPOSITORY]
                             [--version VERSION] [--previous PREVIOUS]
                             [--status STATUS] [--task TASK]
                             [--subject SUBJECT] [--evidence EVIDENCE]
                             [--reason REASON] [--files [FILES ...]] [--trust]
                             [--verify] [--apply] [--preview] [--force]
                             [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs release audit-public

```text
usage: cvrs release audit-public [-h] [--out OUT] root

positional arguments:
  root

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs release build

```text
usage: cvrs release build [-h] --out OUT [--wheel] root

positional arguments:
  root

options:
  -h, --help  show this help message and exit
  --out OUT
  --wheel
```

## cvrs release citation-pack

```text
usage: cvrs release citation-pack [-h] [--out OUT] [--store STORE]
                                  [--spec SPEC] [--plan PLAN]
                                  [--python PYTHON]
                                  [--environment ENVIRONMENT] [--pack PACK]
                                  [--operation OPERATION] [--actor ACTOR]
                                  [--approval APPROVAL] [--approve APPROVE]
                                  [--replacement REPLACEMENT]
                                  [--worker-python WORKER_PYTHON]
                                  [--format FORMAT] [--field FIELD]
                                  [--repository REPOSITORY]
                                  [--version VERSION] [--previous PREVIOUS]
                                  [--status STATUS] [--task TASK]
                                  [--subject SUBJECT] [--evidence EVIDENCE]
                                  [--reason REASON] [--files [FILES ...]]
                                  [--trust] [--verify] [--apply] [--preview]
                                  [--force]
                                  [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs release compatibility

```text
usage: cvrs release compatibility [-h] [--out OUT] old new

positional arguments:
  old
  new

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs release contribution-check

```text
usage: cvrs release contribution-check [-h] [--out OUT] [--store STORE]
                                       [--spec SPEC] [--plan PLAN]
                                       [--python PYTHON]
                                       [--environment ENVIRONMENT]
                                       [--pack PACK] [--operation OPERATION]
                                       [--actor ACTOR] [--approval APPROVAL]
                                       [--approve APPROVE]
                                       [--replacement REPLACEMENT]
                                       [--worker-python WORKER_PYTHON]
                                       [--format FORMAT] [--field FIELD]
                                       [--repository REPOSITORY]
                                       [--version VERSION]
                                       [--previous PREVIOUS] [--status STATUS]
                                       [--task TASK] [--subject SUBJECT]
                                       [--evidence EVIDENCE] [--reason REASON]
                                       [--files [FILES ...]] [--trust]
                                       [--verify] [--apply] [--preview]
                                       [--force]
                                       [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs release counts

```text
usage: cvrs release counts [-h] [--out OUT] root

positional arguments:
  root

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs release freeze-api

```text
usage: cvrs release freeze-api [-h] [--out OUT] [--store STORE] [--spec SPEC]
                               [--plan PLAN] [--python PYTHON]
                               [--environment ENVIRONMENT] [--pack PACK]
                               [--operation OPERATION] [--actor ACTOR]
                               [--approval APPROVAL] [--approve APPROVE]
                               [--replacement REPLACEMENT]
                               [--worker-python WORKER_PYTHON]
                               [--format FORMAT] [--field FIELD]
                               [--repository REPOSITORY] [--version VERSION]
                               [--previous PREVIOUS] [--status STATUS]
                               [--task TASK] [--subject SUBJECT]
                               [--evidence EVIDENCE] [--reason REASON]
                               [--files [FILES ...]] [--trust] [--verify]
                               [--apply] [--preview] [--force]
                               [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs release launch-plan

```text
usage: cvrs release launch-plan [-h] [--out OUT] [--store STORE] [--spec SPEC]
                                [--plan PLAN] [--python PYTHON]
                                [--environment ENVIRONMENT] [--pack PACK]
                                [--operation OPERATION] [--actor ACTOR]
                                [--approval APPROVAL] [--approve APPROVE]
                                [--replacement REPLACEMENT]
                                [--worker-python WORKER_PYTHON]
                                [--format FORMAT] [--field FIELD]
                                [--repository REPOSITORY] [--version VERSION]
                                [--previous PREVIOUS] [--status STATUS]
                                [--task TASK] [--subject SUBJECT]
                                [--evidence EVIDENCE] [--reason REASON]
                                [--files [FILES ...]] [--trust] [--verify]
                                [--apply] [--preview] [--force]
                                [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs release preflight

```text
usage: cvrs release preflight [-h] [--out OUT] [--store STORE] [--spec SPEC]
                              [--plan PLAN] [--python PYTHON]
                              [--environment ENVIRONMENT] [--pack PACK]
                              [--operation OPERATION] [--actor ACTOR]
                              [--approval APPROVAL] [--approve APPROVE]
                              [--replacement REPLACEMENT]
                              [--worker-python WORKER_PYTHON]
                              [--format FORMAT] [--field FIELD]
                              [--repository REPOSITORY] [--version VERSION]
                              [--previous PREVIOUS] [--status STATUS]
                              [--task TASK] [--subject SUBJECT]
                              [--evidence EVIDENCE] [--reason REASON]
                              [--files [FILES ...]] [--trust] [--verify]
                              [--apply] [--preview] [--force]
                              [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs release prepare

```text
usage: cvrs release prepare [-h] --out OUT --version VERSION --note NOTE root

positional arguments:
  root

options:
  -h, --help         show this help message and exit
  --out OUT
  --version VERSION
  --note NOTE
```

## cvrs release public-tree

```text
usage: cvrs release public-tree [-h] --out OUT [--preview] root

positional arguments:
  root

options:
  -h, --help  show this help message and exit
  --out OUT
  --preview
```

## cvrs release publish-bundle

```text
usage: cvrs release publish-bundle [-h] --out OUT [--preview] [--no-packages]
                                   root

positional arguments:
  root

options:
  -h, --help     show this help message and exit
  --out OUT
  --preview
  --no-packages
```

## cvrs release sbom

```text
usage: cvrs release sbom [-h] [--out OUT] root

positional arguments:
  root

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs release security-apply

```text
usage: cvrs release security-apply [-h] [--out OUT] [--store STORE]
                                   [--spec SPEC] [--plan PLAN]
                                   [--python PYTHON]
                                   [--environment ENVIRONMENT] [--pack PACK]
                                   [--operation OPERATION] [--actor ACTOR]
                                   [--approval APPROVAL] [--approve APPROVE]
                                   [--replacement REPLACEMENT]
                                   [--worker-python WORKER_PYTHON]
                                   [--format FORMAT] [--field FIELD]
                                   [--repository REPOSITORY]
                                   [--version VERSION] [--previous PREVIOUS]
                                   [--status STATUS] [--task TASK]
                                   [--subject SUBJECT] [--evidence EVIDENCE]
                                   [--reason REASON] [--files [FILES ...]]
                                   [--trust] [--verify] [--apply] [--preview]
                                   [--force]
                                   [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs release security-plan

```text
usage: cvrs release security-plan [-h] [--out OUT] [--store STORE]
                                  [--spec SPEC] [--plan PLAN]
                                  [--python PYTHON]
                                  [--environment ENVIRONMENT] [--pack PACK]
                                  [--operation OPERATION] [--actor ACTOR]
                                  [--approval APPROVAL] [--approve APPROVE]
                                  [--replacement REPLACEMENT]
                                  [--worker-python WORKER_PYTHON]
                                  [--format FORMAT] [--field FIELD]
                                  [--repository REPOSITORY]
                                  [--version VERSION] [--previous PREVIOUS]
                                  [--status STATUS] [--task TASK]
                                  [--subject SUBJECT] [--evidence EVIDENCE]
                                  [--reason REASON] [--files [FILES ...]]
                                  [--trust] [--verify] [--apply] [--preview]
                                  [--force]
                                  [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs release verify

```text
usage: cvrs release verify [-h] [--out OUT] root

positional arguments:
  root

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs release verify-artifacts

```text
usage: cvrs release verify-artifacts [-h] [--out OUT] [--store STORE]
                                     [--spec SPEC] [--plan PLAN]
                                     [--python PYTHON]
                                     [--environment ENVIRONMENT] [--pack PACK]
                                     [--operation OPERATION] [--actor ACTOR]
                                     [--approval APPROVAL] [--approve APPROVE]
                                     [--replacement REPLACEMENT]
                                     [--worker-python WORKER_PYTHON]
                                     [--format FORMAT] [--field FIELD]
                                     [--repository REPOSITORY]
                                     [--version VERSION] [--previous PREVIOUS]
                                     [--status STATUS] [--task TASK]
                                     [--subject SUBJECT] [--evidence EVIDENCE]
                                     [--reason REASON] [--files [FILES ...]]
                                     [--trust] [--verify] [--apply]
                                     [--preview] [--force]
                                     [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs release workflows

```text
usage: cvrs release workflows [-h] [--out OUT] [--store STORE] [--spec SPEC]
                              [--plan PLAN] [--python PYTHON]
                              [--environment ENVIRONMENT] [--pack PACK]
                              [--operation OPERATION] [--actor ACTOR]
                              [--approval APPROVAL] [--approve APPROVE]
                              [--replacement REPLACEMENT]
                              [--worker-python WORKER_PYTHON]
                              [--format FORMAT] [--field FIELD]
                              [--repository REPOSITORY] [--version VERSION]
                              [--previous PREVIOUS] [--status STATUS]
                              [--task TASK] [--subject SUBJECT]
                              [--evidence EVIDENCE] [--reason REASON]
                              [--files [FILES ...]] [--trust] [--verify]
                              [--apply] [--preview] [--force]
                              [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs report

```text
usage: cvrs report [-h] {create} ...

positional arguments:
  {create}

options:
  -h, --help  show this help message and exit
```

## cvrs report create

```text
usage: cvrs report create [-h] [--title TITLE] [--limitation LIMITATION]
                          --out OUT
                          kind records [records ...]

positional arguments:
  kind
  records

options:
  -h, --help            show this help message and exit
  --title TITLE
  --limitation LIMITATION
  --out OUT
```

## cvrs research

```text
usage: cvrs research [-h] {lint} ...

positional arguments:
  {lint}

options:
  -h, --help  show this help message and exit
```

## cvrs research lint

```text
usage: cvrs research lint [-h] [--out OUT] [--store STORE] [--spec SPEC]
                          [--plan PLAN] [--python PYTHON]
                          [--environment ENVIRONMENT] [--pack PACK]
                          [--operation OPERATION] [--actor ACTOR]
                          [--approval APPROVAL] [--approve APPROVE]
                          [--replacement REPLACEMENT]
                          [--worker-python WORKER_PYTHON] [--format FORMAT]
                          [--field FIELD] [--repository REPOSITORY]
                          [--version VERSION] [--previous PREVIOUS]
                          [--status STATUS] [--task TASK] [--subject SUBJECT]
                          [--evidence EVIDENCE] [--reason REASON]
                          [--files [FILES ...]] [--trust] [--verify] [--apply]
                          [--preview] [--force]
                          [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs research-fixtures

```text
usage: cvrs research-fixtures [-h] destination

positional arguments:
  destination

options:
  -h, --help   show this help message and exit
```

## cvrs research-registry

```text
usage: cvrs research-registry [-h]
                              {init,verify,list,claim,attempt,review,evidence,status,supersede,export,import,capsule,restore,capture-run,reevaluate} ...

positional arguments:
  {init,verify,list,claim,attempt,review,evidence,status,supersede,export,import,capsule,restore,capture-run,reevaluate}

options:
  -h, --help            show this help message and exit
```

## cvrs research-registry attempt

```text
usage: cvrs research-registry attempt [-h] registry spec

positional arguments:
  registry
  spec

options:
  -h, --help  show this help message and exit
```

## cvrs research-registry capsule

```text
usage: cvrs research-registry capsule [-h] --out OUT [--archive ARCHIVE]
                                      registry

positional arguments:
  registry

options:
  -h, --help         show this help message and exit
  --out OUT
  --archive ARCHIVE
```

## cvrs research-registry capture-run

```text
usage: cvrs research-registry capture-run [-h] --dataset DATASET
                                          --metadata METADATA
                                          registry run

positional arguments:
  registry
  run

options:
  -h, --help           show this help message and exit
  --dataset DATASET
  --metadata METADATA
```

## cvrs research-registry claim

```text
usage: cvrs research-registry claim [-h] registry spec

positional arguments:
  registry
  spec

options:
  -h, --help  show this help message and exit
```

## cvrs research-registry evidence

```text
usage: cvrs research-registry evidence [-h] [--media-type MEDIA_TYPE]
                                       [--license-status LICENSE_STATUS]
                                       registry file

positional arguments:
  registry
  file

options:
  -h, --help            show this help message and exit
  --media-type MEDIA_TYPE
  --license-status LICENSE_STATUS
```

## cvrs research-registry export

```text
usage: cvrs research-registry export [-h] --out OUT registry

positional arguments:
  registry

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs research-registry import

```text
usage: cvrs research-registry import [-h] --out OUT snapshot

positional arguments:
  snapshot

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs research-registry init

```text
usage: cvrs research-registry init [-h] registry

positional arguments:
  registry

options:
  -h, --help  show this help message and exit
```

## cvrs research-registry list

```text
usage: cvrs research-registry list [-h] [--kind {claim,attempt,review}]
                                   registry

positional arguments:
  registry

options:
  -h, --help            show this help message and exit
  --kind {claim,attempt,review}
```

## cvrs research-registry reevaluate

```text
usage: cvrs research-registry reevaluate [-h] --dataset DATASET
                                         --predictions PREDICTIONS
                                         --protocol PROTOCOL [--split SPLIT]
                                         --out OUT
                                         [--evaluator-python EVALUATOR_PYTHON]
                                         [--origin ORIGIN]

options:
  -h, --help            show this help message and exit
  --dataset DATASET
  --predictions PREDICTIONS
  --protocol PROTOCOL
  --split SPLIT
  --out OUT
  --evaluator-python EVALUATOR_PYTHON
  --origin ORIGIN
```

## cvrs research-registry restore

```text
usage: cvrs research-registry restore [-h] --out OUT archive

positional arguments:
  archive

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs research-registry review

```text
usage: cvrs research-registry review [-h] registry spec

positional arguments:
  registry
  spec

options:
  -h, --help  show this help message and exit
```

## cvrs research-registry status

```text
usage: cvrs research-registry status [-h] registry claim_id

positional arguments:
  registry
  claim_id

options:
  -h, --help  show this help message and exit
```

## cvrs research-registry supersede

```text
usage: cvrs research-registry supersede [-h] --reason REASON registry old new

positional arguments:
  registry
  old
  new

options:
  -h, --help       show this help message and exit
  --reason REASON
```

## cvrs research-registry verify

```text
usage: cvrs research-registry verify [-h] registry

positional arguments:
  registry

options:
  -h, --help  show this help message and exit
```

## cvrs review

```text
usage: cvrs review [-h] [--out OUT] capsule

positional arguments:
  capsule

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs run

```text
usage: cvrs run [-h] [--out OUT] [--worker-python WORKER_PYTHON]
                [--timeout TIMEOUT] [--authorization AUTHORIZATION]
                [--evaluator-python EVALUATOR_PYTHON]
                spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
  --authorization AUTHORIZATION
  --evaluator-python EVALUATOR_PYTHON
```

## cvrs run-tiled

```text
usage: cvrs run-tiled [-h] --policy POLICY --out OUT
                      [--worker-python WORKER_PYTHON] [--timeout TIMEOUT]
                      spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --policy POLICY
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
```

## cvrs schema

```text
usage: cvrs schema [-h] {list,inspect,validate,export} ...

positional arguments:
  {list,inspect,validate,export}

options:
  -h, --help            show this help message and exit
```

## cvrs schema export

```text
usage: cvrs schema export [-h] --out OUT

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs schema inspect

```text
usage: cvrs schema inspect [-h] name

positional arguments:
  name

options:
  -h, --help  show this help message and exit
```

## cvrs schema list

```text
usage: cvrs schema list [-h]

options:
  -h, --help  show this help message and exit
```

## cvrs schema validate

```text
usage: cvrs schema validate [-h] [--schema SCHEMA] artifact

positional arguments:
  artifact

options:
  -h, --help       show this help message and exit
  --schema SCHEMA
```

## cvrs schemas

```text
usage: cvrs schemas [-h] destination

positional arguments:
  destination

options:
  -h, --help   show this help message and exit
```

## cvrs site

```text
usage: cvrs site [-h] {build} ...

positional arguments:
  {build}

options:
  -h, --help  show this help message and exit
```

## cvrs site build

```text
usage: cvrs site build [-h] [--out OUT] [--store STORE] [--spec SPEC]
                       [--plan PLAN] [--python PYTHON]
                       [--environment ENVIRONMENT] [--pack PACK]
                       [--operation OPERATION] [--actor ACTOR]
                       [--approval APPROVAL] [--approve APPROVE]
                       [--replacement REPLACEMENT]
                       [--worker-python WORKER_PYTHON] [--format FORMAT]
                       [--field FIELD] [--repository REPOSITORY]
                       [--version VERSION] [--previous PREVIOUS]
                       [--status STATUS] [--task TASK] [--subject SUBJECT]
                       [--evidence EVIDENCE] [--reason REASON]
                       [--files [FILES ...]] [--trust] [--verify] [--apply]
                       [--preview] [--force]
                       [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs site graph

```text
usage: cvrs site graph [-h] --out OUT spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs site results

```text
usage: cvrs site results [-h] --out OUT runs [runs ...]

positional arguments:
  runs

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs site visual-diff

```text
usage: cvrs site visual-diff [-h] --out OUT [--allow-image-copy]
                             image left right

positional arguments:
  image
  left
  right

options:
  -h, --help          show this help message and exit
  --out OUT
  --allow-image-copy
```

## cvrs size-evaluate

```text
usage: cvrs size-evaluate [-h] --dataset DATASET --policy POLICY
                          [--split SPLIT] [--iou IOU] [--threshold THRESHOLD]
                          [--gsd GSD] [--out OUT]
                          predictions

positional arguments:
  predictions

options:
  -h, --help            show this help message and exit
  --dataset DATASET
  --policy POLICY
  --split SPLIT
  --iou IOU
  --threshold THRESHOLD
  --gsd GSD
  --out OUT
```

## cvrs slice

```text
usage: cvrs slice [-h] {select} ...

positional arguments:
  {select}

options:
  -h, --help  show this help message and exit
```

## cvrs slice select

```text
usage: cvrs slice select [-h] [--split SPLIT] --policy POLICY
                         [--metadata METADATA] [--out OUT]
                         dataset

positional arguments:
  dataset

options:
  -h, --help           show this help message and exit
  --split SPLIT
  --policy POLICY
  --metadata METADATA
  --out OUT
```

## cvrs source-git

```text
usage: cvrs source-git [-h] {capture,materialize} ...

positional arguments:
  {capture,materialize}

options:
  -h, --help            show this help message and exit
```

## cvrs source-git capture

```text
usage: cvrs source-git capture [-h] --out OUT [--include-untracked] repo

positional arguments:
  repo

options:
  -h, --help           show this help message and exit
  --out OUT
  --include-untracked
```

## cvrs source-git materialize

```text
usage: cvrs source-git materialize [-h] --out OUT [--trust] capsule

positional arguments:
  capsule

options:
  -h, --help  show this help message and exit
  --out OUT
  --trust
```

## cvrs stack

```text
usage: cvrs stack [-h] {configure,doctor,execute,inspect} ...

positional arguments:
  {configure,doctor,execute,inspect}

options:
  -h, --help            show this help message and exit
```

## cvrs stack configure

```text
usage: cvrs stack configure [-h] [--out OUT] [--store STORE] [--spec SPEC]
                            [--plan PLAN] [--python PYTHON]
                            [--environment ENVIRONMENT] [--pack PACK]
                            [--operation OPERATION] [--actor ACTOR]
                            [--approval APPROVAL] [--approve APPROVE]
                            [--replacement REPLACEMENT]
                            [--worker-python WORKER_PYTHON] [--format FORMAT]
                            [--field FIELD] [--repository REPOSITORY]
                            [--version VERSION] [--previous PREVIOUS]
                            [--status STATUS] [--task TASK]
                            [--subject SUBJECT] [--evidence EVIDENCE]
                            [--reason REASON] [--files [FILES ...]] [--trust]
                            [--verify] [--apply] [--preview] [--force]
                            [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs stack doctor

```text
usage: cvrs stack doctor [-h] [--out OUT] [--store STORE] [--spec SPEC]
                         [--plan PLAN] [--python PYTHON]
                         [--environment ENVIRONMENT] [--pack PACK]
                         [--operation OPERATION] [--actor ACTOR]
                         [--approval APPROVAL] [--approve APPROVE]
                         [--replacement REPLACEMENT]
                         [--worker-python WORKER_PYTHON] [--format FORMAT]
                         [--field FIELD] [--repository REPOSITORY]
                         [--version VERSION] [--previous PREVIOUS]
                         [--status STATUS] [--task TASK] [--subject SUBJECT]
                         [--evidence EVIDENCE] [--reason REASON]
                         [--files [FILES ...]] [--trust] [--verify] [--apply]
                         [--preview] [--force]
                         [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs stack execute

```text
usage: cvrs stack execute [-h] [--out OUT] [--store STORE] [--spec SPEC]
                          [--plan PLAN] [--python PYTHON]
                          [--environment ENVIRONMENT] [--pack PACK]
                          [--operation OPERATION] [--actor ACTOR]
                          [--approval APPROVAL] [--approve APPROVE]
                          [--replacement REPLACEMENT]
                          [--worker-python WORKER_PYTHON] [--format FORMAT]
                          [--field FIELD] [--repository REPOSITORY]
                          [--version VERSION] [--previous PREVIOUS]
                          [--status STATUS] [--task TASK] [--subject SUBJECT]
                          [--evidence EVIDENCE] [--reason REASON]
                          [--files [FILES ...]] [--trust] [--verify] [--apply]
                          [--preview] [--force]
                          [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs stack inspect

```text
usage: cvrs stack inspect [-h] [--out OUT] [--store STORE] [--spec SPEC]
                          [--plan PLAN] [--python PYTHON]
                          [--environment ENVIRONMENT] [--pack PACK]
                          [--operation OPERATION] [--actor ACTOR]
                          [--approval APPROVAL] [--approve APPROVE]
                          [--replacement REPLACEMENT]
                          [--worker-python WORKER_PYTHON] [--format FORMAT]
                          [--field FIELD] [--repository REPOSITORY]
                          [--version VERSION] [--previous PREVIOUS]
                          [--status STATUS] [--task TASK] [--subject SUBJECT]
                          [--evidence EVIDENCE] [--reason REASON]
                          [--files [FILES ...]] [--trust] [--verify] [--apply]
                          [--preview] [--force]
                          [target] [other]

positional arguments:
  target
  other

options:
  -h, --help            show this help message and exit
  --out OUT
  --store STORE
  --spec SPEC
  --plan PLAN
  --python PYTHON
  --environment ENVIRONMENT
  --pack PACK
  --operation OPERATION
  --actor ACTOR
  --approval APPROVAL
  --approve APPROVE
  --replacement REPLACEMENT
  --worker-python WORKER_PYTHON
  --format FORMAT
  --field FIELD
  --repository REPOSITORY
  --version VERSION
  --previous PREVIOUS
  --status STATUS
  --task TASK
  --subject SUBJECT
  --evidence EVIDENCE
  --reason REASON
  --files [FILES ...]
  --trust
  --verify
  --apply
  --preview
  --force
```

## cvrs stack list

```text
usage: cvrs stack list [-h]

options:
  -h, --help  show this help message and exit
```

## cvrs stack run

```text
usage: cvrs stack run [-h] --out OUT [--python WORKER_PYTHON] [--trust]
                      [--timeout TIMEOUT]
                      family operation payload

positional arguments:
  family
  operation
  payload

options:
  -h, --help            show this help message and exit
  --out OUT
  --python WORKER_PYTHON
  --trust
  --timeout TIMEOUT
```

## cvrs stream

```text
usage: cvrs stream [-h] {plan,run} ...

positional arguments:
  {plan,run}

options:
  -h, --help  show this help message and exit
```

## cvrs stream plan

```text
usage: cvrs stream plan [-h] --width WIDTH --height HEIGHT [--first FIRST]
                        spec

positional arguments:
  spec

options:
  -h, --help       show this help message and exit
  --width WIDTH
  --height HEIGHT
  --first FIRST
```

## cvrs stream run

```text
usage: cvrs stream run [-h] --out OUT [--worker-python WORKER_PYTHON]
                       [--timeout TIMEOUT] [--resume]
                       [--stop-after-tiles STOP_AFTER_TILES]
                       spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
  --resume
  --stop-after-tiles STOP_AFTER_TILES
```

## cvrs support

```text
usage: cvrs support [-h] {bundle} ...

positional arguments:
  {bundle}

options:
  -h, --help  show this help message and exit
```

## cvrs support bundle

```text
usage: cvrs support bundle [-h] --out OUT run

positional arguments:
  run

options:
  -h, --help  show this help message and exit
  --out OUT
```

## cvrs synthetic

```text
usage: cvrs synthetic [-h] {ingest,validate-sample} ...

positional arguments:
  {ingest,validate-sample}

options:
  -h, --help            show this help message and exit
```

## cvrs synthetic ingest

```text
usage: cvrs synthetic ingest [-h] --mapping MAPPING --out OUT source

positional arguments:
  source

options:
  -h, --help         show this help message and exit
  --mapping MAPPING
  --out OUT
```

## cvrs synthetic map

```text
usage: cvrs synthetic map [-h] --mapping MAPPING --out OUT source

positional arguments:
  source

options:
  -h, --help         show this help message and exit
  --mapping MAPPING
  --out OUT
```

## cvrs synthetic migrate

```text
usage: cvrs synthetic migrate [-h] --sample-id SAMPLE_ID --out OUT source

positional arguments:
  source

options:
  -h, --help            show this help message and exit
  --sample-id SAMPLE_ID
  --out OUT
```

## cvrs synthetic validate

```text
usage: cvrs synthetic validate [-h] record

positional arguments:
  record

options:
  -h, --help  show this help message and exit
```

## cvrs synthetic validate-sample

```text
usage: cvrs synthetic validate-sample [-h] source

positional arguments:
  source

options:
  -h, --help  show this help message and exit
```

## cvrs telemetry

```text
usage: cvrs telemetry [-h] {inspect,aggregate} ...

positional arguments:
  {inspect,aggregate}

options:
  -h, --help           show this help message and exit
```

## cvrs telemetry aggregate

```text
usage: cvrs telemetry aggregate [-h] --expected-ranks EXPECTED_RANKS
                                ledgers [ledgers ...]

positional arguments:
  ledgers

options:
  -h, --help            show this help message and exit
  --expected-ranks EXPECTED_RANKS
```

## cvrs telemetry inspect

```text
usage: cvrs telemetry inspect [-h] ledger

positional arguments:
  ledger

options:
  -h, --help  show this help message and exit
```

## cvrs tiny-evaluate

```text
usage: cvrs tiny-evaluate [-h] --dataset DATASET [--split SPLIT]
                          [--policy POLICY] [--out OUT]
                          predictions

positional arguments:
  predictions

options:
  -h, --help         show this help message and exit
  --dataset DATASET
  --split SPLIT
  --policy POLICY
  --out OUT
```

## cvrs verify

```text
usage: cvrs verify [-h] [--dataset DATASET] run

positional arguments:
  run

options:
  -h, --help         show this help message and exit
  --dataset DATASET
```

## cvrs vision

```text
usage: cvrs vision [-h]
                   {run,evaluate-prompts,evaluate-masks,map-grounding,compare,transform-mask} ...

positional arguments:
  {run,evaluate-prompts,evaluate-masks,map-grounding,compare,transform-mask}

options:
  -h, --help            show this help message and exit
```

## cvrs vision compare

```text
usage: cvrs vision compare [-h] reports [reports ...]

positional arguments:
  reports

options:
  -h, --help  show this help message and exit
```

## cvrs vision evaluate-masks

```text
usage: cvrs vision evaluate-masks [-h] [--evaluator-python EVALUATOR_PYTHON]
                                  spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --evaluator-python EVALUATOR_PYTHON
```

## cvrs vision evaluate-prompts

```text
usage: cvrs vision evaluate-prompts [-h] spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
```

## cvrs vision map-grounding

```text
usage: cvrs vision map-grounding [-h] --mapping MAPPING predictions

positional arguments:
  predictions

options:
  -h, --help         show this help message and exit
  --mapping MAPPING
```

## cvrs vision run

```text
usage: cvrs vision run [-h] --out OUT [--worker-python WORKER_PYTHON]
                       [--timeout TIMEOUT]
                       spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --out OUT
  --worker-python WORKER_PYTHON
  --timeout TIMEOUT
```

## cvrs vision transform-mask

```text
usage: cvrs vision transform-mask [-h] --transform TRANSFORM mask

positional arguments:
  mask

options:
  -h, --help            show this help message and exit
  --transform TRANSFORM
```

## cvrs wrap-paper

```text
usage: cvrs wrap-paper [-h] --out OUT [--python PYTHON] [--commands COMMANDS]
                       [--purpose {research,software_fixture}]
                       repo

positional arguments:
  repo

options:
  -h, --help            show this help message and exit
  --out OUT
  --python PYTHON
  --commands COMMANDS   reviewed operation→argv/output mapping JSON
  --purpose {research,software_fixture}
```

## cvrs wrap-repo

```text
usage: cvrs wrap-repo [-h] --out OUT [--python PYTHON] [--commands COMMANDS]
                      [--purpose {research,software_fixture}]
                      repo

positional arguments:
  repo

options:
  -h, --help            show this help message and exit
  --out OUT
  --python PYTHON
  --commands COMMANDS   reviewed operation→argv/output mapping JSON
  --purpose {research,software_fixture}
```
