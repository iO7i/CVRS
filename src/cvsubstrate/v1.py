"""Frozen finite public facade for Slices 1–5 closure.

The facade/schema contracts are versioned independently from package version.
Native implementation modules remain provisional pending external integration.
"""
from cvsubstrate.foundation.identity import content_id,COMPONENT_VERSIONS,ProvenanceGraph,ProvenanceNode,ProvenanceEdge
from cvsubstrate.foundation.lifecycle import CancellationToken,Cancelled,process_lock,transition
from cvsubstrate.artifacts.managed import ManagedArtifactStore
from cvsubstrate.artifacts.dependencies import Dependency,DependencyClosure,inspect_closure
from cvsubstrate.execution.session import run_session
from cvsubstrate.heritage.closure import config_closure,preserve_closure
from cvsubstrate.heritage.checkpoint_v1 import diff_checkpoints,transform_checkpoint
from cvsubstrate.campaigns.native import NativeCampaign,NativeStage,compile_native_campaign,run_native_campaign
from cvsubstrate.datasets.sensors import BandSpec,SensorSpec,GeoSceneSpec
from cvsubstrate.data.asset_lineage import SourceAsset,SampleLineage,AssetLineage,check_asset_leakage
from cvsubstrate.streaming.tasks import execute_task_stream,SpatialPredictionIndex,ResourceBudget
from cvsubstrate.vision.prompts import PromptSet,PromptAtom,ReferenceAsset,negotiate_prompts
from cvsubstrate.vision.assets import VisionModelDescriptor,VisionAsset,inspect_assets
from cvsubstrate.vision.ontology import ConceptOntology,Concept,evaluate_open_set
from cvsubstrate.research.claims import ScientificClaim,EffectObservation,EvidenceAttempt,IndependenceAttestation,ActorIdentity,EvidenceEdge
from cvsubstrate.research.federated import FederatedRegistry,migrate_registry_v1
from cvsubstrate.research.evaluators import reevaluate_task
from cvsubstrate.research.signing import keygen,sign_payload,verify_signature
from cvsubstrate.research.task_access import authorize_task_evaluation
from cvsubstrate.research.capture_v2 import capture_comparison
from cvsubstrate.vision.trajectories import execute_trajectory,continue_prompt_step
from cvsubstrate.analysis.population import population_slice
# Keep this finite facade explicit; importing a helper must not export it.
__all__ = [
    'content_id',
    'COMPONENT_VERSIONS',
    'ProvenanceGraph',
    'ProvenanceNode',
    'ProvenanceEdge',
    'CancellationToken',
    'Cancelled',
    'process_lock',
    'transition',
    'ManagedArtifactStore',
    'Dependency',
    'DependencyClosure',
    'inspect_closure',
    'run_session',
    'config_closure',
    'preserve_closure',
    'diff_checkpoints',
    'transform_checkpoint',
    'NativeCampaign',
    'NativeStage',
    'compile_native_campaign',
    'run_native_campaign',
    'BandSpec',
    'SensorSpec',
    'GeoSceneSpec',
    'SourceAsset',
    'SampleLineage',
    'AssetLineage',
    'check_asset_leakage',
    'execute_task_stream',
    'SpatialPredictionIndex',
    'ResourceBudget',
    'PromptSet',
    'PromptAtom',
    'ReferenceAsset',
    'negotiate_prompts',
    'VisionModelDescriptor',
    'VisionAsset',
    'inspect_assets',
    'ConceptOntology',
    'Concept',
    'evaluate_open_set',
    'ScientificClaim',
    'EffectObservation',
    'EvidenceAttempt',
    'IndependenceAttestation',
    'ActorIdentity',
    'EvidenceEdge',
    'FederatedRegistry',
    'migrate_registry_v1',
    'reevaluate_task',
    'keygen',
    'sign_payload',
    'verify_signature',
    'authorize_task_evaluation',
    'capture_comparison',
    'execute_trajectory',
    'continue_prompt_step',
    'population_slice',
]
