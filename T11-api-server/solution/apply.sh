#!/usr/bin/env bash
# Reference solution for T11. cwd = workspace copy.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$HERE/files/server.py" server.py
