# Contract reference

Generated from Pydantic schemas. Optional dependencies are not imported.

## AccessApproval



| Field | Required | Type/schema |
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

## AdapterCapabilities



| Field | Required | Type/schema |
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



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| name | False | `string` |
| config | False | `object` |

## ArmSpec



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| stages | True | `array` |

## ArtifactEntry



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| path | True | `string` |
| sha256 | True | `string` |
| bytes | True | `integer` |

## ArtifactEnvelope



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| schema_name | True | `string` |
| payload_version | False | `string` |
| payload | True | `object` |
| source_digest | False | `[{'pattern': '^[a-f0-9]{64}$', 'type': 'string'}, {'type': 'null'}]` |
| migration_history | False | `array` |

## ArtifactManifest



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| algorithm | False | `string` |
| files | True | `array` |
| root_digest | True | `string` |
| limits | True | `string` |

## ArtifactRef



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| sha256 | True | `string` |
| bytes | True | `integer` |
| media_type | False | `string` |
| name | False | `[{'type': 'string'}, {'type': 'null'}]` |

## BackboneDescriptor



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| provider | True | `string` |
| model | True | `string` |
| weights | False | `[{'type': 'string'}, {'type': 'null'}]` |
| weights_sha256 | False | `[{'pattern': '^[a-f0-9]{64}$', 'type': 'string'}, {'type': 'null'}]` |
| revision | False | `[{'type': 'string'}, {'type': 'null'}]` |
| out_indices | False | `array` |
| trust_local_repository | False | `boolean` |
| local_repository | False | `[{'type': 'string'}, {'type': 'null'}]` |
| repository_sha256 | False | `[{'pattern': '^[a-f0-9]{64}$', 'type': 'string'}, {'type': 'null'}]` |
| local_model_directory_sha256 | False | `[{'pattern': '^[a-f0-9]{64}$', 'type': 'string'}, {'type': 'null'}]` |
| license | False | `string` |
| allow_downloads | False | `boolean` |
| input_contract | False | `object` |

## BackendTemplate



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| experiment | True | `#/$defs/ExperimentSpec` |
| worker_python | False | `[{'type': 'string'}, {'type': 'null'}]` |

## BenchmarkSpec



| Field | Required | Type/schema |
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



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| xyxy | True | `array` |
| category_id | True | `integer` |
| iscrowd | False | `boolean` |
| ignore | False | `boolean` |
| area | False | `[{'type': 'number'}, {'type': 'null'}]` |

## BudgetConstraint



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| metric | True | `string` |
| arms | True | `array` |
| tolerance | False | `number` |
| mode | False | `string` |
| limit | False | `[{'type': 'number'}, {'type': 'null'}]` |

## CameraRecord



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| image_width | False | `[{'exclusiveMinimum': 0, 'type': 'integer'}, {'type': 'null'}]` |
| image_height | False | `[{'exclusiveMinimum': 0, 'type': 'integer'}, {'type': 'null'}]` |
| intrinsics | False | `[{'items': {'items': {'type': 'number'}, 'type': 'array'}, 'type': 'array'}, {'type': 'null'}]` |
| camera_to_world | False | `[{'items': {'items': {'type': 'number'}, 'type': 'array'}, 'type': 'array'}, {'type': 'null'}]` |
| coordinate_convention | False | `[{'type': 'string'}, {'type': 'null'}]` |
| distance_unit | False | `[{'type': 'string'}, {'type': 'null'}]` |

## CampaignSpec



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| backends | True | `array` |
| arms | False | `array` |
| seeds | True | `array` |
| phase | False | `string` |
| selection_record_digest | False | `[{'pattern': '^[a-f0-9]{64}$', 'type': 'string'}, {'type': 'null'}]` |
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



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| task | True | `string` |
| operation | True | `string` |
| input_format | True | `string` |
| output_format | True | `string` |
| dataset_fields | False | `array` |
| precision | False | `[{'type': 'string'}, {'type': 'null'}]` |

