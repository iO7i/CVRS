"""Build a deterministic offline file inventory for a CVRS workspace."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


EXCLUDED_DIR_NAMES = frozenset(
    {
        ".git", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv-alpha",
        ".venv-cvrs", ".venv-nativeqa", ".venv-quality", ".venv-controller",
        ".venv-tier1-evaluator", ".venv-torchgeo", ".venv-fiftyone", ".alpha-docs-site",
        ".alpha-docs-site-2", "fiftyone-db", "runs", "build", "dist", "__pycache__",
    }
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inventory(root: Path) -> dict[str, object]:
    root = root.resolve()
    files: list[dict[str, object]] = []
    symlinks: list[str] = []
    skipped: list[str] = []
    for current, dirs, names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_dirs: list[str] = []
        for name in sorted(dirs):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if name in EXCLUDED_DIR_NAMES:
                skipped.append(relative)
                continue
            if path.is_symlink():
                symlinks.append(relative)
                continue
            kept_dirs.append(name)
        dirs[:] = kept_dirs
        for name in sorted(names):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                symlinks.append(relative)
                continue
            if path.suffix in {".pyc", ".pyo"} or not path.is_file():
                skipped.append(relative)
                continue
            files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    files.sort(key=lambda row: str(row["path"]))
    file_map_digest = hashlib.sha256(
        json.dumps(files, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "schema": "cvrs.offline-source-inventory.v1",
        "root": str(root),
        "files": files,
        "file_count": len(files),
        "bytes": sum(int(row["bytes"]) for row in files),
        "file_map_sha256": file_map_digest,
        "symlinks": sorted(symlinks),
        "skipped": sorted(skipped),
        "limits": [
            "This is a byte inventory, not a license, vulnerability, or execution certification.",
            "Excluded directories are explicitly listed and are not copied into the clean workspace.",
            "No model, dataset, credential, or external path is read by this tool.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error(f"refusing to overwrite existing evidence: {args.out}")
    value = inventory(args.root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"file_count": value["file_count"], "bytes": value["bytes"], "file_map_sha256": value["file_map_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
