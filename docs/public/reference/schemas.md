# Contract reference

Generated JSON Schema definitions. Native SDK availability is not inferred.

## AccessApproval

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| dataset_digest | True | `string` |
| experiment_digest | True | `string` |
| split | True | `string` |
| purpose | False | `string` |
| approved_by | True | `string` |
| reason | True | `string` |
| max_uses | False | `integer` |
| note | False | `string` |

## ActorIdentity

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| display_name | True | `string` |
| public_keys | False | `array` |
| identities | False | `object` |
| organization | False | `union / see schema` |
| verification | False | `string` |
| attestation_evidence | False | `array` |

## AdapterCapabilities

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| input_formats | False | `array` |
| output_formats | False | `array` |
| training_contracts | False | `array` |
| precisions | False | `array` |
| adapter | True | `string` |
| protocol_version | False | `string` |
| tasks | True | `array` |
| operations | True | `array` |
| installed | True | `boolean` |
| execution_verified_in_this_process | False | `boolean` |
| limitations | False | `array` |
| environment | False | `object` |

## AdapterSpec

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| name | False | `string` |
| config | False | `object` |

## ArmSpec

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| stages | True | `array` |

## ArtifactEntry

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| path | True | `string` |
| sha256 | True | `string` |
| bytes | True | `integer` |

## ArtifactEnvelope

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| schema_name | True | `string` |
| payload_version | False | `string` |
| payload | True | `object` |
| source_digest | False | `union / see schema` |
| migration_history | False | `array` |

## ArtifactManifest

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| algorithm | False | `string` |
| files | True | `array` |
| root_digest | True | `string` |
| limits | True | `string` |

## ArtifactRef

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| sha256 | True | `string` |
| bytes | True | `integer` |
| media_type | False | `string` |
| name | False | `union / see schema` |

## AssetLineage

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| assets | True | `array` |
| samples | True | `array` |

## BackboneDescriptor

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| provider | True | `string` |
| model | True | `string` |
| weights | False | `union / see schema` |
| weights_sha256 | False | `union / see schema` |
| revision | False | `union / see schema` |
| out_indices | False | `array` |
| trust_local_repository | False | `boolean` |
| local_repository | False | `union / see schema` |
| repository_sha256 | False | `union / see schema` |
| local_model_directory_sha256 | False | `union / see schema` |
| license | False | `string` |
| allow_downloads | False | `boolean` |
| input_contract | False | `object` |

## BackendTemplate

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| experiment | True | `#/$defs/ExperimentSpec` |
| worker_python | False | `union / see schema` |

## BandSpec

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| index | True | `integer` |
| meaning | False | `string` |
| units | True | `string` |
| wavelength_nm | False | `union / see schema` |
| scale | False | `number` |
| offset | False | `number` |
| nodata | False | `union / see schema` |
| normalization | False | `string` |
| minimum | False | `union / see schema` |
| maximum | False | `union / see schema` |
| mean | False | `union / see schema` |
| std | False | `union / see schema` |

## BenchmarkSpec

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| version | True | `string` |
| datasets | True | `object` |
| allowed_training_datasets | False | `array` |
| split_roles | True | `object` |
| taxonomy_digest | True | `string` |
| task | False | `string` |
| evaluation | True | `object` |
| tiling | False | `object` |
| seed_policy | False | `object` |
| required_artifacts | False | `array` |
| locked_test_policy | False | `string` |

## Box

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| xyxy | True | `array` |
| category_id | True | `integer` |
| iscrowd | False | `boolean` |
| ignore | False | `boolean` |
| area | False | `union / see schema` |

## BridgeJob

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| bridge | True | `string` |
| operation | True | `string` |
| payload | True | `object` |
| output_dir | True | `string` |
| worker_python | False | `union / see schema` |
| trust_code | False | `boolean` |
| allow_network | False | `boolean` |
| timeout_seconds | False | `number` |

## BudgetConstraint

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| metric | True | `string` |
| arms | True | `array` |
| tolerance | False | `number` |
| mode | False | `string` |
| limit | False | `union / see schema` |

## CalibrationItem

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| path | True | `string` |
| sha256 | True | `string` |
| split_role | True | `string` |

## CameraRecord

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| image_width | False | `union / see schema` |
| image_height | False | `union / see schema` |
| intrinsics | False | `union / see schema` |
| camera_to_world | False | `union / see schema` |
| coordinate_convention | False | `union / see schema` |
| distance_unit | False | `union / see schema` |

