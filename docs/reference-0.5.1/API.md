# Public API inventory

Stable finite imports: `cvsubstrate.v1`. Native driver internals remain provisional.

## `cvsubstrate.contracts.models`

### `relative_path`

Portable relative POSIX paths only; traversal is always rejected.

### `Contract`

See the implementation and declared contract.

### `LicenseInfo`

See the implementation and declared contract.

### `Category`

See the implementation and declared contract.

### `Box`

See the implementation and declared contract.

### `GenerationMetadata`

See the implementation and declared contract.

### `Sample`

See the implementation and declared contract.

### `Split`

See the implementation and declared contract.

### `DatasetManifest`

See the implementation and declared contract.

### `DetectionPrediction`

See the implementation and declared contract.

### `EvaluationProtocol`

See the implementation and declared contract.

### `AdapterSpec`

See the implementation and declared contract.

### `CheckpointRef`

See the implementation and declared contract.

### `TrainingSpec`

See the implementation and declared contract.

### `ExperimentSpec`

See the implementation and declared contract.

### `FinalTestAuthorization`

See the implementation and declared contract.

### `TrainingTrace`

See the implementation and declared contract.

### `AdapterCapabilities`

See the implementation and declared contract.

### `WorkerRequest`

See the implementation and declared contract.

### `WorkerResponse`

See the implementation and declared contract.

### `RunManifest`

See the implementation and declared contract.

### `LegacyExperimentRef`

See the implementation and declared contract.

### `EnvironmentCapsule`

See the implementation and declared contract.

### `HeritageCertification`

See the implementation and declared contract.

### `ArtifactEntry`

See the implementation and declared contract.

### `ArtifactManifest`

See the implementation and declared contract.

## `cvsubstrate.contracts.research`

### `Quantity`

See the implementation and declared contract.

### `CameraRecord`

See the implementation and declared contract.

### `SyntheticObject`

See the implementation and declared contract.

### `SyntheticRecord`

See the implementation and declared contract.

### `FieldMapping`

See the implementation and declared contract.

### `SidecarMapping`

See the implementation and declared contract.

### `GeoReference`

See the implementation and declared contract.

### `TilingPolicy`

See the implementation and declared contract.

### `OrientedAnnotation`

See the implementation and declared contract.

### `OrientedSample`

See the implementation and declared contract.

### `OrientedDataset`

See the implementation and declared contract.

### `OrientedPrediction`

See the implementation and declared contract.

### `TinyEvaluationPolicy`

See the implementation and declared contract.

### `BackendTemplate`

See the implementation and declared contract.

### `CampaignSpec`

See the implementation and declared contract.

### `AccessApproval`

See the implementation and declared contract.

## `cvsubstrate.contracts.groundwork`

### `ArtifactRef`

See the implementation and declared contract.

### `ArtifactEnvelope`

See the implementation and declared contract.

### `PluginDescriptor`

See the implementation and declared contract.

### `CapabilityRequirement`

See the implementation and declared contract.

### `EnvironmentManifest`

See the implementation and declared contract.

### `ExecutionEvent`

See the implementation and declared contract.

### `InputReference`

See the implementation and declared contract.

### `ExecutionNode`

See the implementation and declared contract.

### `ExecutionGraph`

See the implementation and declared contract.

### `CheckpointDescriptor`

See the implementation and declared contract.

### `CheckpointConversionSpec`

See the implementation and declared contract.

### `ObjectSizePolicy`

See the implementation and declared contract.

### `SliceExpression`

See the implementation and declared contract.

### `MergePolicy`

See the implementation and declared contract.

### `LargeImagePlan`

See the implementation and declared contract.

### `GeoDatasetManifest`

See the implementation and declared contract.

### `StageSpec`

See the implementation and declared contract.

### `ArmSpec`

See the implementation and declared contract.

### `BudgetConstraint`

See the implementation and declared contract.

### `ResearchCampaign`

See the implementation and declared contract.

### `BenchmarkSpec`

See the implementation and declared contract.

### `BackboneDescriptor`

See the implementation and declared contract.

### `DeploymentSpec`

See the implementation and declared contract.

## `cvsubstrate.contracts.synthetic`

### `Observation`

See the implementation and declared contract.

### `SyntheticSampleManifest`

See the implementation and declared contract.

## `cvsubstrate.adapters.sdk`

### `ModelAdapter`

See the implementation and declared contract.

### `DatasetAdapter`

See the implementation and declared contract.

### `EvaluatorAdapter`

