#!/usr/bin/env bash
# Reference solution for T22-crash-forensics: fix the three bugs.
set -euo pipefail
cp "$TASK_DIR/solution/files/parse.py" orderflow/parse.py
cp "$TASK_DIR/solution/files/pricing.py" orderflow/pricing.py
cp "$TASK_DIR/solution/files/batch.py" orderflow/batch.py
python3 replay.py
echo "T22 reference solution applied"
