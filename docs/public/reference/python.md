# Python adoption API

These are local alpha adoption APIs. The existing `cvsubstrate.v1` facade retains its separate compatibility promise.

## cvsubstrate.adoption.api

### `Experiment`

See the typed implementation and matching command contract.

### `Run`

See the typed implementation and matching command contract.

## cvsubstrate.adoption.inspect

### `git_state(root)`

See the typed implementation and matching command contract.

### `inspect_repository(root, max_files=8000, max_bytes=48 * 1024 * 1024)`

See the typed implementation and matching command contract.

## cvsubstrate.adoption.wrapping

### `wrap_repository(repo, destination, *, python=None, commands=None, purpose='research')`

See the typed implementation and matching command contract.

### `validate_paper(spec_path)`

See the typed implementation and matching command contract.

### `run_paper(spec_path, operation, destination, *, trust=False, cancel_token=None)`

See the typed implementation and matching command contract.

## cvsubstrate.adoption.composition

### `check_port(artifact, port)`

See the typed implementation and matching command contract.

### `inspect_artifact(value, root)`

See the typed implementation and matching command contract.

### `compile_composition(spec)`

See the typed implementation and matching command contract.

### `run_composition(spec, root, *, trust=False)`

See the typed implementation and matching command contract.

## cvsubstrate.adoption.recipes

### `recipe_list()`

See the typed implementation and matching command contract.

### `recipe_inspect(name)`

See the typed implementation and matching command contract.

### `materialize_recipe(name, destination)`

See the typed implementation and matching command contract.

### `asset_status(recipe_path, bindings_path)`

See the typed implementation and matching command contract.

## cvsubstrate.adoption.environments

### `list_packs()`

See the typed implementation and matching command contract.

### `scaffold_environment(pack, destination, *, pins=None, python_version=None, base_image=None)`

See the typed implementation and matching command contract.

### `doctor(python=None)`

See the typed implementation and matching command contract.

### `hpc_script(spec_path, destination, *, scheduler='slurm', cpus=4, memory_gb=16, gpus=0, walltime='01:00:00', python='python', container=None)`

See the typed implementation and matching command contract.

## cvsubstrate.adoption.assets

### `AssetManager`

See the typed implementation and matching command contract.

### `hf_inspect(repo_id, revision='main', *, allow_network=False, repo_type='model')`

See the typed implementation and matching command contract.

### `lock_local_assets(root, *, provider='local', repo_id=None, revision=None)`

See the typed implementation and matching command contract.

## cvsubstrate.adoption.methodology

### `evaluation_equivalence(a, b)`

See the typed implementation and matching command contract.

### `lint_methodology(value)`

See the typed implementation and matching command contract.

### `experiment_diff(a, b)`

See the typed implementation and matching command contract.

### `reviewer_report(root)`

See the typed implementation and matching command contract.

## cvsubstrate.adoption.gallery

### `run_example(name, out, *, repo=None, left=None, right=None, job=None, execute=False, worker_python=None)`

See the typed implementation and matching command contract.

### `main(name, argv=None)`

See the typed implementation and matching command contract.

## cvsubstrate.bridges.service

### `bridge_catalogue()`

See the typed implementation and matching command contract.

### `run_bridge(value)`

See the typed implementation and matching command contract.

## cvsubstrate.bridges.interchange

### `detection_bundle(manifest, predictions, root)`

See the typed implementation and matching command contract.

### `supervision_roundtrip(bundle)`

In-process public API for users already running Supervision.

### `from_supervision(detections, *, sample_id, width, height)`

See the typed implementation and matching command contract.

## cvsubstrate.bridges.exports

### `export_codeocean(capsule, destination, *, argv, environment=None)`

See the typed implementation and matching command contract.

### `export_benchmark(spec, destination)`

See the typed implementation and matching command contract.

### `export_reproduction(run, destination)`

Export exact expected output and an executable, asset-gated rerun project.

## cvsubstrate.bridges.semantic

### `semantic_metrics(pairs, num_classes, ignore_index=255, reduce_zero_label=False)`

See the typed implementation and matching command contract.

## cvsubstrate.publication.audit

### `settings(root)`

