#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3.13}"
EXTRAS="${1:-}"
OLDIFS="$IFS"; IFS=','
for extra in $EXTRAS; do
  case "$extra" in native|coco|dev|research|geo|geometry-validation) ;; *) echo "Unknown extra: $extra" >&2; exit 2;; esac
done
IFS="$OLDIFS"
[ -x .venv/bin/python ] || "$PYTHON" -m venv .venv
TARGET='.'
[ -z "$EXTRAS" ] || TARGET=".[$EXTRAS]"
.venv/bin/python -m pip install -e "$TARGET"
.venv/bin/python -m cvsubstrate doctor
