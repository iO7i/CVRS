"""Transactional, opt-in named environment management.

Environments live at their final absolute prefix: moving a venv after creation
breaks script shebangs. A repaired environment is a *new* revision. Only a
successful health check changes the small atomic current-revision pointer.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Literal

from cvsubstrate.errors import CVRSError
from cvsubstrate.foundation.lifecycle import process_lock
from cvsubstrate.product.contracts import EnvironmentCommand, EnvironmentPlan, ManagedEnvironmentSpec
from cvsubstrate.product.process import clean_environment, execute
from cvsubstrate.provenance.io import digest, file_digest, read_json, write_json
from cvsubstrate.security import sanitize

PROBE = r'''
import sys, json, platform, importlib.util, importlib.metadata as md
names = json.loads(sys.argv[1])
packages = {}
for d in md.distributions():
    n = d.metadata.get('Name')
    if n: packages[n.lower().replace('_','-')] = d.version
modules = {}
for name in names:
    try: modules[name] = importlib.util.find_spec(name) is not None
    except (ValueError, ImportError, AttributeError): modules[name] = False
print(json.dumps({'python': platform.python_version(), 'executable':sys.executable,
 'prefix':sys.prefix, 'base_prefix':sys.base_prefix, 'platform':platform.platform(),
 'packages':packages, 'modules':modules,
 'marker_environment':{'python_version':'.'.join(platform.python_version().split('.')[:2]),
 'python_full_version':platform.python_version(),'sys_platform':sys.platform,'os_name':__import__('os').name,
 'platform_system':platform.system(),'platform_machine':platform.machine(),
 'platform_release':platform.release(),'platform_version':platform.version(),
 'implementation_name':sys.implementation.name,'platform_python_implementation':platform.python_implementation(),
 'implementation_version':platform.python_version(),'extra':''}}))
'''


def _name(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", value):
        raise ValueError("invalid managed environment name")
    return value


def _python(prefix: Path) -> Path:
    return prefix / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _required_executable(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise CVRSError("DEPENDENCY_UNAVAILABLE", name + " executable is not installed")
    return executable


def probe(interpreter: str, modules: list[str], *, timeout: float = 40) -> dict:
    if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", m) for m in modules):
        raise ValueError("only top-level module metadata probes are allowed")
    result = execute([interpreter, "-I", "-c", PROBE, json.dumps(modules)], timeout=timeout)
    try:
        return json.loads(result["output"].strip().splitlines()[-1])
    except (ValueError, IndexError) as exc:
        raise CVRSError("ENV_PROBE_INVALID", "interpreter did not return the expected observation") from exc


def observation_diff(expected: ManagedEnvironmentSpec, observed: dict) -> dict:
    from packaging.requirements import Requirement
    from packaging.specifiers import SpecifierSet
    from packaging.utils import canonicalize_name
    issues: list[dict[str, Any]] = []
    observed_python = observed.get("python")
    if not isinstance(observed_python, str) or observed_python not in SpecifierSet(expected.python_constraint):
        issues.append({"code": "PYTHON_MISMATCH", "expected": expected.python_constraint,
                       "actual": observed_python})
    packages = {canonicalize_name(k): v for k, v in observed.get("packages", {}).items()}
    for line in expected.requirements:
        requirement = Requirement(line)
        # Evaluate markers using the target interpreter, not the controller.
        target = dict(observed.get("marker_environment", {}))
        if requirement.marker and not target:
            issues.append({"code": "MARKER_UNRESOLVED", "requirement": line})
            continue
        if requirement.marker and not requirement.marker.evaluate(target):
            continue
        version = packages.get(canonicalize_name(requirement.name))
        if version is None or version not in requirement.specifier:
            issues.append({"code": "PACKAGE_MISMATCH", "name": requirement.name,
                           "expected": str(requirement.specifier), "actual": version})
    for module in expected.expected_modules:
        if not observed.get("modules", {}).get(module, False):
            issues.append({"code": "MODULE_MISSING", "module": module})
    return {"status": "HEALTHY_METADATA" if not issues else "UNHEALTHY", "issues": issues,
            "native_model_execution": "NOT_RUN", "cuda_abi_compatibility": "NOT_INFERRED"}


class EnvironmentManager:
    """Manage only prefixes below a caller-selected owned store."""

    def __init__(self, store: str | Path):
        raw = Path(store).absolute()
        if any(p.is_symlink() for p in [raw, *raw.parents]):
            raise CVRSError("ENV_SYMLINK", "managed store must not traverse symlinks")
        self.root = raw.resolve()
        if self.root in {Path('/'), Path.home().resolve(), Path(sys.prefix).resolve()}:
            raise CVRSError("ENV_UNSAFE_ROOT", "choose a dedicated environment-store directory")

    def _owned_root(self) -> None:
        marker = self.root / "CVRS_ENVIRONMENTS.json"
        if self.root.exists() and not marker.exists() and any(self.root.iterdir()):
            raise CVRSError("ENV_UNOWNED", "refusing to adopt a nonempty, unmarked directory")
        self.root.mkdir(parents=True, exist_ok=True)
        if not marker.exists():
            write_json(marker, {"schema_version": "1.0", "purpose": "cvrs-managed-environments"})
        elif read_json(marker).get("purpose") != "cvrs-managed-environments":
            raise CVRSError("ENV_UNOWNED", "environment store marker is invalid")

    def _current(self, name: str) -> dict | None:
        p = self.root / _name(name) / "current.json"
        if any(q.is_symlink() for q in [p, p.parent]):
            raise CVRSError("ENV_SYMLINK", "active environment pointer must not traverse symlinks")
        return read_json(p) if p.is_file() else None

    def _revision_path(self, name: str, revision: str) -> Path:
        if not re.fullmatch(r"r[0-9]{6}-[0-9a-f]{12}", revision):
            raise CVRSError("ENV_REVISION", "invalid environment revision")
        path = self.root / _name(name) / "revisions" / revision
        if any(p.is_symlink() for p in [path, *path.parents] if p.is_relative_to(self.root)):
            raise CVRSError("ENV_SYMLINK", "revision traverses a symlink")
        return path

    def plan(self, value: dict | ManagedEnvironmentSpec, *, operation: Literal["create", "repair", "upgrade"] = "create") -> EnvironmentPlan:
        spec = ManagedEnvironmentSpec.model_validate(value)
        if operation not in {"create", "repair", "upgrade"}:
            raise ValueError("unsupported environment operation")
        current = self._current(spec.name)
        if operation == "create" and current:
            raise CVRSError("ENV_EXISTS", "use repair or upgrade to create a separate revision")
        if operation != "create" and not current:
            raise CVRSError("ENV_MISSING", "create the named environment first")
        parent = self.root / spec.name / "revisions"
        existing = [int(p.name[1:7]) for p in parent.glob("r*-*") if re.fullmatch(r"r\d{6}-[0-9a-f]{12}", p.name)]
        generation = max(existing, default=0) + 1
        revision = f"r{generation:06d}-{digest(spec)[:12]}"
        target = self._revision_path(spec.name, revision)
        prefix = target / "env"
        commands: list[EnvironmentCommand] = []
        inputs: dict[str, str] = {}
        for item in spec.artifacts:
            raw = Path(item.path).absolute()
            if any(q.is_symlink() for q in [raw, *raw.parents]):
                raise CVRSError("ENV_SYMLINK", "local package artifacts must not traverse symlinks")
            p = raw.resolve()
            if not p.is_file() or file_digest(p) != item.sha256:
                raise CVRSError("ENV_ARTIFACT_MISMATCH", "local package artifact is missing or changed")
            if not p.name.endswith(".whl") and not spec.allow_source_builds:
                raise CVRSError("ENV_SOURCE_BUILD_DENIED", "only wheels are accepted without source-build approval")
            inputs[str(p)] = item.sha256
        requirements = str(target / "requirements.txt")
        py = str(_python(prefix))
        if spec.backend == "venv":
            executable = shutil.which(spec.python) or (str(Path(spec.python).resolve()) if Path(spec.python).is_file() else None)
            if executable is None:
                raise CVRSError("ENV_PYTHON_MISSING", "supply an installed interpreter path, or use an explicitly authorized uv Python download")
            inputs[executable] = file_digest(Path(executable))
            commands.append(EnvironmentCommand(stage="create", argv=[executable, "-I", "-m", "venv", str(prefix)]))
        elif spec.backend == "uv":
            executable = shutil.which("uv")
            if not executable:
                raise CVRSError("DEPENDENCY_UNAVAILABLE", "uv executable is not installed")
            argv = [executable, "venv", "--no-config", "--python", spec.python]
            if not spec.allow_python_download:
                argv.append("--no-python-downloads")
            if not spec.allow_network:
                argv.append("--offline")
            commands.append(EnvironmentCommand(stage="create", argv=argv + [str(prefix)]))
        elif spec.backend == "conda":
            executable = shutil.which("conda")
            if not executable:
                raise CVRSError("DEPENDENCY_UNAVAILABLE", "conda executable is not installed")
            if not re.fullmatch(r"3\.\d+(?:\.\d+)?", spec.python):
                raise ValueError("conda recipe python must be an explicit version")
            argv = [executable, "create", "--yes", "--json", "--prefix", str(prefix), "--override-channels"]
            for channel in spec.conda_channels:
                argv += ["--channel", channel]
            if not spec.allow_network:
                argv.append("--offline")
            commands.append(EnvironmentCommand(stage="create", argv=argv + ["python=" + spec.python, "pip", *spec.conda_packages]))
        else:
            executable = shutil.which(spec.backend)
            if not executable:
                raise CVRSError("DEPENDENCY_UNAVAILABLE", spec.backend + " executable is not installed")
            if spec.backend == "docker":
                argv = [executable, "build", "--network", "default" if spec.allow_network else "none", "--iidfile", str(target / "image.id"), str(target / "context")]
            else:
                if not spec.allow_network:
                    raise CVRSError("ENV_OFFLINE_BASE", "Apptainer builds from registry images require explicit network approval; use an existing interpreter for offline work")
                argv = [executable, "build", str(target / "environment.sif"), str(target / "context/Apptainer.def")]
            commands.append(EnvironmentCommand(stage="build", argv=argv, cwd=str(target / "context")))
        if spec.backend in {"venv", "uv", "conda"} and (spec.requirements or spec.artifacts):
            if spec.backend == "uv":
                argv = [_required_executable("uv"), "pip", "install", "--no-config", "--python", py]
                if not spec.allow_network:
                    argv += ["--offline", "--no-index"]
            else:
                argv = [py, "-I", "-m", "pip", "--isolated", "--disable-pip-version-check", "install", "--no-input"]
                if not spec.allow_network:
                    argv.append("--no-index")
            if spec.allow_network:
                argv += ["--index-url", spec.index_url]
            if not spec.allow_source_builds:
                argv += ["--only-binary", ":all:"]
            if spec.require_hashes:
                argv.append("--require-hashes")
            argv += ["--find-links", str(target / "wheels"), "-r", requirements]
            commands.append(EnvironmentCommand(stage="install", argv=argv))
        for command in commands:
            binary = Path(command.argv[0])
            if binary.is_file():
                inputs[str(binary.resolve())] = file_digest(binary)
        warnings = ["Recipe pins are not a proof of CUDA/compiled-operator compatibility.",
                    "Native environments and package installers execute trusted third-party code."]
        if not spec.require_hashes:
            warnings.append("Not a fully hash-locked transitive wheel closure; observed packages will be captured.")
        result = EnvironmentPlan(operation=operation, spec=spec, store=str(self.root), revision=generation,
            revision_dir=str(target), commands=commands, input_hashes=inputs,
            previous_revision=current.get("revision") if current else None,
            network_effects=["Dependency resolution/downloads in the managed environment"] if spec.allow_network else [],
            warnings=warnings)
        result.plan_digest = digest(result.model_dump(mode="json", exclude={"plan_digest"}))
        return result

    def apply(self, value: dict | EnvironmentPlan, *, approve_digest: str) -> dict:
        plan = EnvironmentPlan.model_validate(value)
        if plan.store != str(self.root) or approve_digest != plan.plan_digest:
            raise CVRSError("ENV_APPROVAL", "approve the exact plan for this store")
        expected = digest(plan.model_dump(mode="json", exclude={"plan_digest"}))
        if expected != plan.plan_digest:
            raise CVRSError("ENV_PLAN_TAMPERED", "environment plan has changed")
        self._owned_root()
        with process_lock(self.root / ".operations.lock"):
            refreshed = self.plan(plan.spec, operation=plan.operation)
            if refreshed.plan_digest != plan.plan_digest:
                raise CVRSError("ENV_PLAN_STALE", "store or input assets changed; review a new plan")
            target = Path(plan.revision_dir)
            target.mkdir(parents=True, exist_ok=False)
            write_json(target / "plan.json", plan)
            write_json(target / "spec.json", plan.spec)
            state = {"status": "CREATING", "revision": target.name, "plan_digest": plan.plan_digest,
                     "started_at_ns": time.time_ns(), "previous_revision": plan.previous_revision}
            write_json(target / "state.json", state)
            try:
                self._prepare(plan, target)
                results = []
                for index, command in enumerate(plan.commands):
                    # Input hashes rechecked immediately before every executable operation.
                    for path, sha in plan.input_hashes.items():
                        if file_digest(Path(path)) != sha:
                            raise CVRSError("ENV_INPUT_CHANGED", "a reviewed input changed before execution")
                    results.append(execute(command.argv, cwd=Path(command.cwd) if command.cwd else target,
                        timeout=plan.spec.timeout_seconds, log=target / f"command-{index}.json"))
                observed = self._observe_revision(target, plan.spec)
                health = observation_diff(plan.spec, observed)
                write_json(target / "observation.json", observed)
                write_json(target / "health.json", health)
                if health["status"] != "HEALTHY_METADATA":
                    raise CVRSError("ENV_UNHEALTHY", "new revision does not satisfy the declared recipe; old revision remains active")
                state.update(status="READY", finished_at_ns=time.time_ns(), observation_digest=digest(observed))
                write_json(target / "state.json", state)
                write_json(self.root / plan.spec.name / "current.json", {"revision": target.name,
                    "spec_digest": digest(plan.spec), "activated_at_ns": time.time_ns()})
                return {"status": "READY", "name": plan.spec.name, "revision": target.name,
                        "python": str(_python(target / "env")) if plan.spec.backend in {"venv", "uv", "conda"} else None,
                        "health": health, "previous_revision_preserved": plan.previous_revision,
                        "native_model_execution": "NOT_RUN"}
            except BaseException as exc:
                state.update(status="CANCELLED" if isinstance(exc, KeyboardInterrupt) else "FAILED",
                             finished_at_ns=time.time_ns(), error=sanitize(str(exc)))
                write_json(target / "state.json", state)
                raise

    def _prepare(self, plan: EnvironmentPlan, target: Path) -> None:
        spec = plan.spec
        wheels = target / "wheels"
        wheels.mkdir()
        lines = list(spec.requirements)
        for item in spec.artifacts:
            source = Path(item.path).resolve()
            dest = wheels / source.name
            if dest.exists():
                raise ValueError("local wheel filenames must be unique")
            shutil.copyfile(source, dest)
            if file_digest(dest) != item.sha256:
                raise CVRSError("ENV_ARTIFACT_MISMATCH", "copied wheel does not match the approved content")
            lines.append(str(dest) + (" --hash=sha256:" + item.sha256 if spec.require_hashes else ""))
        (target / "requirements.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        if spec.backend not in {"docker", "apptainer"}:
            return
        base_image = spec.base_image
        if not base_image:
            raise CVRSError("ENV_BASE_IMAGE", "container environments require an explicit base image")
        context = target / "context"
        context.mkdir()
        shutil.copytree(wheels, context / "wheels")
        container_lines = list(spec.requirements) + ["/opt/cvrs/wheels/" + Path(a.path).name +
            (" --hash=sha256:" + a.sha256 if spec.require_hashes else "") for a in spec.artifacts]
        (context / "requirements.txt").write_text("\n".join(container_lines) + "\n")
        args = ["python", "-m", "pip", "--isolated", "install", "--no-input", "--disable-pip-version-check"]
        if not spec.allow_network:
            args.append("--no-index")
        else:
            args += ["--index-url", spec.index_url]
        if not spec.allow_source_builds:
            args += ["--only-binary", ":all:"]
        if spec.require_hashes:
            args.append("--require-hashes")
        args += ["--find-links", "/opt/cvrs/wheels", "-r", "/opt/cvrs/requirements.txt"]
        import shlex
        install = shlex.join(args) if container_lines else "python --version"
        (context / "Dockerfile").write_text(f"FROM {base_image}\nCOPY . /opt/cvrs/\nRUN {install}\nWORKDIR /work\n")
        (context / "Apptainer.def").write_text(f"Bootstrap: docker\nFrom: {base_image}\n\n%files\n    requirements.txt /opt/cvrs/requirements.txt\n    wheels /opt/cvrs/wheels\n\n%post\n    {install}\n\n%runscript\n    exec python \"$@\"\n")
        if spec.backend == "docker" and not spec.allow_network:
            execute([_required_executable("docker"), "image", "inspect", base_image],
                    timeout=60, log=target / "base-image-check.json")

    def _observe_revision(self, target: Path, spec: ManagedEnvironmentSpec) -> dict:
        if spec.backend in {"venv", "uv", "conda"}:
            result = probe(str(_python(target / "env")), spec.expected_modules)
            # pip check captures declared dependency inconsistencies; no network is used.
            if (target / "env/pyvenv.cfg").exists() and spec.backend == "uv" and "pip" not in result["packages"]:
                check = [_required_executable("uv"), "pip", "check", "--python", str(_python(target / "env")), "--no-config"]
            else:
                check = [str(_python(target / "env")), "-I", "-m", "pip", "--isolated", "check"]
            execute(check, timeout=60, log=target / "dependency-check.json")
            result["dependency_check"] = "PASSED"
            return result
        if spec.backend == "docker":
            image = (target / "image.id").read_text().strip()
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
                raise ValueError("Docker build did not produce a digest")
            argv = [_required_executable("docker"), "run", "--rm", "--network", "none", image,
                    "python", "-I", "-c", PROBE, json.dumps(spec.expected_modules)]
        else:
            image = str(target / "environment.sif")
            argv = [_required_executable("apptainer"), "exec", "--cleanenv", image,
                    "python", "-I", "-c", PROBE, json.dumps(spec.expected_modules)]
        output = execute(argv, timeout=120, log=target / "probe.json")
        result = json.loads(output["output"].strip().splitlines()[-1])
        result["container_image"] = image
        return result

    def list(self) -> list[dict]:
        if not self.root.is_dir():
            return []
        result = []
        for p in sorted(self.root.iterdir()):
            if not p.is_dir() or p.is_symlink() or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", p.name):
                continue
            current = self._current(p.name)
            result.append({"name": p.name, "current": current, "revisions": [
                read_json(s) for s in sorted((p / "revisions").glob("*/state.json"))]})
        return result

    def doctor(self, name: str) -> dict:
        current = self._current(name)
        if not current:
            raise CVRSError("ENV_MISSING", "environment is not active")
        target = self._revision_path(name, current["revision"])
        spec = ManagedEnvironmentSpec.model_validate(read_json(target / "spec.json"))
        try:
            observation = self._observe_revision(target, spec)
            health = observation_diff(spec, observation)
            return {"name": name, "revision": current["revision"], "health": health,
                    "observation": observation, "native_execution": "NOT_RUN"}
        except CVRSError as exc:
            return {"name": name, "revision": current["revision"], "health": {"status": "UNHEALTHY"},
                    "error": exc.as_dict(), "remediation": "Create a new repair revision; the active prefix is not modified."}

    def repair_plan(self, name: str, *, replacement_spec: dict | None = None) -> EnvironmentPlan:
        current = self._current(name)
        if not current:
            raise CVRSError("ENV_MISSING", "there is no active revision to repair")
        old = read_json(self._revision_path(name, current["revision"]) / "spec.json")
        spec = replacement_spec or old
        if spec.get("name") != name:
            raise ValueError("repair/upgrade must keep the same managed name")
        return self.plan(spec, operation="upgrade" if replacement_spec else "repair")

    def activate(self, name: str, revision: str, *, confirm: bool = False) -> dict:
        target = self._revision_path(name, revision)
        state = read_json(target / "state.json")
        if state.get("status") != "READY":
            raise CVRSError("ENV_NOT_READY", "cannot activate a failed or partial revision")
        spec = ManagedEnvironmentSpec.model_validate(read_json(target / "spec.json"))
        report = {"name": name, "revision": revision, "previous": self._current(name), "applied": False}
        if not confirm:
            return report
        with process_lock(self.root / ".operations.lock"):
            health = observation_diff(spec, self._observe_revision(target, spec))
            if health["status"] != "HEALTHY_METADATA":
                raise CVRSError("ENV_UNHEALTHY", "revision is no longer healthy")
            write_json(self.root / name / "current.json", {"revision": revision, "spec_digest": digest(spec),
                                                        "activated_at_ns": time.time_ns()})
        report["applied"] = True
        return report

    def interpreter(self, name: str) -> str:
        current = self._current(name)
        if not current:
            raise CVRSError("ENV_MISSING", name)
        target = self._revision_path(name, current["revision"])
        spec = read_json(target / "spec.json")
        if spec["backend"] not in {"venv", "uv", "conda"}:
            raise CVRSError("ENV_CONTAINER", "container environment requires a container launch plan, not a fake Python path")
        return str(_python(target / "env"))

    def diff(self, left: str, right: str) -> dict:
        a, b = self.doctor(left), self.doctor(right)
        x, y = a.get("observation", {}).get("packages", {}), b.get("observation", {}).get("packages", {})
        return {"left": left, "right": right, "left_health": a["health"], "right_health": b["health"],
                "packages": [{"name": k, "left": x.get(k), "right": y.get(k)} for k in sorted(x.keys() | y.keys()) if x.get(k) != y.get(k)],
                "binary_compatibility": "NOT_INFERRED"}