See the typed implementation and matching command contract.

### `audit_public(root, *, require_identity=True, max_file_bytes=2 * 1024 * 1024)`

See the typed implementation and matching command contract.

### `public_tree(source, destination, *, preview=False)`

See the typed implementation and matching command contract.

## cvsubstrate.publication.build

### `deterministic_zip(source, archive, *, prefix=None)`

See the typed implementation and matching command contract.

### `publish_bundle(source, destination, *, preview=False, build_packages=True)`

See the typed implementation and matching command contract.

## cvsubstrate.publication.site

### `page(title, body, nav='')`

See the typed implementation and matching command contract.

### `markdown(text)`

See the typed implementation and matching command contract.

### `build_docs(source, destination)`

See the typed implementation and matching command contract.

### `link_check(site)`

See the typed implementation and matching command contract.

### `results_site(runs, destination)`

See the typed implementation and matching command contract.

### `graph_site(spec, destination)`

See the typed implementation and matching command contract.

### `visual_diff(image, left, right, destination, *, allow_image_copy=False)`

See the typed implementation and matching command contract.

## cvsubstrate.publication.metadata

### `validate_settings(settings)`

See the typed implementation and matching command contract.

### `configure(root, settings, *, license_text=None)`

See the typed implementation and matching command contract.

### `derive_identity(source, destination, settings, *, license_text=None)`

See the typed implementation and matching command contract.

## cvsubstrate.publication.compatibility

### `inventory(path)`

See the typed implementation and matching command contract.

### `compare_compatibility(old, new)`

See the typed implementation and matching command contract.

## cvsubstrate.product.environments

### `probe(interpreter: str, modules: list[str], *, timeout: float=40)`

See the typed implementation and matching command contract.

### `observation_diff(expected: ManagedEnvironmentSpec, observed: dict)`

See the typed implementation and matching command contract.

### `EnvironmentManager`

Manage only prefixes below a caller-selected owned store.

## cvsubstrate.product.stacks

### `inspect_pack(name: str)`

See the typed implementation and matching command contract.

### `list_packs()`

See the typed implementation and matching command contract.

### `diagnose(observation: dict, pack: str, error_text: str='')`

See the typed implementation and matching command contract.

### `configure_pack(pack: str, destination: Path, *, python: str | None=None, store: Path | None=None, environment: str | None=None, payload: dict | None=None)`

See the typed implementation and matching command contract.

### `workspace_doctor(workspace: Path)`

See the typed implementation and matching command contract.

### `run_workspace(workspace: Path, operation: str, destination: Path, *, trust: bool=False)`

See the typed implementation and matching command contract.

## cvsubstrate.product.onboarding

### `prepare_paper(repo: Path, destination: Path, *, python: str | None=None, store: Path | None=None, environment: str | None=None, decisions: dict | None=None)`

Write explicit decisions, source evidence and unresolved prerequisites.

A scanner's `train.py` candidate is never promoted into an approved command.
`decisions` supplies exact argv, outputs, input bindings and operation names.

### `readiness(spec_path: Path)`

See the typed implementation and matching command contract.

### `approve_paper(spec_path: Path, actor: str, destination: Path)`

See the typed implementation and matching command contract.

### `execute_approved(spec_path: Path, approval_path: Path, operation: str, destination: Path, *, trust: bool=False)`

See the typed implementation and matching command contract.

## cvsubstrate.product.methodology

### `review_methodology(value: dict[str, Any])`

See the typed implementation and matching command contract.

### `review_report(value: dict)`

See the typed implementation and matching command contract.

## cvsubstrate.product.interchange

### `RichObject`

See the typed implementation and matching command contract.

### `RichFrame`

See the typed implementation and matching command contract.

### `RichInterchange`

See the typed implementation and matching command contract.

### `to_supervision_payload(value: dict | RichInterchange, *, max_mask_pixels: int=64 * 1024 * 1024)`

See the typed implementation and matching command contract.

### `from_supervision_payload(payload: dict, *, max_mask_pixels: int=64 * 1024 * 1024)`

See the typed implementation and matching command contract.

### `to_fiftyone_payload(value: dict | RichInterchange, *, max_mask_pixels: int=64 * 1024 * 1024)`

