"""Compatibility entrypoint for the standalone MMDetection worker shim.

The controller no longer launches this module in heritage environments. It launches
``worker_shims/mmdetection_worker.py`` by file path so CVRS/Pydantic need not exist in
that environment. This module remains only for users of the old ``python -m`` path.
"""
from pathlib import Path
import runpy


def main() -> None:
    shim = Path(__file__).resolve().parents[1] / 'worker_shims' / 'mmdetection_worker.py'
    runpy.run_path(str(shim), run_name='__main__')


if __name__ == '__main__':
    main()
