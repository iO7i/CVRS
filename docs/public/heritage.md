# Preserve a working native repository

Do not rewrite a historical model merely to use CVRS. Preserve its interpreter, complete config closure and checkpoint; expose native predictions through an explicit adapter.

```bash
cvrs inspect-repo ../my-paper --out scan.json
cvrs wrap-repo ../my-paper --out wrapped --python ../old-env/bin/python
```

`scan.json` records literal observations with file/line evidence. README requirements and guessed entrypoints are candidates. Static analysis does not execute setup.py or evaluate Python configs. It cannot solve transitive dependencies or CUDA ABIs.

## Review the wrapper

Set argv tokens such as `${python}`, `${repo}`, `${output}` and `${inputs.checkpoint}`. Declare exact output paths relative to `${output}`. No shell interpolation, wildcard checkpoint selection, implicit trusted pickle loading or import-time execution occurs in the controller.

Both `trust_code: true` and `--trust` are required. The wrapper checks source identity before and after execution; generated outputs belong outside the native repository. A command that succeeds without its required outputs fails the wrapper.

## Native packs

MMDetection2/3 and OneDL keep their own loaders. MMRotate retains xywha-to-polygon semantics. MMSeg emits **semantic label maps**, not instances. Detectron2 uses DefaultPredictor's native BGR and resizing behavior; model-specific LazyConfig projects use the generic reviewed paper wrapper rather than an invented universal importer.

Use [pack schemas](packs.md). Native source revisions and config/checkpoint hashes must be supplied. A pack code path is not evidence that your version has executed.

## Configuration conflicts

```bash
cvrs env explain ../legacy ../modern
```

The report only proves contradictions present in declared constraints. NO_PROVEN_CONFLICTS is not installability. An embedded SAM component and its MMSeg parent may need the same environment; no tool can move the component out without preserving the actual model computation. Feature caching is allowed only across explicit detached/materialized boundaries.

## Exact source capture

`cvrs source-git capture` records a Git bundle, dirty patch and optional untracked files. `materialize --trust` reconstructs into a new checkout without touching the original or initializing submodules. Bundles contain history; review them for secrets before sharing.

## Input identity

Wrapped commands hash existing file inputs before execution and verify that their bytes did not change afterwards. Use `input_digests` to pin expected bytes before a run. Directory inputs require a content manifest; an unversioned directory is reported as partial input closure. Composed stages automatically pin the producer artifact hash. Arbitrary dependencies opened inside native code cannot be inferred from argv alone.
