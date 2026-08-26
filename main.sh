#!/usr/bin/env sh
set -eu

PYTHONPATH=src exec python3 -m sitegen serve --watch --host 0.0.0.0 --port "${PORT:-8888}"