## CampaignSpec

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| backends | True | `array` |
| arms | False | `array` |
| seeds | True | `array` |
| phase | False | `string` |
| selection_record_digest | False | `union / see schema` |
| previous_seeds | False | `array` |
| updates | False | `integer` |
| pretrain_updates | False | `integer` |
| real_per_update | False | `integer` |
| synthetic_per_update | False | `integer` |
| timeout_seconds | False | `number` |
| primary_metric | False | `string` |
| control_claim | False | `string` |
| rationale | True | `string` |

## CapabilityRequirement

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| task | True | `string` |
| operation | True | `string` |
| input_format | True | `string` |
| output_format | True | `string` |
| dataset_fields | False | `array` |
| precision | False | `union / see schema` |

## CatalogueEntry

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| family | True | `string` |
| upstream | False | `string` |
| source_url | True | `string` |
| source_ref | True | `string` |
| source_verified_on | False | `union / see schema` |
| config_path | False | `union / see schema` |
| paper_url | False | `union / see schema` |
| checkpoint_url | False | `union / see schema` |
| checkpoint_sha256 | False | `union / see schema` |
| reported_ap_percent | False | `union / see schema` |
| dataset | False | `string` |
| licenses | False | `#/$defs/LicenseInfo` |
| metadata_status | False | `string` |
| execution_status | False | `string` |
| notes | False | `union / see schema` |

## Category

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `integer` |
| name | True | `string` |

## CheckpointConversionSpec

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| source | True | `#/$defs/CheckpointDescriptor` |
| destination_framework | True | `string` |
| destination_architecture | True | `string` |
| parameter_mapping | False | `object` |
| destination_shapes | False | `object` |
| allowed_missing | False | `array` |
| allowed_drop | False | `array` |
| output_format | False | `string` |

## CheckpointDescriptor

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| source_framework | True | `string` |
| source_revision | False | `union / see schema` |
| architecture | True | `string` |
| path | True | `string` |
| sha256 | True | `string` |
| serialization | False | `string` |
| state_dict_key | False | `union / see schema` |
| license | False | `string` |
| trust_legacy_pickle | False | `boolean` |

## CheckpointRef

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| path | True | `string` |
| sha256 | True | `string` |
| trust | False | `string` |
| license | False | `string` |

## ClaimSpec

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| title | True | `string` |
| question | True | `string` |
| dataset_sha256 | True | `string` |
| protocol_sha256 | True | `string` |
| experiment_sha256 | True | `string` |
| estimand | True | `string` |
| reported_metrics | True | `object` |
| absolute_tolerances | True | `object` |
| author_id | True | `string` |
| implementation_id | True | `string` |
| source_reference | False | `union / see schema` |
| purpose | False | `string` |

## CommandOutput

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| path | True | `string` |
| kind | False | `string` |
| required | False | `boolean` |

## CompatibilityReceipt

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| subject_id | True | `string` |
| protocol | False | `string` |
| task | True | `string` |
| operation | True | `string` |
| implementation | True | `string` |
| execution | False | `string` |
| reference_evaluation | False | `string` |
| reproduction | False | `string` |
| evidence | False | `array` |
| limitations | False | `array` |

## Concept

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| name | True | `string` |
| aliases | False | `array` |
| parents | False | `array` |
| partition | False | `string` |

## ConceptOntology

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| concepts | True | `array` |
| phrase_to_concept | False | `object` |
| category_to_concept | False | `object` |
| case_sensitive | False | `boolean` |

## DatasetManifest

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| version | True | `string` |
| categories | True | `array` |
| samples | True | `array` |
| splits | True | `object` |
| licenses | False | `#/$defs/LicenseInfo` |
| notes | False | `union / see schema` |
| purpose | False | `string` |

## Dependency

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| sha256 | True | `string` |
| disposition | True | `string` |
| path | False | `union / see schema` |
| license | False | `string` |
| depends_on | False | `array` |

## DependencyClosure

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| dependencies | True | `array` |

## DeploymentSpec

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| source | False | `union / see schema` |
| backend | True | `string` |
| model_path | True | `string` |
| model_sha256 | True | `string` |
| input_arrays | False | `object` |
| precision | False | `string` |
| options | False | `object` |
| device | False | `string` |
| trust_executable_artifact | False | `boolean` |

## DetectionPrediction

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| sample_id | True | `string` |
| width | True | `integer` |
| height | True | `integer` |
| boxes | True | `array` |
| scores | True | `array` |
| category_ids | True | `array` |
| coordinate_frame | False | `string` |
| score_semantics | False | `string` |
| transform_provenance | False | `object` |

## DotaReference

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| repository | False | `string` |
| source_revision | True | `string` |
| module_path | True | `string` |
| module_sha256 | True | `string` |
| trust_executable_code | False | `boolean` |
| iou_threshold | False | `number` |
| use_07_metric | False | `boolean` |
| note | False | `string` |

