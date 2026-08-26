#!/usr/bin/env sh
set -eu

PYTHONPATH=src python3 -m unittest discover -s src -p 'test*.py'
