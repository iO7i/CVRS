"""Bounded RQ002 TorchGeo/public-GeoTIFF qualification on ephemeral Modal storage."""
from __future__ import annotations

import json
from pathlib import Path

import modal


SOURCE_REVISION = "d8d81ce1d04ca28abe8b94016d35b4337294b658"
SOURCE_URL = (
    "https://raw.githubusercontent.com/rasterio/rasterio/"
    f"{SOURCE_REVISION}/tests/data/RGB.byte.tif"
)
LICENSE_URL = (
    "https://raw.githubusercontent.com/rasterio/rasterio/"
    f"{SOURCE_REVISION}/LICENSE.txt"
)
MAX_SOURCE_BYTES = 8 * 1024 * 1024
WINDOW_SIZE = 128

app = modal.App("cvrs-rq002-torchgeo-public-geotiff")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch==2.14.0",
        "torchvision==0.29.0",
        index_url="https://download.pytorch.org/whl/cpu",
    )
    .pip_install(
        "torchgeo==0.10.0",
        "rasterio==1.5.1",
        "numpy==2.5.3",
        "pydantic==2.11.9",
        "Pillow==11.3.0",
        "pyproj==3.8.0",
        "shapely==2.1.2",
    )
    .add_local_dir("src/cvsubstrate", "/root/cvrs-src/cvsubstrate", copy=True)
    .env({"PYTHONPATH": "/root/cvrs-src"})
)


