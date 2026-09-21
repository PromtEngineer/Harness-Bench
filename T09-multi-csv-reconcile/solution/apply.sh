#!/usr/bin/env bash
# Reference solution for T09. cwd = workspace copy.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$HERE/files/solve.py"
