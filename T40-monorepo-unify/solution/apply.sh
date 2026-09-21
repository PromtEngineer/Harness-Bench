#!/usr/bin/env bash
set -euo pipefail
mkdir -p corelib
cp "$TASK_DIR/solution/files/corelib/"*.py corelib/
for svc in billing fulfil notify; do
  cp "$TASK_DIR/solution/files/api_$svc.py" "services/$svc/api.py"
  rm -rf "services/$svc/utils"
done
echo "T40 reference solution applied"
