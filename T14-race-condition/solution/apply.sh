#!/usr/bin/env bash
# Reference solution for T14: replace queue.py with the properly locked
# version (in-place mutation of results dict + counter increment, both
# guarded by a dedicated state lock).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/queue_fixed.py" jobqueue/queue.py
echo "applied fixed jobqueue/queue.py"
