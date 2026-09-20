"""Decode a saved MMSegmentation native array through CVRS without inference."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from cvsubstrate.product.bridges import decode_arrays


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.native, allow_pickle=False) as bundle:
        maps = bundle["maps"]
        if maps.ndim != 3 or len(maps) != 1:
            raise ValueError("expected one NHW semantic map")
        height, width = maps.shape[1:]
    spec = {
        "sha256": hashlib.sha256(args.native.read_bytes()).hexdigest(),
        "task": "semantic_segmentation", "array": "maps", "layout": "NHW",
        "samples": [{"id": args.sample_id, "width": int(width), "height": int(height)}],
        "category_mapping": {str(i): i for i in range(150)},
        "ignore_index": 255, "reduce_zero_label": False,
    }
    report = decode_arrays(args.native, spec, args.out)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