## CatalogueEntry



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| family | True | `string` |
| upstream | False | `string` |
| source_url | True | `string` |
| source_ref | True | `string` |
| source_verified_on | False | `[{'type': 'string'}, {'type': 'null'}]` |
| config_path | False | `[{'type': 'string'}, {'type': 'null'}]` |
| paper_url | False | `[{'type': 'string'}, {'type': 'null'}]` |
| checkpoint_url | False | `[{'type': 'string'}, {'type': 'null'}]` |
| checkpoint_sha256 | False | `[{'pattern': '^[a-f0-9]{64}$', 'type': 'string'}, {'type': 'null'}]` |
| reported_ap_percent | False | `[{'type': 'number'}, {'type': 'null'}]` |
| dataset | False | `string` |
| licenses | False | `#/$defs/LicenseInfo` |
| metadata_status | False | `string` |
| execution_status | False | `string` |
| notes | False | `[{'type': 'string'}, {'type': 'null'}]` |

## Category



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| id | True | `integer` |
| name | True | `string` |

## CheckpointConversionSpec



| Field | Required | Type/schema |
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



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| source_framework | True | `string` |
| source_revision | False | `[{'type': 'string'}, {'type': 'null'}]` |
| architecture | True | `string` |
| path | True | `string` |
| sha256 | True | `string` |
| serialization | False | `string` |
| state_dict_key | False | `[{'type': 'string'}, {'type': 'null'}]` |
| license | False | `string` |
| trust_legacy_pickle | False | `boolean` |

## CheckpointRef



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| path | True | `string` |
| sha256 | True | `string` |
| trust | False | `string` |
| license | False | `string` |

## DatasetManifest



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| version | True | `string` |
| categories | True | `array` |
| samples | True | `array` |
| splits | True | `object` |
| licenses | False | `#/$defs/LicenseInfo` |
| notes | False | `[{'type': 'string'}, {'type': 'null'}]` |
| purpose | False | `string` |

## DeploymentSpec



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| source | False | `[{'$ref': '#/$defs/CheckpointDescriptor'}, {'type': 'null'}]` |
| backend | True | `string` |
| model_path | True | `string` |
| model_sha256 | True | `string` |
| input_arrays | False | `object` |
| precision | False | `string` |
| options | False | `object` |
| device | False | `string` |
| trust_executable_artifact | False | `boolean` |

## DetectionPrediction



| Field | Required | Type/schema |
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



| Field | Required | Type/schema |
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

## EnvironmentCapsule



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| adapter | True | `string` |
| python | True | `string` |
| packages | True | `object` |
| source | False | `object` |
| container_digest | False | `[{'pattern': '^[a-f0-9]{64}$', 'type': 'string'}, {'type': 'null'}]` |
| status | False | `string` |
| notes | False | `[{'type': 'string'}, {'type': 'null'}]` |

## EnvironmentManifest



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| python | False | `[{'type': 'string'}, {'type': 'null'}]` |
| platform | False | `[{'type': 'string'}, {'type': 'null'}]` |
| packages | False | `array` |
| imports | False | `array` |
| hardware | False | `object` |
| container_digest | False | `[{'type': 'string'}, {'type': 'null'}]` |
| metadata_status | False | `string` |
| execution_verified | False | `boolean` |
| unresolved | False | `array` |

## EvaluationProtocol



| Field | Required | Type/schema |
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

## ExecutionEvent



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| sequence | True | `integer` |
| at | True | `string` |
| run_id | True | `string` |
| node_id | False | `[{'type': 'string'}, {'type': 'null'}]` |
| component | True | `string` |
| event_type | True | `string` |
| payload | False | `object` |
| previous_digest | False | `[{'pattern': '^[a-f0-9]{64}$', 'type': 'string'}, {'type': 'null'}]` |

## ExecutionGraph



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| nodes | True | `array` |
| continue_independent_nodes | False | `boolean` |

## ExecutionNode



| Field | Required | Type/schema |
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



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| dataset | True | `string` |
| dataset_sha256 | True | `string` |
| train_split | False | `string` |
| eval_split | False | `string` |
| seed | False | `integer` |
| adapter | False | `#/$defs/AdapterSpec` |
| checkpoint | False | `[{'$ref': '#/$defs/CheckpointRef'}, {'type': 'null'}]` |
| training | False | `[{'$ref': '#/$defs/TrainingSpec'}, {'type': 'null'}]` |
| evaluation | False | `#/$defs/EvaluationProtocol` |
| preprocessing | False | `object` |
| notes | False | `[{'type': 'string'}, {'type': 'null'}]` |

## FieldMapping



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| pointer | True | `string` |
| target | True | `string` |
| group | False | `string` |
| status | False | `string` |
| unit | False | `[{'type': 'string'}, {'type': 'null'}]` |
| method | False | `[{'type': 'string'}, {'type': 'null'}]` |
| scale | False | `number` |
| offset | False | `number` |
| required | False | `boolean` |