## EffectObservation

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| metric | True | `string` |
| baseline | True | `number` |
| treatment | True | `number` |
| seed_pairs | False | `array` |
| interval | False | `union / see schema` |
| uncertainty_method | False | `union / see schema` |

## EnvironmentCapsule

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| adapter | True | `string` |
| python | True | `string` |
| packages | True | `object` |
| source | False | `object` |
| container_digest | False | `union / see schema` |
| status | False | `string` |
| notes | False | `union / see schema` |

## EnvironmentCommand

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| argv | True | `array` |
| stage | True | `string` |
| cwd | False | `union / see schema` |

## EnvironmentManifest

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| python | False | `union / see schema` |
| platform | False | `union / see schema` |
| packages | False | `array` |
| imports | False | `array` |
| hardware | False | `object` |
| container_digest | False | `union / see schema` |
| metadata_status | False | `string` |
| execution_verified | False | `boolean` |
| unresolved | False | `array` |

## EnvironmentPlan

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| operation | True | `string` |
| spec | True | `#/$defs/ManagedEnvironmentSpec` |
| store | True | `string` |
| revision | True | `integer` |
| revision_dir | True | `string` |
| commands | True | `array` |
| input_hashes | True | `object` |
| previous_revision | False | `union / see schema` |
| network_effects | False | `array` |
| warnings | False | `array` |
| plan_digest | False | `string` |

## EvaluationProtocol

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| evaluator | False | `string` |
| evaluator_version | False | `string` |
| task | False | `string` |
| iou_thresholds | False | `array` |
| recall_thresholds | False | `array` |
| area_ranges | False | `object` |
| max_detections | False | `array` |
| score_threshold | False | `number` |
| ignore_policy | False | `string` |
| tile_merge_policy | False | `object` |
| image_universe | False | `string` |
| use_categories | False | `boolean` |

## EvidenceAttempt

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| claim_id | True | `string` |
| role | True | `string` |
| actor_id | True | `string` |
| machine_id | True | `string` |
| environment_sha256 | True | `string` |
| implementation_id | True | `string` |
| scope_fingerprint | True | `string` |
| outcome | True | `string` |
| effect | False | `union / see schema` |
| evidence | False | `object` |
| failure_reason | False | `union / see schema` |
| purpose | False | `string` |

## EvidenceEdge

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| source | True | `string` |
| target | True | `string` |
| relation | True | `string` |
| evidence | False | `array` |
| rationale | False | `string` |

## ExecutionEvent

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| sequence | True | `integer` |
| at | True | `string` |
| run_id | True | `string` |
| node_id | False | `union / see schema` |
| component | True | `string` |
| event_type | True | `string` |
| payload | False | `object` |
| previous_digest | False | `union / see schema` |

## ExecutionGraph

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| nodes | True | `array` |
| continue_independent_nodes | False | `boolean` |

## ExecutionNode

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| action | True | `string` |
| depends_on | False | `array` |
| inputs | False | `object` |
| parameters | False | `object` |
| cache | False | `boolean` |
| retries | False | `integer` |
| idempotent | False | `boolean` |

## ExperimentSpec

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| dataset | True | `string` |
| dataset_sha256 | True | `string` |
| train_split | False | `string` |
| eval_split | False | `string` |
| seed | False | `integer` |
| adapter | False | `#/$defs/AdapterSpec` |
| checkpoint | False | `union / see schema` |
| training | False | `union / see schema` |
| evaluation | False | `#/$defs/EvaluationProtocol` |
| preprocessing | False | `object` |
| notes | False | `union / see schema` |

## ExternalAsset

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| kind | True | `string` |
| source | True | `string` |
| sha256 | True | `string` |
| size_bytes | False | `union / see schema` |
| license_id | False | `string` |
| license_url | False | `union / see schema` |
| redistribution | False | `string` |
| revision | False | `union / see schema` |
| filename | False | `union / see schema` |

## FieldMapping

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| pointer | True | `string` |
| target | True | `string` |
| group | False | `string` |
| status | False | `string` |
| unit | False | `union / see schema` |
| method | False | `union / see schema` |
| scale | False | `number` |
| offset | False | `number` |
| required | False | `boolean` |

## FinalTestAuthorization

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| experiment_digest | True | `string` |
| dataset_digest | True | `string` |
| split | True | `string` |
| approved_by | True | `string` |
| approved_at | True | `string` |
| purpose | False | `string` |
| acknowledge_policy_not_sandbox | True | `boolean` |

