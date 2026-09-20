# Public API inventory

The 0.x API is provisional; serialized original 1.0 contracts retain strict readers.

## `cvsubstrate.contracts.models`

### `relative_path`

Portable relative POSIX paths only; traversal is always rejected.

### `Contract`

See the typed implementation and operation contract.

### `LicenseInfo`

See the typed implementation and operation contract.

### `Category`

See the typed implementation and operation contract.

### `Box`

See the typed implementation and operation contract.

### `GenerationMetadata`

See the typed implementation and operation contract.

### `Sample`

See the typed implementation and operation contract.

### `Split`

See the typed implementation and operation contract.

### `DatasetManifest`

See the typed implementation and operation contract.

### `DetectionPrediction`

See the typed implementation and operation contract.

### `EvaluationProtocol`

See the typed implementation and operation contract.

### `AdapterSpec`

See the typed implementation and operation contract.

### `CheckpointRef`

See the typed implementation and operation contract.

### `TrainingSpec`

See the typed implementation and operation contract.

### `ExperimentSpec`

See the typed implementation and operation contract.

### `FinalTestAuthorization`

See the typed implementation and operation contract.

### `TrainingTrace`

See the typed implementation and operation contract.

### `AdapterCapabilities`

See the typed implementation and operation contract.

### `WorkerRequest`

See the typed implementation and operation contract.

### `WorkerResponse`

See the typed implementation and operation contract.

### `RunManifest`

See the typed implementation and operation contract.

### `LegacyExperimentRef`

See the typed implementation and operation contract.

### `EnvironmentCapsule`

See the typed implementation and operation contract.

### `HeritageCertification`

See the typed implementation and operation contract.

### `ArtifactEntry`

See the typed implementation and operation contract.

### `ArtifactManifest`

See the typed implementation and operation contract.

## `cvsubstrate.contracts.research`

### `Quantity`

See the typed implementation and operation contract.

### `CameraRecord`

See the typed implementation and operation contract.

### `SyntheticObject`

See the typed implementation and operation contract.

### `SyntheticRecord`

See the typed implementation and operation contract.

### `FieldMapping`

See the typed implementation and operation contract.

### `SidecarMapping`

See the typed implementation and operation contract.

### `GeoReference`

See the typed implementation and operation contract.

### `TilingPolicy`

See the typed implementation and operation contract.

### `OrientedAnnotation`

See the typed implementation and operation contract.

### `OrientedSample`

See the typed implementation and operation contract.

### `OrientedDataset`

See the typed implementation and operation contract.

### `OrientedPrediction`

See the typed implementation and operation contract.

### `TinyEvaluationPolicy`

See the typed implementation and operation contract.

### `BackendTemplate`

See the typed implementation and operation contract.

### `CampaignSpec`

See the typed implementation and operation contract.

### `AccessApproval`

See the typed implementation and operation contract.

## `cvsubstrate.contracts.groundwork`

### `ArtifactRef`

See the typed implementation and operation contract.

### `ArtifactEnvelope`

See the typed implementation and operation contract.

### `PluginDescriptor`

See the typed implementation and operation contract.

### `CapabilityRequirement`

See the typed implementation and operation contract.

### `EnvironmentManifest`

See the typed implementation and operation contract.

### `ExecutionEvent`

See the typed implementation and operation contract.

### `InputReference`

See the typed implementation and operation contract.

### `ExecutionNode`

See the typed implementation and operation contract.

### `ExecutionGraph`

See the typed implementation and operation contract.

### `CheckpointDescriptor`

See the typed implementation and operation contract.

### `CheckpointConversionSpec`

See the typed implementation and operation contract.

### `ObjectSizePolicy`

See the typed implementation and operation contract.

### `SliceExpression`

See the typed implementation and operation contract.

### `MergePolicy`

See the typed implementation and operation contract.

### `LargeImagePlan`

See the typed implementation and operation contract.

### `GeoDatasetManifest`

See the typed implementation and operation contract.

### `StageSpec`

See the typed implementation and operation contract.

### `ArmSpec`

See the typed implementation and operation contract.

### `BudgetConstraint`

See the typed implementation and operation contract.

### `ResearchCampaign`

See the typed implementation and operation contract.

