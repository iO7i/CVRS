"""Run a deterministic TorchGeo geospatial window smoke on a local fixture."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
import torchgeo
from rasterio.transform import from_origin
from torchgeo.datasets import RasterDataset
from torchgeo.samplers import GridGeoSampler


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error(f"refusing to overwrite output: {args.out}")
    args.out.mkdir(parents=True)
    fixture = args.out / "fixture_epsg32637.tif"
    height = width = 64
    rows = np.arange(height, dtype=np.uint16)[:, None]
    cols = np.arange(width, dtype=np.uint16)[None, :]
    data = np.stack(
        [
            np.broadcast_to(rows, (height, width)),
            np.broadcast_to(cols, (height, width)),
            np.add(rows, cols, dtype=np.uint16),
        ]
    )
    with rasterio.open(
        fixture,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=3,
        dtype="uint16",
        crs="EPSG:32637",
        transform=from_origin(500000, 3600064, 1, 1),
    ) as dataset:
        dataset.write(data)

    raster = RasterDataset(paths=fixture, crs="EPSG:32637", res=1)
    sampler = GridGeoSampler(raster, size=32, stride=32)
    samples = []
    for index in sampler:
        sample = raster[index]
        samples.append(
            {
                "index": [index[0].start, index[0].stop, index[1].start, index[1].stop],
                "shape": list(sample["image"].shape),
                "bounds": [float(value) for value in sample["bounds"]],
                "transform": [float(value) for value in sample["transform"]],
                "sum": int(sample["image"].sum().item()),
            }
        )
    report = {
        "schema": "cvrs.rq002.torchgeo-smoke.v1",
        "status": "PASS_NATIVE_GEOTIFF_WINDOW_SMOKE" if len(samples) == 4 else "FAIL_WINDOW_COUNT",
        "torchgeo_version": torchgeo.__version__,
        "fixture": {
            "path": fixture.name,
            "sha256": sha256(fixture),
            "shape": [3, height, width],
            "crs": "EPSG:32637",
            "resolution": [1.0, 1.0],
        },
        "sampler": {"type": "GridGeoSampler", "size_pixels": [32, 32], "stride_pixels": [32, 32]},
        "windows": samples,
        "limits": [
            "This is a native TorchGeo geospatial-window smoke on a deterministic local fixture.",
            "It does not qualify a public GeoTIFF AOI or any model lane.",
            "The public geospatial AOI remains unresolved and must be separately locked before acquisition.",
        ],
    }
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    files = sorted(path for path in args.out.rglob("*") if path.is_file() and path.name != "checksums.sha256")
    (args.out / "checksums.sha256").write_text(
        "\n".join(f"{sha256(path)}  {path.relative_to(args.out).as_posix()}" for path in files) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": report["status"], "windows": len(samples), "torchgeo_version": torchgeo.__version__}))
    return 0 if report["status"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