## GenerationMetadata

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| simulator | False | `union / see schema` |
| simulator_version | False | `union / see schema` |
| engine | False | `union / see schema` |
| engine_version | False | `union / see schema` |
| generation_revision | False | `union / see schema` |
| scene_id | False | `union / see schema` |
| asset_ids | False | `array` |
| seed | False | `union / see schema` |
| units | False | `object` |
| coordinate_convention | False | `union / see schema` |
| planned | False | `object` |
| observed | False | `object` |
| occlusion_fraction | False | `union / see schema` |
| truncation_fraction | False | `union / see schema` |
| visibility_definition | False | `union / see schema` |
| annotation_method | False | `union / see schema` |

## GeoDatasetManifest

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| version | True | `string` |
| raster_assets | True | `array` |
| dataset_digest | False | `union / see schema` |
| task | False | `string` |
| license | False | `string` |
| notes | False | `union / see schema` |

## GeoReference

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| crs | True | `string` |
| affine | True | `array` |
| pixel_reference | False | `string` |
| axis_order | False | `string` |
| gsd_m | False | `union / see schema` |

## GeoSceneSpec

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| raster_sha256 | True | `string` |
| width | True | `integer` |
| height | True | `integer` |
| crs | False | `union / see schema` |
| coordinate_kind | False | `string` |
| affine | True | `array` |
| sensor | True | `#/$defs/SensorSpec` |
| capture_timestamp | False | `union / see schema` |
| temporal_stack_id | False | `union / see schema` |
| temporal_index | False | `union / see schema` |
| parent_scene_ids | False | `array` |

## GroundedPrediction

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| sample_id | True | `string` |
| width | True | `integer` |
| height | True | `integer` |
| prompt | True | `#/$defs/PromptSpec` |
| boxes | True | `array` |
| scores | True | `array` |
| phrases | True | `array` |
| token_spans | False | `array` |
| native_output_sha256 | False | `union / see schema` |

## HeritageCertification

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| reference_digest | True | `string` |
| compatibility_level | True | `string` |
| evidence | False | `object` |
| blockers | False | `array` |
| independently_reproduced | False | `boolean` |
| note | False | `string` |

## IndependenceAttestation

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| attempt_id | True | `string` |
| reviewer_id | True | `string` |
| independent_operator | False | `boolean` |
| independent_machine | False | `boolean` |
| independent_environment | False | `boolean` |
| independent_implementation | False | `boolean` |
| independent_organization | False | `boolean` |
| evidence | True | `array` |
| rationale | True | `string` |

## IndependenceReview

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| attempt_id | True | `string` |
| reviewer_id | True | `string` |
| independent_operator_attested | True | `boolean` |
| independent_machine_attested | True | `boolean` |
| independent_implementation_attested | False | `boolean` |
| rationale | True | `string` |
| evidence_sha256 | True | `string` |

## InputReference

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| path | False | `union / see schema` |
| sha256 | False | `union / see schema` |
| node | False | `union / see schema` |
| artifact | False | `union / see schema` |

## InteropArtifact

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| kind | True | `string` |
| path | True | `string` |
| sha256 | True | `string` |
| shape | False | `union / see schema` |
| dtype | False | `union / see schema` |
| coordinate_frame | False | `union / see schema` |
| sample_ids | False | `array` |
| producer | False | `object` |
| semantics | False | `object` |
| materialized | False | `boolean` |
| differentiable | False | `boolean` |

## LargeImagePlan

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| source_id | True | `string` |
| source_width | True | `integer` |
| source_height | True | `integer` |
| scales | False | `array` |
| tile_width | False | `integer` |
| tile_height | False | `integer` |
| overlap_x | False | `integer` |
| overlap_y | False | `integer` |
| pad_edges | False | `boolean` |
| batch_size | False | `integer` |
| memory_budget_bytes | False | `union / see schema` |
| channels | False | `integer` |
| bytes_per_value | False | `integer` |
| merge | False | `#/$defs/MergePolicy` |

## LaunchPlan

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| repository | True | `string` |
| package | True | `string` |
| release_version | True | `string` |
| readiness | True | `string` |
| operations | True | `array` |
| owner_actions | True | `array` |
| approval_digest | False | `string` |
| executed | False | `boolean` |

## LegacyExperimentRef

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| upstream | True | `string` |
| revision | True | `string` |
| framework_version | False | `union / see schema` |
| config | True | `string` |
| config_sha256 | True | `string` |
| resolved_config_sha256 | False | `union / see schema` |
| config_graph_sha256 | False | `union / see schema` |
| checkpoint | False | `union / see schema` |
| dataset_sha256 | False | `union / see schema` |
| taxonomy | False | `array` |
| environment_reference | True | `string` |
| trust_executable_config | False | `boolean` |
| licenses | False | `#/$defs/LicenseInfo` |
| reference_dataset | False | `union / see schema` |
| reference_protocol | False | `object` |
| reported_metrics | False | `object` |
| status | False | `string` |
| compatibility_level | False | `string` |
| evidence | False | `object` |

