#!/usr/bin/env bash
set -euo pipefail
cp "$TASK_DIR/solution/files/solve.py" ./solve.py
python3 solve.py
echo "T30 reference solution applied"
