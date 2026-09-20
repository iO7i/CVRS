# New 0.5 CLI commands

## `cvrs`

```text
usage: cvrs [-h]
            {telemetry,stream,vision,quantize,detector-deploy,adapter-recipes,research-registry} ...

positional arguments:
  {telemetry,stream,vision,quantize,detector-deploy,adapter-recipes,research-registry}

options:
  -h, --help            show this help message and exit
```

## `cvrs telemetry`

```text
usage: cvrs telemetry [-h] {inspect,aggregate} ...

positional arguments:
  {inspect,aggregate}

options:
  -h, --help           show this help message and exit
```

## `cvrs telemetry inspect`

```text
usage: cvrs telemetry inspect [-h] ledger

positional arguments:
  ledger

options:
  -h, --help  show this help message and exit
```

## `cvrs telemetry aggregate`

```text
usage: cvrs telemetry aggregate [-h] --expected-ranks EXPECTED_RANKS
                                ledgers [ledgers ...]

positional arguments:
  ledgers

options:
  -h, --help            show this help message and exit
  --expected-ranks EXPECTED_RANKS
```

## `cvrs stream`

```text
usage: cvrs stream [-h] {plan,run} ...

positional arguments:
  {plan,run}

options:
  -h, --help  show this help message and exit
```

## `cvrs stream plan`

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

## `cvrs stream run`

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

## `cvrs vision`

```text
usage: cvrs vision [-h]
                   {run,evaluate-prompts,evaluate-masks,map-grounding,compare,transform-mask} ...

positional arguments:
  {run,evaluate-prompts,evaluate-masks,map-grounding,compare,transform-mask}

options:
  -h, --help            show this help message and exit
```

## `cvrs vision run`

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

## `cvrs vision evaluate-prompts`

```text
usage: cvrs vision evaluate-prompts [-h] spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
```

## `cvrs vision evaluate-masks`

```text
usage: cvrs vision evaluate-masks [-h] [--evaluator-python EVALUATOR_PYTHON]
                                  spec

positional arguments:
  spec

options:
  -h, --help            show this help message and exit
  --evaluator-python EVALUATOR_PYTHON
```

## `cvrs vision map-grounding`

```text
usage: cvrs vision map-grounding [-h] --mapping MAPPING predictions

positional arguments:
  predictions

options:
  -h, --help         show this help message and exit
  --mapping MAPPING
```

## `cvrs vision compare`

```text
usage: cvrs vision compare [-h] reports [reports ...]

positional arguments:
  reports

options:
  -h, --help  show this help message and exit
```

## `cvrs vision transform-mask`

```text
usage: cvrs vision transform-mask [-h] --transform TRANSFORM mask

positional arguments:
  mask

options:
  -h, --help            show this help message and exit
  --transform TRANSFORM
```

## `cvrs quantize`

```text
usage: cvrs quantize [-h] {validate,run,prepare,regression} ...

positional arguments:
  {validate,run,prepare,regression}

options:
  -h, --help            show this help message and exit
```

## `cvrs quantize validate`

```text
usage: cvrs quantize validate [-h] spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
```

## `cvrs quantize run`

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

## `cvrs quantize prepare`

```text
usage: cvrs quantize prepare [-h] --out OUT spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
  --out OUT
```

## `cvrs quantize regression`

```text
usage: cvrs quantize regression [-h] --limits LIMITS baseline quantized

positional arguments:
  baseline
  quantized

options:
  -h, --help       show this help message and exit
  --limits LIMITS
```

## `cvrs detector-deploy`

```text
usage: cvrs detector-deploy [-h] {profile,infer,export-mm} ...

positional arguments:
  {profile,infer,export-mm}

options:
  -h, --help            show this help message and exit
```

## `cvrs detector-deploy profile`

```text
usage: cvrs detector-deploy profile [-h] spec

positional arguments:
  spec

options:
  -h, --help  show this help message and exit
```

## `cvrs detector-deploy infer`

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

## `cvrs detector-deploy export-mm`

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

## `cvrs adapter-recipes`

```text
usage: cvrs adapter-recipes [-h] {list,show,scaffold} ...

positional arguments:
  {list,show,scaffold}

options:
  -h, --help            show this help message and exit
```

## `cvrs adapter-recipes list`

```text
usage: cvrs adapter-recipes list [-h]

options:
  -h, --help  show this help message and exit
```

## `cvrs adapter-recipes show`

```text
usage: cvrs adapter-recipes show [-h] name

positional arguments:
  name

options:
  -h, --help  show this help message and exit
```

## `cvrs adapter-recipes scaffold`

```text
usage: cvrs adapter-recipes scaffold [-h] out

positional arguments:
  out

options:
  -h, --help  show this help message and exit
```

## `cvrs research-registry`

```text
usage: cvrs research-registry [-h]
                              {init,verify,list,claim,attempt,review,evidence,status,supersede,export,import,capsule,restore,capture-run,reevaluate} ...

positional arguments:
  {init,verify,list,claim,attempt,review,evidence,status,supersede,export,import,capsule,restore,capture-run,reevaluate}

options:
  -h, --help            show this help message and exit
```

## `cvrs research-registry init`

```text
usage: cvrs research-registry init [-h] registry

positional arguments:
  registry

options:
  -h, --help  show this help message and exit
```

## `cvrs research-registry verify`

```text
usage: cvrs research-registry verify [-h] registry

positional arguments:
  registry

options:
  -h, --help  show this help message and exit
```

## `cvrs research-registry list`

```text
usage: cvrs research-registry list [-h] [--kind {claim,attempt,review}]
                                   registry

positional arguments:
  registry

options:
  -h, --help            show this help message and exit
  --kind {claim,attempt,review}
```

## `cvrs research-registry claim`

```text
usage: cvrs research-registry claim [-h] registry spec

positional arguments:
  registry
  spec

options:
  -h, --help  show this help message and exit
```

## `cvrs research-registry attempt`

```text
usage: cvrs research-registry attempt [-h] registry spec

positional arguments:
  registry
  spec

options:
  -h, --help  show this help message and exit
```

## `cvrs research-registry review`

```text
usage: cvrs research-registry review [-h] registry spec

positional arguments:
  registry
  spec

options:
  -h, --help  show this help message and exit
```

## `cvrs research-registry evidence`

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

## `cvrs research-registry status`

```text
usage: cvrs research-registry status [-h] registry claim_id

positional arguments:
  registry
  claim_id

options:
  -h, --help  show this help message and exit
```

## `cvrs research-registry supersede`

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

## `cvrs research-registry export`

```text
usage: cvrs research-registry export [-h] --out OUT registry

positional arguments:
  registry

options:
  -h, --help  show this help message and exit
  --out OUT
```

## `cvrs research-registry import`

```text
usage: cvrs research-registry import [-h] --out OUT snapshot

positional arguments:
  snapshot

options:
  -h, --help  show this help message and exit
  --out OUT
```

## `cvrs research-registry capsule`

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

## `cvrs research-registry restore`

```text
usage: cvrs research-registry restore [-h] --out OUT archive

positional arguments:
  archive

options:
  -h, --help  show this help message and exit
  --out OUT
```

## `cvrs research-registry capture-run`

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

## `cvrs research-registry reevaluate`

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