## LicenseInfo

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| code | False | `string` |
| weights | False | `string` |
| data | False | `string` |
| annotations | False | `string` |
| redistribution | False | `string` |
| notes | False | `union / see schema` |

## LocalPackageArtifact

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| path | True | `string` |
| sha256 | True | `string` |

## ManagedEnvironmentSpec

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| backend | False | `string` |
| pack | False | `string` |
| python | True | `string` |
| python_constraint | False | `string` |
| requirements | False | `array` |
| artifacts | False | `array` |
| expected_modules | False | `array` |
| conda_packages | False | `array` |
| conda_channels | False | `array` |
| base_image | False | `union / see schema` |
| allow_network | False | `boolean` |
| allow_python_download | False | `boolean` |
| allow_source_builds | False | `boolean` |
| index_url | False | `string` |
| require_hashes | False | `boolean` |
| timeout_seconds | False | `number` |
| notes | False | `string` |

## MaskAnnotation

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| sample_id | True | `string` |
| instance_id | True | `string` |
| mask | True | `#/$defs/MaskRLE` |
| category_id | False | `union / see schema` |
| iscrowd | False | `boolean` |
| ignore | False | `boolean` |

## MaskEvaluationProtocol

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| evaluator | False | `string` |
| evaluator_version | False | `string` |
| task | False | `string` |
| bbox_parameters | False | `object` |
| prompt_policy | False | `string` |
| split_role | False | `string` |

## MaskInstance

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| mask | True | `#/$defs/MaskRLE` |
| score | True | `number` |
| score_kind | False | `string` |
| score_semantics | False | `string` |
| category_id | False | `union / see schema` |
| prompt_id | False | `union / see schema` |

## MaskPrediction

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| sample_id | True | `string` |
| width | True | `integer` |
| height | True | `integer` |
| instances | True | `array` |
| prompts | False | `array` |
| selection_policy | False | `string` |
| native_output_sha256 | False | `union / see schema` |

## MaskRLE

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| height | True | `integer` |
| width | True | `integer` |
| counts | True | `array` |
| order | False | `string` |

## MergePolicy

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| kind | False | `string` |
| iou_threshold | False | `number` |
| score_threshold | False | `number` |
| sigma | False | `number` |
| score_fusion | False | `string` |
| max_detections | False | `integer` |

## MethodologySpec

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| dataset_digest | False | `union / see schema` |
| baseline_dataset_digest | False | `union / see schema` |
| evaluation | False | `object` |
| baseline_evaluation | False | `object` |
| arms | False | `array` |
| prompts | False | `array` |
| assets | False | `array` |
| test_accesses | False | `array` |
| lineage | False | `array` |
| declared_interventions | False | `array` |

## NativeCampaign

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| stages | True | `array` |
| seeds | True | `array` |
| equality_requirements | False | `array` |

## NativeStage

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| backend | True | `string` |
| budget_unit | True | `string` |
| budget | True | `integer` |
| dataset_sha256 | True | `string` |
| source | True | `string` |
| job | True | `object` |
| initialized_from | False | `union / see schema` |
| initial_checkpoint | False | `union / see schema` |
| initial_checkpoint_sha256 | False | `union / see schema` |
| checkpoint_output | True | `string` |

## ObjectSizePolicy

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| statistic | False | `string` |
| edges | False | `array` |

## Observation

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| status | False | `string` |
| value | False | `union / see schema` |
| unit | False | `union / see schema` |
| method | False | `union / see schema` |
| input_digests | False | `array` |
| uncertainty | False | `union / see schema` |

## OrientedAnnotation

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| polygon | True | `array` |
| category_id | True | `integer` |
| difficult | False | `boolean` |
| source_line | False | `union / see schema` |

## OrientedDataset

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| version | True | `string` |
| categories | True | `array` |
| samples | True | `array` |
| role | True | `string` |
| purpose | False | `string` |
| licenses | False | `#/$defs/LicenseInfo` |
| convention | False | `string` |
| note | False | `string` |

## OrientedPrediction

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| sample_id | True | `string` |
| polygons | True | `array` |
| scores | True | `array` |
| category_ids | True | `array` |
| convention | False | `string` |

## OrientedSample

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| image | True | `string` |
| sha256 | True | `string` |
| width | True | `integer` |
| height | True | `integer` |
| annotations | False | `array` |
| domain | False | `string` |
| source_kind | False | `string` |
| lineage_group | False | `union / see schema` |
| metadata | False | `object` |