See the implementation and declared contract.

### `ExporterAdapter`

See the implementation and declared contract.

### `SimulatorMetadataAdapter`

See the implementation and declared contract.

### `BackboneAdapter`

See the implementation and declared contract.

### `PluginRegistry`

See the implementation and declared contract.

### `negotiate`

See the implementation and declared contract.

### `validate_plugin`

See the implementation and declared contract.

### `scaffold`

See the implementation and declared contract.

### `ManagedAdapter`

See the implementation and declared contract.

## `cvsubstrate.adapters.conformance`

### `execute_plugin`

See the implementation and declared contract.

### `conformance`

See the implementation and declared contract.

## `cvsubstrate.artifacts.store`

### `ArtifactStore`

See the implementation and declared contract.

### `LocalArtifactStore`

See the implementation and declared contract.

### `ActionCache`

See the implementation and declared contract.

## `cvsubstrate.artifacts.capsule`

### `create_capsule`

See the implementation and declared contract.

### `validate_capsule`

See the implementation and declared contract.

### `archive_capsule`

See the implementation and declared contract.

### `materialize_capsule`

See the implementation and declared contract.

## `cvsubstrate.schemas.registry`

### `schema_registry`

See the implementation and declared contract.

### `inspect_schema`

See the implementation and declared contract.

### `validate_artifact`

See the implementation and declared contract.

### `MigrationRegistry`

See the implementation and declared contract.

### `registry`

See the implementation and declared contract.

### `migrate_artifact`

See the implementation and declared contract.

### `migrate_run`

See the implementation and declared contract.

### `export_schemas`

See the implementation and declared contract.

## `cvsubstrate.experiments.dag`

### `Action`

See the implementation and declared contract.

### `register_action`

See the implementation and declared contract.

### `implementation_identity`

See the implementation and declared contract.

### `topological`

See the implementation and declared contract.

### `execute_graph`

See the implementation and declared contract.

## `cvsubstrate.campaigns.dsl`

### `planned_budgets`

See the implementation and declared contract.

### `check_budgets`

See the implementation and declared contract.

### `compile_campaign`

See the implementation and declared contract.

### `execute_research_campaign`

See the implementation and declared contract.

### `set_pointer`

See the implementation and declared contract.

### `expand_sweep`

See the implementation and declared contract.

### `measured_budget_checks`

See the implementation and declared contract.

## `cvsubstrate.benchmarks.registry`

### `register_benchmark`

See the implementation and declared contract.

### `list_benchmarks`

See the implementation and declared contract.

### `preregister_selection`

See the implementation and declared contract.

### `authorize_final`

See the implementation and declared contract.

### `final_evaluate`

See the implementation and declared contract.

### `validate_submission`

See the implementation and declared contract.

## `cvsubstrate.evaluation.converters`

### `PredictionConverterRegistry`

See the implementation and declared contract.

### `registry`

See the implementation and declared contract.

### `convert_results`

See the implementation and declared contract.

## `cvsubstrate.geometry.merge`

### `box_iou`

See the implementation and declared contract.

### `merge_detections`

See the implementation and declared contract.

## `cvsubstrate.datasets.importers`

### `import_dataset`

See the implementation and declared contract.

## `cvsubstrate.backbones.service`

### `extract_features`

See the implementation and declared contract.

## `cvsubstrate.deployment.service`

### `execute_deployment`

See the implementation and declared contract.

## `cvsubstrate.contracts.frontier`

### `PromptSpec`

See the implementation and declared contract.

### `GroundedPrediction`

See the implementation and declared contract.

### `MaskRLE`

Uncompressed COCO-column-major binary RLE, initial run always background.

### `MaskInstance`

See the implementation and declared contract.

### `MaskPrediction`

See the implementation and declared contract.

### `MaskAnnotation`

See the implementation and declared contract.

### `VisionJob`

See the implementation and declared contract.

### `MaskEvaluationProtocol`

See the implementation and declared contract.

### `CalibrationItem`

See the implementation and declared contract.

### `QuantizationSpec`

See the implementation and declared contract.

### `ClaimSpec`

See the implementation and declared contract.

### `ReproductionAttempt`

See the implementation and declared contract.

### `IndependenceReview`

See the implementation and declared contract.

## `cvsubstrate.telemetry`

### `summarize_telemetry`

See the implementation and declared contract.

### `aggregate_telemetry`

See the implementation and declared contract.

## `cvsubstrate.streaming.raster`