## FinalTestAuthorization



| Field | Required | Type/schema |
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



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| simulator | False | `[{'type': 'string'}, {'type': 'null'}]` |
| simulator_version | False | `[{'type': 'string'}, {'type': 'null'}]` |
| engine | False | `[{'type': 'string'}, {'type': 'null'}]` |
| engine_version | False | `[{'type': 'string'}, {'type': 'null'}]` |
| generation_revision | False | `[{'type': 'string'}, {'type': 'null'}]` |
| scene_id | False | `[{'type': 'string'}, {'type': 'null'}]` |
| asset_ids | False | `array` |
| seed | False | `[{'minimum': 0, 'type': 'integer'}, {'type': 'null'}]` |
| units | False | `object` |
| coordinate_convention | False | `[{'type': 'string'}, {'type': 'null'}]` |
| planned | False | `object` |
| observed | False | `object` |
| occlusion_fraction | False | `[{'maximum': 1, 'minimum': 0, 'type': 'number'}, {'type': 'null'}]` |
| truncation_fraction | False | `[{'maximum': 1, 'minimum': 0, 'type': 'number'}, {'type': 'null'}]` |
| visibility_definition | False | `[{'type': 'string'}, {'type': 'null'}]` |
| annotation_method | False | `[{'type': 'string'}, {'type': 'null'}]` |

## GeoDatasetManifest



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| version | True | `string` |
| raster_assets | True | `array` |
| dataset_digest | False | `[{'pattern': '^[a-f0-9]{64}$', 'type': 'string'}, {'type': 'null'}]` |
| task | False | `string` |
| license | False | `string` |
| notes | False | `[{'type': 'string'}, {'type': 'null'}]` |

## GeoReference



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| crs | True | `string` |
| affine | True | `array` |
| pixel_reference | False | `string` |
| axis_order | False | `string` |
| gsd_m | False | `[{'items': {'type': 'number'}, 'type': 'array'}, {'type': 'null'}]` |

## HeritageCertification



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| reference_digest | True | `string` |
| compatibility_level | True | `string` |
| evidence | False | `object` |
| blockers | False | `array` |
| independently_reproduced | False | `boolean` |
| note | False | `string` |

## InputReference



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| path | False | `[{'type': 'string'}, {'type': 'null'}]` |
| sha256 | False | `[{'pattern': '^[a-f0-9]{64}$', 'type': 'string'}, {'type': 'null'}]` |
| node | False | `[{'maxLength': 180, 'minLength': 1, 'pattern': '^[A-Za-z0-9][A-Za-z0-9_.:-]*$', 'type': 'string'}, {'type': 'null'}]` |
| artifact | False | `[{'type': 'string'}, {'type': 'null'}]` |

## LargeImagePlan



| Field | Required | Type/schema |
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
| memory_budget_bytes | False | `[{'exclusiveMinimum': 0, 'type': 'integer'}, {'type': 'null'}]` |
| channels | False | `integer` |
| bytes_per_value | False | `integer` |
| merge | False | `#/$defs/MergePolicy` |

## LegacyExperimentRef



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| upstream | True | `string` |
| revision | True | `string` |
| framework_version | False | `[{'type': 'string'}, {'type': 'null'}]` |
| config | True | `string` |
| config_sha256 | True | `string` |
| resolved_config_sha256 | False | `[{'pattern': '^[a-f0-9]{64}$', 'type': 'string'}, {'type': 'null'}]` |
| config_graph_sha256 | False | `[{'pattern': '^[a-f0-9]{64}$', 'type': 'string'}, {'type': 'null'}]` |
| checkpoint | False | `[{'$ref': '#/$defs/CheckpointRef'}, {'type': 'null'}]` |
| dataset_sha256 | False | `[{'pattern': '^[a-f0-9]{64}$', 'type': 'string'}, {'type': 'null'}]` |
| taxonomy | False | `array` |
| environment_reference | True | `string` |
| trust_executable_config | False | `boolean` |
| licenses | False | `#/$defs/LicenseInfo` |
| reference_dataset | False | `[{'type': 'string'}, {'type': 'null'}]` |
| reference_protocol | False | `object` |
| reported_metrics | False | `object` |
| status | False | `string` |
| compatibility_level | False | `string` |
| evidence | False | `object` |