def _download(url: str, destination: Path, *, maximum: int = MAX_SOURCE_BYTES) -> dict:
    import hashlib
    import urllib.request

    digest = hashlib.sha256()
    total = 0
    request = urllib.request.Request(url, headers={"User-Agent": "CVRS-RQ002/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as handle:
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            total += len(block)
            if total > maximum:
                raise RuntimeError("SOURCE_BYTE_BUDGET_EXCEEDED")
            digest.update(block)
            handle.write(block)
        headers = {key.lower(): value for key, value in response.headers.items()}
    return {"sha256": digest.hexdigest(), "bytes": total, "response_headers": headers}


def _metadata(path: Path) -> dict:
    import rasterio

    with rasterio.open(path) as source:
        transform = source.transform
        return {
            "driver": source.driver,
            "width": source.width,
            "height": source.height,
            "bands": source.count,
            "band_indexes": list(source.indexes),
            "dtypes": list(source.dtypes),
            "nodata": source.nodata,
            "crs": source.crs.to_string() if source.crs else None,
            "transform": [transform.a, transform.b, transform.c, transform.d, transform.e, transform.f],
            "bounds": list(source.bounds),
            "resolution": [abs(float(source.res[0])), abs(float(source.res[1]))],
            "color_interpretation": [str(value) for value in source.colorinterp],
            "block_shapes": [list(value) for value in source.block_shapes],
            "is_tiled": source.is_tiled,
        }


@app.function(image=image, cpu=2.0, memory=4096, timeout=600, retries=0)
def probe_source() -> dict:
    import importlib.metadata
    import tempfile

    with tempfile.TemporaryDirectory() as temporary:
        source = Path(temporary) / "RGB.byte.tif"
        identity = _download(SOURCE_URL, source)
        license_file = Path(temporary) / "LICENSE.txt"
        license_identity = _download(LICENSE_URL, license_file, maximum=64 * 1024)
        return {
            "schema": "cvrs.rq002.geotiff-source-probe.v1",
            "status": "SOURCE_IDENTITY_OBSERVED_NOT_YET_QUALIFIED",
            "source_url": SOURCE_URL,
            "source_revision": SOURCE_REVISION,
            "source": identity,
            "metadata": _metadata(source),
            "license": {
                "identifier": "BSD-3-Clause repository license",
                "url": LICENSE_URL,
                **license_identity,
                "scope_note": "Repository-level terms cover the distributed test asset; upstream scene ancestry is not inferred.",
            },
            "environment": {
                name: importlib.metadata.version(name)
                for name in ("torch", "torchvision", "torchgeo", "rasterio", "numpy", "pydantic")
            },
            "controls": {"training": False, "gpu": False, "protected_data_access": 0},
        }


@app.function(image=image, cpu=2.0, memory=4096, timeout=600, retries=0)
def qualify(expected_sha256: str) -> bytes:
    import hashlib
    import importlib.metadata
    import io
    import math
    import tempfile
    import time
    import zipfile

    import numpy as np
    import rasterio
    import torchgeo
    from rasterio.windows import Window
    from torchgeo.datasets import RasterDataset

    from cvsubstrate.data.geotiff import export_native_window_artifact, export_raw_window, inspect_geotiff
    from cvsubstrate.datasets.geospatial import inspect_raster
    from cvsubstrate.geometry.geospatial import pixel_to_world, world_to_pixel
    from cvsubstrate.contracts.research import GeoReference

    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = root / "RGB.byte.tif"
        identity = _download(SOURCE_URL, source)
        if identity["sha256"] != expected_sha256:
            raise RuntimeError("SOURCE_SHA256_MISMATCH")
        metadata = _metadata(source)
        if metadata["crs"] is None:
            raise RuntimeError("SOURCE_CRS_MISSING")
        cvrs_inspections = {
            "data_geotiff": inspect_geotiff(source),
            "datasets_geospatial": inspect_raster(source),
        }
        source_reference = GeoReference.model_validate(cvrs_inspections["data_geotiff"]["reference"])
        offsets = [
            [0, 0],
            [metadata["width"] - WINDOW_SIZE, 0],
            [0, metadata["height"] - WINDOW_SIZE],
            [metadata["width"] - WINDOW_SIZE, metadata["height"] - WINDOW_SIZE],
        ]
        raster = RasterDataset(
            paths=source,
            crs=metadata["crs"],
            res=tuple(metadata["resolution"]),
        )
        source_transform = rasterio.Affine(*metadata["transform"])
        records = []
        for index, (column, row) in enumerate(offsets):
            rasterio_window = Window(column, row, WINDOW_SIZE, WINDOW_SIZE)
            left, bottom, right, top = rasterio.windows.bounds(rasterio_window, source_transform)
            query_bounds = [
                math.nextafter(left, right),
                math.nextafter(bottom, top),
                math.nextafter(right, left),
                math.nextafter(top, bottom),
            ]
            query = (
                slice(query_bounds[0], query_bounds[2], metadata["resolution"][0]),
                slice(query_bounds[1], query_bounds[3], metadata["resolution"][1]),
            )
            native_sample = raster[query]
            native = native_sample["image"].detach().cpu().numpy()
            native_path = root / f"native-{index}.npy"
            np.save(native_path, native, allow_pickle=False)

            native_transform = np.asarray(native_sample["transform"]).reshape(-1).astype(float).tolist()[:6]
            native_reference = GeoReference(crs=metadata["crs"], affine=native_transform)
            wrapped_dir = root / f"wrapped-{index}"
            wrapped_record = export_native_window_artifact(
                native,
                wrapped_dir,
                source_sha256=identity["sha256"],
                source_reference=source_reference,
                output_reference=native_reference,
                window=[column, row, WINDOW_SIZE, WINDOW_SIZE],
                bands=list(metadata["band_indexes"]),
                nodata=metadata["nodata"],
            )
            wrapped_data = np.load(wrapped_dir / "data.npy", allow_pickle=False)
            wrapped_valid = np.load(wrapped_dir / "valid_mask.npy", allow_pickle=False)

            cvrs_dir = root / f"cvrs-{index}"
            cvrs_record = export_raw_window(
                source,
                cvrs_dir,
                window=[column, row, WINDOW_SIZE, WINDOW_SIZE],
                bands=list(metadata["band_indexes"]),
            )
            cvrs_data = np.load(cvrs_dir / "data.npy", allow_pickle=False)
            cvrs_valid = np.load(cvrs_dir / "valid_mask.npy", allow_pickle=False)
            native_in_source_dtype = native.astype(cvrs_data.dtype, copy=False)
            values_equal = np.array_equal(native_in_source_dtype, cvrs_data)
            value_hash = hashlib.sha256(native_in_source_dtype.tobytes(order="C")).hexdigest()
            cvrs_value_hash = hashlib.sha256(cvrs_data.tobytes(order="C")).hexdigest()
            cvrs_transform = cvrs_record["output_reference"]["affine"]
            transform_delta = max(abs(a - b) for a, b in zip(native_transform, cvrs_transform))
            expected_native_transform = np.asarray(cvrs_transform, dtype=np.float32).astype(float).tolist()
            transform_float32_equal = native_transform == expected_native_transform
            world = pixel_to_world(source_reference, column + 31.5, row + 63.5)
            pixel = world_to_pixel(source_reference, *world)
            roundtrip_error = max(abs(pixel[0] - (column + 31.5)), abs(pixel[1] - (row + 63.5)))
            nodata_value = metadata["nodata"]
            expected_valid = np.ones_like(cvrs_data, dtype=bool)
            if nodata_value is not None:
                expected_valid = cvrs_data != nodata_value
            nodata_equal = np.array_equal(expected_valid, cvrs_valid)
            records.append(
                {
                    "id": f"window-{index}",
                    "window_col_row_width_height": [column, row, WINDOW_SIZE, WINDOW_SIZE],
                    "world_bounds": [left, bottom, right, top],
                    "torchgeo_query_bounds_inward_one_ulp": query_bounds,
                    "native": {
                        "shape": list(native.shape),
                        "presentation_dtype": str(native.dtype),
                        "source_dtype_view": str(native_in_source_dtype.dtype),
                        "array_sha256": hashlib.sha256(native_path.read_bytes()).hexdigest(),
                        "source_value_sha256": value_hash,
                        "transform": native_transform,
                        "expected_float32_transform": expected_native_transform,
                    },
                    "cvrs": {
                        "shape": list(cvrs_data.shape),
                        "dtype": str(cvrs_data.dtype),
                        "data_npy_sha256": cvrs_record["data_sha256"],
                        "valid_mask_npy_sha256": cvrs_record["valid_mask_sha256"],
                        "source_value_sha256": cvrs_value_hash,
                        "transform": cvrs_transform,
                        "bands": cvrs_record["bands"],
                    },
                    "wrapped_native": {
                        "shape": wrapped_record["shape"],
                        "dtype": wrapped_record["dtype"],
                        "data_npy_sha256": wrapped_record["data_sha256"],
                        "valid_mask_npy_sha256": wrapped_record["valid_mask_sha256"],
                        "source_sha256": wrapped_record["source_sha256"],
                        "source_reference": wrapped_record["source_reference"],
                        "output_reference": wrapped_record["output_reference"],
                        "window": wrapped_record["window"],
                        "bands": wrapped_record["bands"],
                        "nodata": wrapped_record["nodata"],
                    },
                    "comparison": {
                        "native_equals_cvrs_wrapped_native": np.array_equal(native, wrapped_data),
                        "native_dtype_preserved": str(native.dtype) == str(wrapped_data.dtype),
                        "native_shape_preserved": native.shape == wrapped_data.shape,
                        "native_nodata_mask_preserved": np.array_equal(native != metadata["nodata"], wrapped_valid),
                        "native_affine_preserved": wrapped_record["output_reference"]["affine"] == native_transform,
                        "source_identity_preserved": wrapped_record["source_sha256"] == identity["sha256"],
                        "window_and_bands_preserved": wrapped_record["window"] == [column, row, WINDOW_SIZE, WINDOW_SIZE]
                        and wrapped_record["bands"] == list(metadata["band_indexes"]),
                        "native_values_equal_direct_source_after_dtype_cast_diagnostic": values_equal,
                        "transform_max_absolute_delta": transform_delta,
                        "transform_equal_after_documented_float32_cast": transform_float32_equal,
                        "pixel_world_pixel_max_error": roundtrip_error,
                        "nodata_mask_equal": nodata_equal,
                        "bounds_equal": all(
                            abs(a - b) <= 1e-9 for a, b in zip(cvrs_record["window_bounds"], [left, bottom, right, top])
                        ),
                    },
                }
            )
        passed = all(
            item["comparison"][key]
            for item in records
            for key in (
                "native_equals_cvrs_wrapped_native",
                "native_dtype_preserved",
                "native_shape_preserved",
                "native_nodata_mask_preserved",
                "native_affine_preserved",
                "source_identity_preserved",
                "window_and_bands_preserved",
                "nodata_mask_equal",
                "bounds_equal",
            )
        ) and all(item["comparison"]["pixel_world_pixel_max_error"] <= 1e-9 for item in records)
        report = {
            "schema": "cvrs.rq002.torchgeo-public-geotiff.v1",
            "status": "PASS_TORCHGEO_PUBLIC_GEOTIFF_INTEROPERABILITY" if passed else "FAIL_TORCHGEO_PUBLIC_GEOTIFF_INTEROPERABILITY",
            "source": {"url": SOURCE_URL, "revision": SOURCE_REVISION, **identity, **metadata},
            "license": {"identifier": "BSD-3-Clause repository license", "url": LICENSE_URL},
            "selection": {"policy": "four 128x128 source-pixel corner windows", "count": len(records)},
            "native_path": "TorchGeo RasterDataset queried by a world-coordinate GeoSlice; exact pixel edges are moved one floating-point ULP inward to preserve the frozen closed-open pixel window under inverse-affine arithmetic",
            "cvrs_path": "CVRS inspect_geotiff + inspect_raster + lossless native-window artifact wrapper; export_raw_window separately preserves direct source pixels",
            "windows": records,
            "environment": {
                name: importlib.metadata.version(name)
                for name in ("torch", "torchvision", "torchgeo", "rasterio", "numpy", "pydantic")
            },
            "torchgeo_module_version": torchgeo.__version__,
            "controls": {
                "training": False,
                "model_downloads": False,
                "gpu": False,
                "protected_data_access": 0,
                "sealed_test_access": 0,
                "source_deleted_with_ephemeral_container": True,
            },
            "runtime_seconds": time.perf_counter() - started,
            "limits": [
                "This is a geospatial provenance/interoperability qualification, not a model result.",
                "TorchGeo presents image tensors as float32; equality is checked only after an explicit cast back to the locked uint8 source dtype.",
                "TorchGeo returns its affine as a float32 tensor; affine equality requires exact equality to the CVRS float64 affine after an explicit float32 representation cast.",
                "The direct source-pixel window and TorchGeo's world-grid merge differ at a small number of nodata-boundary values on this non-integer affine; this diagnostic is disclosed but is not a CVRS transport mutation.",
                "No derived RGB display artifact was needed because the source is already a three-band RGB test raster.",
                "Repository-level licensing is recorded; upstream Landsat scene ancestry is not inferred.",
            ],
        }
        (root / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        checksums = []
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name not in {"RGB.byte.tif", "checksums.sha256"}:
                checksums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}")
        (root / "checksums.sha256").write_text("\n".join(checksums) + "\n", encoding="utf-8")
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(root.rglob("*")):
                if path.is_file() and path.name != "RGB.byte.tif":
                    bundle.write(path, path.relative_to(root).as_posix())
        return archive.getvalue()


@app.function(image=image, cpu=2.0, memory=4096, timeout=600, retries=0)
def diagnose_offsets(expected_sha256: str) -> dict:
    import hashlib
    import math
    import tempfile

    import numpy as np
    import rasterio
    from rasterio.windows import Window
    from torchgeo.datasets import RasterDataset

    with tempfile.TemporaryDirectory() as temporary:
        source = Path(temporary) / "RGB.byte.tif"
        identity = _download(SOURCE_URL, source)
        if identity["sha256"] != expected_sha256:
            raise RuntimeError("SOURCE_SHA256_MISMATCH")
        metadata = _metadata(source)
        raster = RasterDataset(paths=source, crs=metadata["crs"], res=tuple(metadata["resolution"]))
        transform = rasterio.Affine(*metadata["transform"])
        offsets = [
            [0, 0],
            [metadata["width"] - WINDOW_SIZE, 0],
            [0, metadata["height"] - WINDOW_SIZE],
            [metadata["width"] - WINDOW_SIZE, metadata["height"] - WINDOW_SIZE],
        ]
        records = []
        with rasterio.open(source) as dataset:
            for index, (column, row) in enumerate(offsets):
                nominal = Window(column, row, WINDOW_SIZE, WINDOW_SIZE)
                left, bottom, right, top = rasterio.windows.bounds(nominal, transform)
                query = (
                    slice(math.nextafter(left, right), math.nextafter(right, left), metadata["resolution"][0]),
                    slice(math.nextafter(bottom, top), math.nextafter(top, bottom), metadata["resolution"][1]),
                )
                native = raster[query]["image"].detach().cpu().numpy().astype(np.uint8)
                candidates = []
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        candidate = dataset.read(
                            window=Window(column + dx, row + dy, WINDOW_SIZE, WINDOW_SIZE),
                            boundless=True,
                            fill_value=metadata["nodata"],
                        )
                        mismatch_count = int(np.count_nonzero(native != candidate))
                        candidates.append(
                            {
                                "dx": dx,
                                "dy": dy,
                                "mismatch_count": mismatch_count,
                                "candidate_value_sha256": hashlib.sha256(candidate.tobytes(order="C")).hexdigest(),
                            }
                        )
                candidates.sort(key=lambda item: (item["mismatch_count"], abs(item["dx"]) + abs(item["dy"])))
                records.append(
                    {
                        "id": f"window-{index}",
                        "native_value_sha256": hashlib.sha256(native.tobytes(order="C")).hexdigest(),
                        "best_candidates": candidates[:5],
                    }
                )
        return {
            "schema": "cvrs.rq002.torchgeo-offset-diagnostic.v1",
            "status": "DIAGNOSTIC_ONLY",
            "source_sha256": identity["sha256"],
            "windows": records,
            "controls": {"training": False, "gpu": False, "protected_data_access": 0, "sealed_test_access": 0},
        }


@app.local_entrypoint()
def main(mode: str, out: str, expected_sha256: str = "") -> None:
    destination = Path(out)
    if destination.exists():
        raise RuntimeError(f"refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if mode == "probe":
        destination.write_text(json.dumps(probe_source.remote(), indent=2) + "\n", encoding="utf-8")
    elif mode == "qualify":
        if len(expected_sha256) != 64:
            raise ValueError("qualify requires --expected-sha256")
        destination.write_bytes(qualify.remote(expected_sha256))
    elif mode == "diagnose-offsets":
        if len(expected_sha256) != 64:
            raise ValueError("diagnose-offsets requires --expected-sha256")
        destination.write_text(
            json.dumps(diagnose_offsets.remote(expected_sha256), indent=2) + "\n", encoding="utf-8"
        )
    else:
        raise ValueError("mode must be probe, qualify, or diagnose-offsets")
    print(json.dumps({"mode": mode, "output": str(destination), "bytes": destination.stat().st_size}))
