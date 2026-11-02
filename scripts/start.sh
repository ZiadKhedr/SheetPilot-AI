#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
exec .venv/bin/python -m uvicorn sheetpilot.api:app --host 127.0.0.1 --port "${PORT:-8000}"