## LicenseInfo



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| code | False | `string` |
| weights | False | `string` |
| data | False | `string` |
| annotations | False | `string` |
| redistribution | False | `string` |
| notes | False | `[{'type': 'string'}, {'type': 'null'}]` |

## MergePolicy



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| kind | False | `string` |
| iou_threshold | False | `number` |
| score_threshold | False | `number` |
| sigma | False | `number` |
| score_fusion | False | `string` |
| max_detections | False | `integer` |

## ObjectSizePolicy



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| statistic | False | `string` |
| edges | False | `array` |

## Observation



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| status | False | `string` |
| value | False | `see schema` |
| unit | False | `[{'type': 'string'}, {'type': 'null'}]` |
| method | False | `[{'type': 'string'}, {'type': 'null'}]` |
| input_digests | False | `array` |
| uncertainty | False | `[{'minimum': 0, 'type': 'number'}, {'type': 'null'}]` |

## OrientedAnnotation



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| polygon | True | `array` |
| category_id | True | `integer` |
| difficult | False | `boolean` |
| source_line | False | `[{'exclusiveMinimum': 0, 'type': 'integer'}, {'type': 'null'}]` |

## OrientedDataset



| Field | Required | Type/schema |
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



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| sample_id | True | `string` |
| polygons | True | `array` |
| scores | True | `array` |
| category_ids | True | `array` |
| convention | False | `string` |

## OrientedSample



| Field | Required | Type/schema |
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
| lineage_group | False | `[{'type': 'string'}, {'type': 'null'}]` |
| metadata | False | `object` |

## PluginDescriptor



| Field | Required | Type/schema |
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
| implementation_revision | False | `[{'type': 'string'}, {'type': 'null'}]` |
| execution_status | False | `string` |

## Quantity



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| status | True | `string` |
| value | False | `see schema` |
| unit | False | `[{'type': 'string'}, {'type': 'null'}]` |
| method | False | `[{'type': 'string'}, {'type': 'null'}]` |
| evidence | False | `[{'type': 'string'}, {'type': 'null'}]` |

## ResearchCampaign



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| arms | True | `array` |
| seeds | True | `array` |
| backends | True | `array` |
| constraints | False | `array` |
| phase | False | `string` |
| previous_seeds | False | `array` |
| selection_digest | False | `[{'pattern': '^[a-f0-9]{64}$', 'type': 'string'}, {'type': 'null'}]` |

## RunManifest



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| run_id | True | `string` |
| experiment_digest | True | `string` |
| dataset_digest | True | `string` |
| state | True | `string` |
| created_at | True | `string` |
| finished_at | False | `[{'type': 'string'}, {'type': 'null'}]` |
| failure | False | `[{'additionalProperties': {'type': 'string'}, 'type': 'object'}, {'type': 'null'}]` |
| note | False | `string` |

## Sample



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| image | True | `string` |
| sha256 | True | `string` |
| width | True | `integer` |
| height | True | `integer` |
| source_kind | False | `string` |
| domain | False | `string` |
| sensor | False | `[{'type': 'string'}, {'type': 'null'}]` |
| lineage_group | False | `[{'type': 'string'}, {'type': 'null'}]` |
| parent_ids | False | `array` |
| boxes | False | `array` |
| geospatial | False | `[{'additionalProperties': True, 'type': 'object'}, {'type': 'null'}]` |
| generation | False | `[{'$ref': '#/$defs/GenerationMetadata'}, {'type': 'null'}]` |

## SidecarMapping



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| sample_id_pointer | False | `string` |
| generator | True | `string` |
| generator_version | False | `[{'type': 'string'}, {'type': 'null'}]` |
| simulator | False | `[{'type': 'string'}, {'type': 'null'}]` |
| engine | False | `[{'type': 'string'}, {'type': 'null'}]` |
| fields | True | `array` |
| identity_pointers | False | `object` |
| note | False | `string` |

## SliceExpression



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| name | True | `string` |
| expression | True | `object` |
| level | False | `string` |
| missing_policy | False | `string` |
| metadata_origin | True | `string` |

## Split



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| role | True | `string` |
| sample_ids | True | `array` |

## StageSpec



| Field | Required | Type/schema |
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



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| object_id | True | `string` |
| asset_id | False | `[{'type': 'string'}, {'type': 'null'}]` |
| category | False | `[{'type': 'string'}, {'type': 'null'}]` |
| attributes | False | `object` |