### `StreamSpec`

See the implementation and declared contract.

### `Tile`

See the implementation and declared contract.

### `RasterSource`

See the implementation and declared contract.

### `Predictor`

See the implementation and declared contract.

### `plan_tiles`

Lazy multiscale windows: fractional source offsets preserve exact inversion.

### `PredictionDatabase`

See the implementation and declared contract.

### `execute_stream`

See the implementation and declared contract.

## `cvsubstrate.streaming.service`

### `stream_job`

See the implementation and declared contract.

## `cvsubstrate.vision.masks`

### `encode_mask`

See the implementation and declared contract.

### `decode_mask`

See the implementation and declared contract.

### `mask_area`

See the implementation and declared contract.

### `mask_intersection`

See the implementation and declared contract.

### `mask_iou`

See the implementation and declared contract.

### `transform_mask`

See the implementation and declared contract.

### `paste_mask`

See the implementation and declared contract.

### `merge_mask_tiles`

Union only for explicitly same tracked instance ID; do not merge all objects.

### `evaluate_prompt_masks`

Pairs specify prompt -> target *before* evaluation. Never pick by GT IoU.

## `cvsubstrate.vision.grounding`

### `map_grounded`

See the implementation and declared contract.

### `cross_paradigm_report`

See the implementation and declared contract.

## `cvsubstrate.vision.evaluation`

### `mask_reference_payload`

See the implementation and declared contract.

### `evaluate_masks`

See the implementation and declared contract.

## `cvsubstrate.vision.service`

### `vision_job`

See the implementation and declared contract.

## `cvsubstrate.adapters.recipes`

### `recipes`

See the implementation and declared contract.

### `recipe`

See the implementation and declared contract.

### `scaffold_vision_adapter`

External plugin delegates to actual optional native vision APIs, not mock outputs.

## `cvsubstrate.deployment.profiles`

### `DetectorProfile`

See the implementation and declared contract.

### `preprocess_image`

See the implementation and declared contract.

### `decode_outputs`

See the implementation and declared contract.

## `cvsubstrate.deployment.calibration`

### `prepare_calibration`

See the implementation and declared contract.

### `accuracy_regression`

See the implementation and declared contract.

## `cvsubstrate.deployment.quantization`

### `validate_calibration`

See the implementation and declared contract.

### `quantize`

See the implementation and declared contract.

## `cvsubstrate.research.registry`

### `ResearchRegistry`

See the implementation and declared contract.

### `import_snapshot`

See the implementation and declared contract.

## `cvsubstrate.research.capture`

### `capture_run`

See the implementation and declared contract.

## `cvsubstrate.research.reevaluate`

### `reevaluate`

See the implementation and declared contract.

## `cvsubstrate.research.capsule`

### `export_registry_capsule`

See the implementation and declared contract.

### `import_registry_capsule`

See the implementation and declared contract.

## `cvsubstrate.foundation.identity`

### `content_id`

See the implementation and declared contract.

### `ProvenanceNode`

See the implementation and declared contract.

### `ProvenanceEdge`

See the implementation and declared contract.

### `ProvenanceGraph`

See the implementation and declared contract.

## `cvsubstrate.foundation.lifecycle`

### `transition`

See the implementation and declared contract.

### `Cancelled`

See the implementation and declared contract.

### `CancellationToken`

See the implementation and declared contract.

### `process_lock`

Cooperative advisory lock released by the OS on crash, POSIX/Windows.

Lock files are deliberately not unlinked: unlinking a held lock permits
another inode to bypass it. This does not protect against hostile writers.

### `retry_allowed`

See the implementation and declared contract.

### `cancellation_scope`

See the implementation and declared contract.

## `cvsubstrate.foundation.policy`

## `cvsubstrate.foundation.compatibility`

### `inspect_compatibility`

See the implementation and declared contract.

## `cvsubstrate.artifacts.managed`

### `ManagedArtifactStore`

See the implementation and declared contract.

## `cvsubstrate.artifacts.dependencies`

### `Dependency`

See the implementation and declared contract.

### `DependencyClosure`

See the implementation and declared contract.

### `inspect_closure`

See the implementation and declared contract.

## `cvsubstrate.execution.session`

### `run_session`

See the implementation and declared contract.

### `legacy_handler`

Session-2 envelope around an existing *real* protocol-1 native worker.

## `cvsubstrate.heritage.closure`

### `config_closure`

See the implementation and declared contract.

### `preserve_closure`

See the implementation and declared contract.

