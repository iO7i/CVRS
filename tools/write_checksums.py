"""Write deterministic SHA-256 sums for a qualification directory."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    if args.out.exists() and not args.replace:
        parser.error(f"refusing to overwrite existing checksum file: {args.out}")
    rows = []
    for path in sorted(args.root.rglob("*")):
        if path.is_file() and path != args.out:
            rows.append(f"{sha256(path)}  {path.relative_to(args.root).as_posix()}")
    args.out.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"checksummed={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