See the typed implementation and matching command contract.

### `from_fiftyone_payload(payload: dict, *, max_mask_pixels: int=64 * 1024 * 1024)`

See the typed implementation and matching command contract.

### `audit_roundtrip(original: dict | RichInterchange, restored: dict | RichInterchange, *, coordinate_tolerance=1e-09)`

Compare by stable object IDs, including pixels/phrases and metadata.

### `exchange(value: dict, target: str, direction: str)`

See the typed implementation and matching command contract.

## cvsubstrate.product.bridges

### `native_exchange(value: dict, target: str, destination: Path, *, worker_python: str | None=None, trust: bool=False, timeout: float=600)`

Export and read back a genuine SDK representation in a selected worker.

### `import_fiftyone_dataset(name: str, destination: Path, *, worker_python: str | None=None, trust=False)`

See the typed implementation and matching command contract.

### `decode_arrays(path: Path, spec: dict, destination: Path)`

Decode a declared TerraTorch/custom NPZ boundary without heuristic guessing.

Supported: NHW semantic maps, NCHW class logits (explicit argmax), and
detection arrays boxes[N,K,4], scores[N,K], labels[N,K], optional counts[N].
All arrays are loaded with allow_pickle=False and a byte budget.

### `tracking_handoff(run: Path, destination: Path, *, approved_files: list[str] | None=None)`

Retain CVRS evidence semantics when exporting into W&B/MLflow.

No upload occurs. Media/weights are excluded unless individually approved.

## cvsubstrate.product.recipes

### `check_recipe(value: dict, *, contributor: bool=False)`

See the typed implementation and matching command contract.

### `search_recipes(query='', *, framework=None, task=None)`

See the typed implementation and matching command contract.

### `contribute_recipe(path: Path, destination: Path)`

See the typed implementation and matching command contract.

### `recipe_index(destination: Path)`

See the typed implementation and matching command contract.

## cvsubstrate.product.browser

### `collect_catalog(source: Path, *, verify=False, max_records=5000)`

See the typed implementation and matching command contract.

### `render_browser(catalog: dict, destination: Path)`

See the typed implementation and matching command contract.

### `build_browser(source: Path, destination: Path, *, verify=False)`

See the typed implementation and matching command contract.

### `build_portal(source: Path, destination: Path)`

Versioned, offline searchable documentation over the existing renderer.

### `versioned_portal(portals: list[Path], destination: Path)`

Assemble already-generated versions without rebuilding or relabeling them.

Each input must declare its own current version in versions.json. Only static
site files are copied, with per-file hashes in the output catalogue. This
does not download past releases or claim those releases were reproduced.

## cvsubstrate.product.compatibility

### `make_receipt(descriptor: dict, evidence: Path | None=None)`

See the typed implementation and matching command contract.

### `render_badge(value: dict, destination: Path)`

See the typed implementation and matching command contract.

### `freeze_api(root: Path, destination: Path)`

See the typed implementation and matching command contract.

### `compare_api(previous: dict, current: dict)`

See the typed implementation and matching command contract.

## cvsubstrate.product.launch

### `preflight(root: Path, *, require_clean=False)`

See the typed implementation and matching command contract.

### `action_lock()`

See the typed implementation and matching command contract.

### `workflow_documents()`

Build jobs have no signing/publishing tokens. Privileged jobs consume files.

### `generate_workflows(root: Path, destination: Path)`

See the typed implementation and matching command contract.

### `launch_plan(root: Path)`

See the typed implementation and matching command contract.

### `security_plan(repository: str, *, required_checks=None, branch='main', approving_reviews=0, observed_state=None)`

See the typed implementation and matching command contract.

### `security_readback_matches(operation: dict, observation: dict)`

Check requested enablement fields, not merely an HTTP success status.

### `apply_security_plan(plan: dict, *, approve_digest: str, allow_network: bool, destination: Path)`

See the typed implementation and matching command contract.

### `verify_artifacts(manifest_path: Path)`

Verify wheel/sdist identity and contents without importing or extracting code.

### `contribution_check(root: Path)`

See the typed implementation and matching command contract.