## PaperCommand

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| argv | True | `array` |
| outputs | False | `object` |
| timeout_seconds | False | `number` |
| env | False | `object` |

## PaperRecipe

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| title | True | `string` |
| source_urls | True | `array` |
| repositories | True | `array` |
| frameworks | True | `array` |
| tasks | True | `array` |
| assets | False | `array` |
| commands | False | `object` |
| integration_boundary | True | `string` |
| status | False | `string` |
| verified_revision | False | `union / see schema` |
| inspected_date | True | `string` |
| limitations | True | `array` |

## PaperRunSpec

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| repo | True | `string` |
| python | True | `string` |
| repository_digest | True | `string` |
| operations | True | `object` |
| inputs | False | `object` |
| input_digests | False | `object` |
| purpose | False | `string` |
| trust_code | False | `boolean` |
| network | False | `string` |
| unresolved | False | `array` |

## PluginDescriptor

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| kind | True | `string` |
| protocol_version | False | `string` |
| target | True | `string` |
| tasks | False | `array` |
| operations | False | `array` |
| formats | False | `array` |
| required_packages | False | `array` |
| trust_code | False | `boolean` |
| evidence | False | `object` |
| implementation_revision | False | `union / see schema` |
| execution_status | False | `string` |

## ProductFinding

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| rule_id | True | `string` |
| severity | True | `string` |
| message | True | `string` |
| evidence | False | `array` |
| remediation | False | `union / see schema` |
| rule_version | False | `string` |

## PromptAtom

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| kind | True | `string` |
| source | True | `string` |
| source_sha256 | False | `union / see schema` |
| target_id | False | `union / see schema` |
| text | False | `union / see schema` |
| points | False | `array` |
| labels | False | `array` |
| box | False | `union / see schema` |
| mask | False | `union / see schema` |
| reference | False | `union / see schema` |
| concept_id | False | `union / see schema` |

## PromptSet

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| sample_id | True | `string` |
| width | True | `integer` |
| height | True | `integer` |
| prompts | True | `array` |
| previous_set_sha256 | False | `union / see schema` |
| previous_prediction_sha256 | False | `union / see schema` |
| interaction | False | `string` |

## PromptSpec

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| sample_id | True | `string` |
| kind | True | `string` |
| text | False | `union / see schema` |
| points | False | `array` |
| point_labels | False | `array` |
| box | False | `union / see schema` |
| mask_reference | False | `union / see schema` |
| source | True | `string` |
| source_artifact_sha256 | False | `union / see schema` |

## ProvenanceEdge

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| source | True | `string` |
| target | True | `string` |
| relation | True | `string` |
| evidence | False | `array` |

## ProvenanceGraph

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| nodes | True | `array` |
| edges | True | `array` |

## ProvenanceNode

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| kind | True | `string` |
| content_sha256 | True | `string` |
| metadata | False | `object` |

## PublicationSettings

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| display_name | False | `string` |
| distribution_name | False | `string` |
| import_name | False | `string` |
| cli_name | False | `string` |
| repository_url | False | `union / see schema` |
| authors | False | `array` |
| license_id | False | `string` |
| copyright_holder | False | `union / see schema` |
| identity_approved | False | `boolean` |
| license_approved | False | `boolean` |
| security_contact | False | `union / see schema` |
| private_terms | False | `array` |

## Quantity

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| status | True | `string` |
| value | False | `union / see schema` |
| unit | False | `union / see schema` |
| method | False | `union / see schema` |
| evidence | False | `union / see schema` |

## QuantizationSpec

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| backend | True | `string` |
| model_path | True | `string` |
| model_sha256 | True | `string` |
| calibration | True | `array` |
| dataset_sha256 | True | `string` |
| preprocessing_sha256 | True | `string` |
| input_names | True | `array` |
| input_shapes | False | `object` |
| method | False | `string` |
| per_channel | False | `boolean` |
| weight_type | False | `string` |
| activation_type | False | `string` |
| nodes_to_exclude | False | `array` |
| trust_model | False | `boolean` |

## ReferenceAsset

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| path | True | `string` |
| sha256 | True | `string` |
| width | False | `union / see schema` |
| height | False | `union / see schema` |
| region | False | `union / see schema` |

## RepositoryReport

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| repository_name | True | `string` |
| root_identity | True | `string` |
| files | True | `object` |
| observations | True | `array` |
| frameworks | True | `array` |
| command_candidates | True | `array` |
| unresolved | True | `array` |
| git | False | `object` |
| truncated | False | `boolean` |
| executable_code_loaded | False | `boolean` |

