"""Convert a saved MMRotate native JSON artifact through CVRS without inference."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cvsubstrate.evaluation.converters import convert_results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    native = json.loads(args.native.read_text("utf-8"))
    mapping = {str(index): index for index in range(15)}
    report = convert_results(
        native,
        format="mmrotate",
        category_map=mapping,
        output=args.out,
        angle_convention={"unit": "radians", "positive": "clockwise"},
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