## `cvsubstrate.heritage.native_data`

### `bind_coco_training`

See the implementation and declared contract.

## `cvsubstrate.heritage.checkpoint_v1`

### `diff_checkpoints`

See the implementation and declared contract.

### `transform_checkpoint`

See the implementation and declared contract.

## `cvsubstrate.heritage.model_index`

### `ingest_model_index`

See the implementation and declared contract.

## `cvsubstrate.campaigns.native`

### `NativeStage`

See the implementation and declared contract.

### `NativeCampaign`

See the implementation and declared contract.

### `compile_native_campaign`

See the implementation and declared contract.

### `run_native_campaign`

See the implementation and declared contract.

## `cvsubstrate.datasets.sensors`

### `BandSpec`

See the implementation and declared contract.

### `SensorSpec`

See the implementation and declared contract.

### `GeoSceneSpec`

See the implementation and declared contract.

### `normalize_bands`

See the implementation and declared contract.

## `cvsubstrate.data.asset_lineage`

### `SourceAsset`

See the implementation and declared contract.

### `SampleLineage`

See the implementation and declared contract.

### `AssetLineage`

See the implementation and declared contract.

### `check_asset_leakage`

See the implementation and declared contract.

## `cvsubstrate.streaming.tasks`

### `SpatialPredictionIndex`

See the implementation and declared contract.

### `ResourceBudget`

See the implementation and declared contract.

### `canonical_rows`

See the implementation and declared contract.

### `execute_task_stream`

See the implementation and declared contract.

## `cvsubstrate.vision.prompts`

### `ReferenceAsset`

See the implementation and declared contract.

### `PromptAtom`

See the implementation and declared contract.

### `PromptSet`

See the implementation and declared contract.

### `register_prompt_backend`

See the implementation and declared contract.

### `native_prompt_groups`

See the implementation and declared contract.

### `negotiate_prompts`

See the implementation and declared contract.

### `legacy_prompts`

Loss-audited lowering to native point/box/text/mask requests.

### `validate_trajectory`

See the implementation and declared contract.

## `cvsubstrate.vision.trajectories`

### `execute_trajectory`

See the implementation and declared contract.

### `continue_prompt_step`

Bind a user correction to observed previous hashes, never an invented output.

## `cvsubstrate.vision.ontology`

### `Concept`

See the implementation and declared contract.

### `ConceptOntology`

See the implementation and declared contract.

### `iou`

See the implementation and declared contract.

### `evaluate_open_set`

See the implementation and declared contract.

### `canonical_grounding_rows`

Convert native canonical per-image grounding to audited evaluation records.

## `cvsubstrate.vision.assets`

### `VisionAsset`

See the implementation and declared contract.

### `VisionModelDescriptor`

See the implementation and declared contract.

### `inspect_assets`

See the implementation and declared contract.

## `cvsubstrate.vision.diagnostics`

### `mask_diagnostics`

See the implementation and declared contract.

### `compare_paradigms`

See the implementation and declared contract.

## `cvsubstrate.research.claims`

### `ActorIdentity`

See the implementation and declared contract.

### `ScientificClaim`

See the implementation and declared contract.

### `EffectObservation`

See the implementation and declared contract.

### `EvidenceAttempt`

See the implementation and declared contract.

### `IndependenceAttestation`

See the implementation and declared contract.

### `EvidenceEdge`

See the implementation and declared contract.

## `cvsubstrate.research.federated`

### `FederatedRegistry`

See the implementation and declared contract.

### `migrate_registry_v1`

Lossless legacy records/history capture; never invent structured claim semantics.

## `cvsubstrate.research.capture_v2`

### `capture_comparison`

See the implementation and declared contract.

### `capture_run_lineage`

Preserve reusable outputs and explicit external checkpoint descriptors.

Images and checkpoint bytes are not copied by default. A descriptor records
their declared content identity and makes their external status explicit.

## `cvsubstrate.research.evaluators`

### `reevaluate_task`

See the implementation and declared contract.

### `register_evaluation`

See the implementation and declared contract.

## `cvsubstrate.research.signing`

### `keygen`

See the implementation and declared contract.

### `sign_payload`

See the implementation and declared contract.

### `verify_signature`

See the implementation and declared contract.

## `cvsubstrate.research.task_access`

### `task_evaluation_identity`

See the implementation and declared contract.

### `authorize_task_evaluation`

See the implementation and declared contract.

### `consume_task_authorization`

See the implementation and declared contract.