### `BenchmarkSpec`

See the typed implementation and operation contract.

### `BackboneDescriptor`

See the typed implementation and operation contract.

### `DeploymentSpec`

See the typed implementation and operation contract.

## `cvsubstrate.contracts.synthetic`

### `Observation`

See the typed implementation and operation contract.

### `SyntheticSampleManifest`

See the typed implementation and operation contract.

## `cvsubstrate.adapters.sdk`

### `ModelAdapter`

See the typed implementation and operation contract.

### `DatasetAdapter`

See the typed implementation and operation contract.

### `EvaluatorAdapter`

See the typed implementation and operation contract.

### `ExporterAdapter`

See the typed implementation and operation contract.

### `SimulatorMetadataAdapter`

See the typed implementation and operation contract.

### `BackboneAdapter`

See the typed implementation and operation contract.

### `PluginRegistry`

See the typed implementation and operation contract.

### `negotiate`

See the typed implementation and operation contract.

### `validate_plugin`

See the typed implementation and operation contract.

### `scaffold`

See the typed implementation and operation contract.

### `ManagedAdapter`

See the typed implementation and operation contract.

## `cvsubstrate.adapters.conformance`

### `execute_plugin`

See the typed implementation and operation contract.

### `conformance`

See the typed implementation and operation contract.

## `cvsubstrate.artifacts.store`

### `ArtifactStore`

See the typed implementation and operation contract.

### `LocalArtifactStore`

See the typed implementation and operation contract.

### `ActionCache`

See the typed implementation and operation contract.

## `cvsubstrate.artifacts.capsule`

### `create_capsule`

See the typed implementation and operation contract.

### `validate_capsule`

See the typed implementation and operation contract.

### `archive_capsule`

See the typed implementation and operation contract.

### `materialize_capsule`

See the typed implementation and operation contract.

## `cvsubstrate.schemas.registry`

### `schema_registry`

See the typed implementation and operation contract.

### `inspect_schema`

See the typed implementation and operation contract.

### `validate_artifact`

See the typed implementation and operation contract.

### `MigrationRegistry`

See the typed implementation and operation contract.

### `registry`

See the typed implementation and operation contract.

### `migrate_artifact`

See the typed implementation and operation contract.

### `migrate_run`

See the typed implementation and operation contract.

### `export_schemas`

See the typed implementation and operation contract.

## `cvsubstrate.experiments.dag`

### `Action`

See the typed implementation and operation contract.

### `register_action`

See the typed implementation and operation contract.

### `implementation_identity`

See the typed implementation and operation contract.

### `topological`

See the typed implementation and operation contract.

### `execute_graph`

See the typed implementation and operation contract.

## `cvsubstrate.campaigns.dsl`

### `planned_budgets`

See the typed implementation and operation contract.

### `check_budgets`

See the typed implementation and operation contract.

### `compile_campaign`

See the typed implementation and operation contract.

### `execute_research_campaign`

See the typed implementation and operation contract.

### `set_pointer`

See the typed implementation and operation contract.

### `expand_sweep`

See the typed implementation and operation contract.

### `measured_budget_checks`

See the typed implementation and operation contract.

## `cvsubstrate.benchmarks.registry`

### `register_benchmark`

See the typed implementation and operation contract.

### `list_benchmarks`

See the typed implementation and operation contract.

### `preregister_selection`

See the typed implementation and operation contract.

### `authorize_final`

See the typed implementation and operation contract.

### `final_evaluate`

See the typed implementation and operation contract.

### `validate_submission`

See the typed implementation and operation contract.

## `cvsubstrate.evaluation.converters`

### `PredictionConverterRegistry`

See the typed implementation and operation contract.

### `registry`

See the typed implementation and operation contract.

### `convert_results`

See the typed implementation and operation contract.

## `cvsubstrate.geometry.merge`

### `box_iou`

See the typed implementation and operation contract.

### `merge_detections`

See the typed implementation and operation contract.

## `cvsubstrate.datasets.importers`

### `import_dataset`

See the typed implementation and operation contract.

## `cvsubstrate.backbones.service`

### `extract_features`

See the typed implementation and operation contract.

## `cvsubstrate.deployment.service`