## SyntheticRecord



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| sample_id | True | `string` |
| generator | True | `string` |
| generator_version | False | `[{'type': 'string'}, {'type': 'null'}]` |
| simulator | False | `[{'type': 'string'}, {'type': 'null'}]` |
| simulator_version | False | `[{'type': 'string'}, {'type': 'null'}]` |
| engine | False | `[{'type': 'string'}, {'type': 'null'}]` |
| engine_version | False | `[{'type': 'string'}, {'type': 'null'}]` |
| generation_revision | False | `[{'type': 'string'}, {'type': 'null'}]` |
| generation_environment_digest | False | `[{'pattern': '^[a-f0-9]{64}$', 'type': 'string'}, {'type': 'null'}]` |
| raw_sidecar_digest | False | `[{'pattern': '^[a-f0-9]{64}$', 'type': 'string'}, {'type': 'null'}]` |
| scene_id | False | `[{'type': 'string'}, {'type': 'null'}]` |
| scene_source | False | `[{'type': 'string'}, {'type': 'null'}]` |
| asset_ids | False | `array` |
| seed | False | `[{'minimum': 0, 'type': 'integer'}, {'type': 'null'}]` |
| camera | False | `#/$defs/CameraRecord` |
| planned | False | `object` |
| observed | False | `object` |
| objects | False | `array` |
| annotation_method | False | `[{'type': 'string'}, {'type': 'null'}]` |
| licenses | False | `#/$defs/LicenseInfo` |
| notes | False | `[{'type': 'string'}, {'type': 'null'}]` |

## SyntheticSampleManifest



| Field | Required | Type/schema |
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



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| width | False | `integer` |
| height | False | `integer` |
| overlap_x | False | `integer` |
| overlap_y | False | `integer` |
| resize_width | False | `[{'exclusiveMinimum': 0, 'type': 'integer'}, {'type': 'null'}]` |
| resize_height | False | `[{'exclusiveMinimum': 0, 'type': 'integer'}, {'type': 'null'}]` |
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



| Field | Required | Type/schema |
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



| Field | Required | Type/schema |
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



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| update | True | `integer` |
| stage | True | `string` |
| real_sample_ids | True | `array` |
| synthetic_sample_ids | True | `array` |
| real_loss | False | `[{'type': 'number'}, {'type': 'null'}]` |
| synthetic_loss | False | `[{'type': 'number'}, {'type': 'null'}]` |
| nominal_synthetic_weight | True | `number` |
| real_primary_sample_ids | False | `array` |
| real_replay_sample_ids | False | `array` |
| real_replay_loss | False | `[{'type': 'number'}, {'type': 'null'}]` |
| weighted_total_loss | True | `number` |
| gradient_influence | False | `string` |
| augmentation | False | `string` |

## WorkerPlugin



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| id | True | `string` |
| script | True | `string` |
| script_sha256 | True | `string` |
| interpreter | False | `[{'type': 'string'}, {'type': 'null'}]` |
| protocol_version | False | `string` |
| trust_executable_code | False | `boolean` |
| implementation_revision | False | `[{'type': 'string'}, {'type': 'null'}]` |
| environment_capsule_digest | False | `[{'pattern': '^[a-f0-9]{64}$', 'type': 'string'}, {'type': 'null'}]` |

## WorkerRequest



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| protocol_version | False | `string` |
| operation | True | `string` |
| experiment | False | `[{'additionalProperties': True, 'type': 'object'}, {'type': 'null'}]` |
| manifest | False | `[{'additionalProperties': True, 'type': 'object'}, {'type': 'null'}]` |
| data_root | False | `[{'type': 'string'}, {'type': 'null'}]` |
| output_dir | False | `[{'type': 'string'}, {'type': 'null'}]` |
| checkpoint | False | `[{'additionalProperties': True, 'type': 'object'}, {'type': 'null'}]` |
| final_test_authorization | False | `[{'additionalProperties': True, 'type': 'object'}, {'type': 'null'}]` |

## WorkerResponse



| Field | Required | Type/schema |
|---|---|---|
| schema_version | False | `string` |
| protocol_version | False | `string` |
| status | True | `string` |
| result | False | `object` |
| error | False | `[{'additionalProperties': {'type': 'string'}, 'type': 'object'}, {'type': 'null'}]` |