## ReproductionAttempt

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| attempt_kind | False | `string` |
| claim_id | True | `string` |
| actor_id | True | `string` |
| machine_id | True | `string` |
| implementation_id | True | `string` |
| dataset_sha256 | True | `string` |
| protocol_sha256 | True | `string` |
| experiment_sha256 | True | `string` |
| estimand | True | `string` |
| outcome | True | `string` |
| metrics | False | `object` |
| evidence | False | `object` |
| failure_reason | False | `union / see schema` |
| purpose | False | `string` |

## ResearchCampaign

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| arms | True | `array` |
| seeds | True | `array` |
| backends | True | `array` |
| constraints | False | `array` |
| phase | False | `string` |
| previous_seeds | False | `array` |
| selection_digest | False | `union / see schema` |

## RichFrame

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| sample_id | True | `string` |
| width | True | `integer` |
| height | True | `integer` |
| image | False | `union / see schema` |
| image_sha256 | False | `union / see schema` |
| task | True | `string` |
| objects | True | `array` |
| metadata | False | `object` |

## RichInterchange

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| dataset_digest | True | `string` |
| categories | False | `object` |
| frames | True | `array` |
| licenses | False | `object` |
| provenance | False | `object` |

## RichObject

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| category_id | False | `union / see schema` |
| score | True | `number` |
| box | False | `union / see schema` |
| polygon | False | `union / see schema` |
| mask | False | `union / see schema` |
| phrase | False | `union / see schema` |
| prompt_digest | False | `union / see schema` |
| attributes | False | `object` |

## RunManifest

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| run_id | True | `string` |
| experiment_digest | True | `string` |
| dataset_digest | True | `string` |
| state | True | `string` |
| created_at | True | `string` |
| finished_at | False | `union / see schema` |
| failure | False | `union / see schema` |
| note | False | `string` |

## Sample

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| image | True | `string` |
| sha256 | True | `string` |
| width | True | `integer` |
| height | True | `integer` |
| source_kind | False | `string` |
| domain | False | `string` |
| sensor | False | `union / see schema` |
| lineage_group | False | `union / see schema` |
| parent_ids | False | `array` |
| boxes | False | `array` |
| geospatial | False | `union / see schema` |
| generation | False | `union / see schema` |

## SampleLineage

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| sample_id | True | `string` |
| split | True | `string` |
| asset_ids | False | `array` |

## ScientificClaim

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| title | True | `string` |
| population | True | `string` |
| dataset_sha256 | True | `string` |
| split | True | `string` |
| intervention | True | `object` |
| comparator | True | `object` |
| metric | True | `string` |
| units | False | `string` |
| direction | True | `string` |
| minimum_effect | False | `number` |
| equivalence_margin | False | `number` |
| reproduction_tolerance | False | `number` |
| protocol_sha256 | True | `string` |
| model_scope | False | `object` |
| conditions | False | `object` |
| author_id | True | `string` |
| purpose | False | `string` |

## SemanticLabelMap

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| task | False | `string` |
| sample_id | True | `string` |
| width | True | `integer` |
| height | True | `integer` |
| labels | True | `string` |
| sha256 | True | `string` |
| category_mapping | True | `object` |
| ignore_index | False | `integer` |
| reduce_zero_label | False | `boolean` |

## SensorSpec

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| kind | True | `string` |
| bands | True | `array` |
| model_channel_names | True | `array` |
| output_dtype | False | `string` |

## SidecarMapping

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| sample_id_pointer | False | `string` |
| generator | True | `string` |
| generator_version | False | `union / see schema` |
| simulator | False | `union / see schema` |
| engine | False | `union / see schema` |
| fields | True | `array` |
| identity_pointers | False | `object` |
| note | False | `string` |

## SliceExpression

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| expression | True | `object` |
| level | False | `string` |
| missing_policy | False | `string` |
| metadata_origin | True | `string` |

## SourceAsset

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| kind | True | `string` |
| sha256 | False | `union / see schema` |
| parents | False | `array` |
| license | False | `string` |

## SourceObservation

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| path | True | `string` |
| line | True | `integer` |
| kind | True | `string` |
| value | True | `string` |
| confidence | False | `string` |

## Split

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| role | True | `string` |
| sample_ids | True | `array` |

## StageSpec

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| source | True | `string` |
| updates | True | `integer` |
| real_per_update | False | `integer` |
| synthetic_per_update | False | `integer` |
| real_weight | False | `number` |
| synthetic_weight | False | `number` |
| initialize_from_previous | False | `boolean` |
| transition | False | `string` |

## SyntheticObject

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| object_id | True | `string` |
| asset_id | False | `union / see schema` |
| category | False | `union / see schema` |
| attributes | False | `object` |