### `execute_deployment`

See the typed implementation and operation contract.

## `cvsubstrate.contracts.frontier`

### `PromptSpec`

See the typed implementation and operation contract.

### `GroundedPrediction`

See the typed implementation and operation contract.

### `MaskRLE`

Uncompressed COCO-column-major binary RLE, initial run always background.

### `MaskInstance`

See the typed implementation and operation contract.

### `MaskPrediction`

See the typed implementation and operation contract.

### `MaskAnnotation`

See the typed implementation and operation contract.

### `VisionJob`

See the typed implementation and operation contract.

### `MaskEvaluationProtocol`

See the typed implementation and operation contract.

### `CalibrationItem`

See the typed implementation and operation contract.

### `QuantizationSpec`

See the typed implementation and operation contract.

### `ClaimSpec`

See the typed implementation and operation contract.

### `ReproductionAttempt`

See the typed implementation and operation contract.

### `IndependenceReview`

See the typed implementation and operation contract.

## `cvsubstrate.telemetry`

### `summarize_telemetry`

See the typed implementation and operation contract.

### `aggregate_telemetry`

See the typed implementation and operation contract.

## `cvsubstrate.streaming.raster`

### `StreamSpec`

See the typed implementation and operation contract.

### `Tile`

See the typed implementation and operation contract.

### `RasterSource`

See the typed implementation and operation contract.

### `Predictor`

See the typed implementation and operation contract.

### `plan_tiles`

Lazy multiscale windows: fractional source offsets preserve exact inversion.

### `PredictionDatabase`

See the typed implementation and operation contract.

### `execute_stream`

See the typed implementation and operation contract.

## `cvsubstrate.streaming.service`

### `stream_job`

See the typed implementation and operation contract.

## `cvsubstrate.vision.masks`

### `encode_mask`

See the typed implementation and operation contract.

### `decode_mask`

See the typed implementation and operation contract.

### `mask_area`

See the typed implementation and operation contract.

### `mask_intersection`

See the typed implementation and operation contract.

### `mask_iou`

See the typed implementation and operation contract.

### `transform_mask`

See the typed implementation and operation contract.

### `paste_mask`

See the typed implementation and operation contract.

### `merge_mask_tiles`

Union only for explicitly same tracked instance ID; do not merge all objects.

### `evaluate_prompt_masks`

Pairs specify prompt -> target *before* evaluation. Never pick by GT IoU.

## `cvsubstrate.vision.grounding`

### `map_grounded`

See the typed implementation and operation contract.

### `cross_paradigm_report`

See the typed implementation and operation contract.

## `cvsubstrate.vision.evaluation`

### `mask_reference_payload`

See the typed implementation and operation contract.

### `evaluate_masks`

See the typed implementation and operation contract.

## `cvsubstrate.vision.service`

### `vision_job`

See the typed implementation and operation contract.

## `cvsubstrate.adapters.recipes`

### `recipes`

See the typed implementation and operation contract.

### `recipe`

See the typed implementation and operation contract.

### `scaffold_vision_adapter`

External plugin delegates to actual optional native vision APIs, not mock outputs.

## `cvsubstrate.deployment.profiles`

### `DetectorProfile`

See the typed implementation and operation contract.

### `preprocess_image`

See the typed implementation and operation contract.

### `decode_outputs`

See the typed implementation and operation contract.

## `cvsubstrate.deployment.calibration`

### `prepare_calibration`

See the typed implementation and operation contract.

### `accuracy_regression`

See the typed implementation and operation contract.

## `cvsubstrate.deployment.quantization`

### `validate_calibration`

See the typed implementation and operation contract.

### `quantize`

See the typed implementation and operation contract.

## `cvsubstrate.research.registry`

### `ResearchRegistry`

See the typed implementation and operation contract.

### `import_snapshot`

See the typed implementation and operation contract.

## `cvsubstrate.research.capture`

### `capture_run`

See the typed implementation and operation contract.

## `cvsubstrate.research.reevaluate`

### `reevaluate`

See the typed implementation and operation contract.

## `cvsubstrate.research.capsule`

### `export_registry_capsule`

See the typed implementation and operation contract.

### `import_registry_capsule`

See the typed implementation and operation contract.
