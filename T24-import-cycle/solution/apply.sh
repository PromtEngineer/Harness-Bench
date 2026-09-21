#!/usr/bin/env bash
set -euo pipefail
cp "$TASK_DIR/solution/files/serializers.py" flowkit/serializers.py
cp "$TASK_DIR/solution/files/cli.py" flowkit/cli.py
echo "T24 reference solution applied"
