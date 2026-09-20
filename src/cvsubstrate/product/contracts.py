"""Strict product contracts. Package and protocol versions are independent."""
from __future__ import annotations

import re
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProductContract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    schema_version: Literal["1.0"] = "1.0"


class LocalPackageArtifact(ProductContract):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ManagedEnvironmentSpec(ProductContract):
    name: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")
    backend: Literal["venv", "uv", "conda", "docker", "apptainer"] = "venv"
    pack: str = "core"
    python: str
    python_constraint: str = ">=3.11"
    requirements: list[str] = Field(default_factory=list)
    artifacts: list[LocalPackageArtifact] = Field(default_factory=list)
    expected_modules: list[str] = Field(default_factory=list)
    conda_packages: list[str] = Field(default_factory=list)
    conda_channels: list[str] = Field(default_factory=lambda: ["conda-forge"])
    base_image: str | None = None
    allow_network: bool = False
    allow_python_download: bool = False
    allow_source_builds: bool = False
    index_url: str = "https://pypi.org/simple"
    require_hashes: bool = False
    timeout_seconds: float = Field(default=1200, gt=0, le=86400)
    notes: str = ""

    @field_validator("python", "base_image")
    @classmethod
    def single_line(cls, value: str | None) -> str | None:
        if value and ("\n" in value or "\r" in value or "\x00" in value):
            raise ValueError("interpreter/image must be a single value")
        return value

    @field_validator("expected_modules")
    @classmethod
    def top_level_modules(cls, values: list[str]) -> list[str]:
        if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v) for v in values):
            raise ValueError("probe only top-level module names without executing parent packages")
        return sorted(set(values))

    @field_validator("requirements")
    @classmethod
    def pinned_requirements(cls, values: list[str]) -> list[str]:
        from packaging.requirements import Requirement
        result = []
        for value in values:
            if any(c in value for c in "\n\r\x00") or value.lstrip().startswith("-"):
                raise ValueError("requirements cannot contain pip flags or additional lines")
            # PEP 508 requirements, not arbitrary requirements-file syntax.
            requirement = Requirement(value)
            if requirement.url:
                raise ValueError("direct URL/VCS installs need a separately downloaded, hashed local artifact")
            pins = list(requirement.specifier)
            if len(pins) != 1 or pins[0].operator != "==" or "*" in pins[0].version:
                raise ValueError("managed environments require exact package==version pins")
            result.append(str(requirement))
        return sorted(set(result))

    @field_validator("index_url")
    @classmethod
    def public_index(cls, value: str) -> str:
        from urllib.parse import urlsplit
        url = urlsplit(value)
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("index must be an HTTPS URL without embedded credentials/query")
        return value

    @model_validator(mode="after")
    def consistent_policy(self):
        from packaging.specifiers import SpecifierSet
        SpecifierSet(self.python_constraint)
        if self.allow_python_download and (self.backend != "uv" or not self.allow_network):
            raise ValueError("Python downloads require uv plus explicit network permission")
        if self.require_hashes and self.requirements:
            raise ValueError("hash-locked installation uses local artifacts for the full dependency closure")
        if self.backend in {"docker", "apptainer"}:
            if not self.base_image or not re.fullmatch(r"[a-zA-Z0-9._:/-]+@sha256:[0-9a-f]{64}", self.base_image):
                raise ValueError("container environment requires a digest-pinned base image")
        for item in self.conda_packages + self.conda_channels:
            if not re.fullmatch(r"[A-Za-z0-9_.*+:/=<>!,-]+", item) or item.startswith("-"):
                raise ValueError("unsafe conda package/channel declaration")
        return self


class EnvironmentCommand(ProductContract):
    argv: list[str]
    stage: Literal["create", "install", "build"]
    cwd: str | None = None


class EnvironmentPlan(ProductContract):
    operation: Literal["create", "repair", "upgrade"]
    spec: ManagedEnvironmentSpec
    store: str
    revision: int = Field(ge=1)
    revision_dir: str
    commands: list[EnvironmentCommand]
    input_hashes: dict[str, str]
    previous_revision: str | None = None
    network_effects: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    plan_digest: str = ""


class CompatibilityReceipt(ProductContract):
    subject_id: str
    protocol: str = "1.0"
    task: str
    operation: str
    implementation: Literal["AVAILABLE", "UNSUPPORTED"]
    execution: Literal["NOT_RUN", "SUCCEEDED", "FAILED", "BLOCKED"] = "NOT_RUN"
    reference_evaluation: Literal["NOT_RUN", "MATCHED", "MISMATCH"] = "NOT_RUN"
    reproduction: Literal["NOT_RUN", "LOCAL", "INDEPENDENT_ATTESTED"] = "NOT_RUN"
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ProductFinding(ProductContract):
    rule_id: str
    severity: Literal["INFO", "WARN", "BLOCK", "UNKNOWN"]
    message: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    remediation: str | None = None
    rule_version: str = "1.0"


class LaunchPlan(ProductContract):
    repository: str
    package: str
    release_version: str
    readiness: Literal["OWNER_ACTIONS_REQUIRED", "READY_FOR_REVIEW"]
    operations: list[dict[str, Any]]
    owner_actions: list[str]
    approval_digest: str = ""
    executed: bool = False


PRODUCT_SCHEMAS = [
    LocalPackageArtifact, ManagedEnvironmentSpec, EnvironmentCommand,
    EnvironmentPlan, CompatibilityReceipt, ProductFinding, LaunchPlan,
]
