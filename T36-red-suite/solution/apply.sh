#!/usr/bin/env bash
set -euo pipefail
for f in tokenize ngrams readability wordfreq; do
  cp "$TASK_DIR/solution/files/$f.py" "textstat/$f.py"
done
echo "T36 reference solution applied"