## SyntheticRecord

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| sample_id | True | `string` |
| generator | True | `string` |
| generator_version | False | `union / see schema` |
| simulator | False | `union / see schema` |
| simulator_version | False | `union / see schema` |
| engine | False | `union / see schema` |
| engine_version | False | `union / see schema` |
| generation_revision | False | `union / see schema` |
| generation_environment_digest | False | `union / see schema` |
| raw_sidecar_digest | False | `union / see schema` |
| scene_id | False | `union / see schema` |
| scene_source | False | `union / see schema` |
| asset_ids | False | `array` |
| seed | False | `union / see schema` |
| camera | False | `#/$defs/CameraRecord` |
| planned | False | `object` |
| observed | False | `object` |
| objects | False | `array` |
| annotation_method | False | `union / see schema` |
| licenses | False | `#/$defs/LicenseInfo` |
| notes | False | `union / see schema` |

## SyntheticSampleManifest

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| record | True | `#/$defs/SyntheticRecord` |
| scene | False | `object` |
| assets | False | `array` |
| lens | False | `object` |
| sensor | False | `object` |
| rendering | False | `object` |
| weather | False | `object` |
| illumination | False | `object` |
| compression | False | `object` |
| randomization | False | `object` |
| annotations | False | `object` |
| object_observations | False | `object` |
| planned | False | `object` |
| measurement_definitions | False | `object` |

## TilingPolicy

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| width | False | `integer` |
| height | False | `integer` |
| overlap_x | False | `integer` |
| overlap_y | False | `integer` |
| resize_width | False | `union / see schema` |
| resize_height | False | `union / see schema` |
| resize_method | False | `string` |
| edge_policy | False | `string` |
| pad_to_tile | False | `boolean` |
| padding_rgb | False | `array` |
| padding_prediction_policy | False | `string` |
| merge | False | `string` |
| merge_iou | False | `number` |
| max_source_pixels | False | `integer` |
| max_tiles | False | `integer` |

## TinyEvaluationPolicy

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| iou | False | `number` |
| size_edges | False | `array` |
| size_statistic | False | `string` |
| density_edges | False | `array` |
| border_distances_px | False | `array` |
| fppi_budgets | False | `array` |
| fixed_score_threshold | False | `number` |
| max_detections_per_image | False | `integer` |

## TrainingSpec

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| arm | False | `string` |
| updates | False | `integer` |
| pretrain_updates | False | `integer` |
| real_per_update | False | `integer` |
| synthetic_per_update | False | `integer` |
| learning_rate | False | `number` |
| synthetic_weight | False | `number` |
| fairness | False | `string` |
| optimizer | False | `string` |
| precision | False | `string` |
| stage_transition | False | `string` |

## TrainingTrace

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| update | True | `integer` |
| stage | True | `string` |
| real_sample_ids | True | `array` |
| synthetic_sample_ids | True | `array` |
| real_loss | False | `union / see schema` |
| synthetic_loss | False | `union / see schema` |
| nominal_synthetic_weight | True | `number` |
| real_primary_sample_ids | False | `array` |
| real_replay_sample_ids | False | `array` |
| real_replay_loss | False | `union / see schema` |
| weighted_total_loss | True | `number` |
| gradient_influence | False | `string` |
| augmentation | False | `string` |

## VisionAsset

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| role | True | `string` |
| path | True | `string` |
| sha256 | True | `string` |
| license | False | `string` |

## VisionJob

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| backend | True | `string` |
| operation | False | `string` |
| model_dir | True | `string` |
| model_files | True | `object` |
| trust_local_code | False | `boolean` |
| device | False | `string` |
| package_versions | False | `object` |
| images | False | `array` |
| prompts | False | `array` |
| config | False | `object` |
| purpose | False | `string` |

## VisionModelDescriptor

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| backend | True | `string` |
| revision | True | `string` |
| assets | True | `array` |
| preprocessing | False | `object` |
| feature_geometry | False | `object` |

## WorkerPlugin

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| script | True | `string` |
| script_sha256 | True | `string` |
| interpreter | False | `union / see schema` |
| protocol_version | False | `string` |
| trust_executable_code | False | `boolean` |
| implementation_revision | False | `union / see schema` |
| environment_capsule_digest | False | `union / see schema` |

## WorkerRequest

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| protocol_version | False | `string` |
| operation | True | `string` |
| experiment | False | `union / see schema` |
| manifest | False | `union / see schema` |
| data_root | False | `union / see schema` |
| output_dir | False | `union / see schema` |
| checkpoint | False | `union / see schema` |
| final_test_authorization | False | `union / see schema` |

## WorkerResponse

| Field | Required | Definition |
|---|---|---|
| schema_version | False | `string` |
| protocol_version | False | `string` |
| status | True | `string` |
| result | False | `object` |
| error | False | `union / see schema` |
