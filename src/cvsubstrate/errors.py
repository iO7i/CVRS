"""Stable, machine-readable errors across the CLI and worker boundary."""

class CVRSError(Exception):

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

    def as_dict(self) -> dict:
        return {'code': self.code, 'message': self.message}


class TypedCVRSError(CVRSError):
    code_value = 'CVRS_ERROR'
    def __init__(self,message): super().__init__(self.code_value,message)

class DependencyUnavailable(TypedCVRSError): code_value='DEPENDENCY_UNAVAILABLE'
class UnsupportedCapability(TypedCVRSError): code_value='UNSUPPORTED_CAPABILITY'
class SchemaMismatch(TypedCVRSError): code_value='SCHEMA_MISMATCH'
class DataIntegrityError(TypedCVRSError): code_value='DATA_INTEGRITY'
class ConfigResolutionError(TypedCVRSError): code_value='CONFIG_RESOLUTION'
class CheckpointMismatch(TypedCVRSError): code_value='CHECKPOINT_MISMATCH'
class PredictionConversionError(TypedCVRSError): code_value='PREDICTION_CONVERSION'
class EvaluatorUnavailable(TypedCVRSError): code_value='EVALUATOR_UNAVAILABLE'
class BenchmarkViolation(TypedCVRSError): code_value='BENCHMARK_VIOLATION'
class ProtectedSplitViolation(TypedCVRSError): code_value='PROTECTED_SPLIT'
class ArtifactIntegrityError(TypedCVRSError): code_value='ARTIFACT_INTEGRITY'
class WorkerProtocolError(TypedCVRSError): code_value='WORKER_PROTOCOL'


def public_error(exc):
    """Stable public categories. Preserve diagnostics separately from error code."""
    if isinstance(exc,CVRSError):return exc.as_dict()
    if isinstance(exc,ImportError):code='DEPENDENCY_UNAVAILABLE'
    elif isinstance(exc,FileNotFoundError):code='ARTIFACT_MISSING'
    elif isinstance(exc,PermissionError):code='PERMISSION_DENIED'
    elif isinstance(exc,TimeoutError):code='DEADLINE_EXCEEDED'
    elif isinstance(exc,(ValueError,KeyError,TypeError)):code='VALIDATION_ERROR'
    elif isinstance(exc,OSError):code='IO_ERROR'
    else:code='INTERNAL_ERROR'
    return {'code':code,'message':str(exc)}
