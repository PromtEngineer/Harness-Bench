#!/usr/bin/env bash
# Reference solution for T10. cwd = workspace copy.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$HERE/files/pyproject.toml" pyproject.toml
cp "$HERE/files/parse.py" src/chronolib/parse.py
