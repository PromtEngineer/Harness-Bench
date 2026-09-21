#!/usr/bin/env bash
# Reference solution for T02-bugfix-simple. cwd = workspace copy.
# Fixes the off-by-one in sliding_windows (range end must be len-size+1).
set -euo pipefail
SOLUTION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SOLUTION_DIR/files/windows.py" textstats/windows.py
