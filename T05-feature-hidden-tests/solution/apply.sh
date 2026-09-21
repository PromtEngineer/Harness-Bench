#!/usr/bin/env bash
# cwd = workspace copy. Applies the reference solution.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/files/ratelimiter.py" ./ratelimiter.py
