#!/usr/bin/env bash
# T02-bugfix-simple checker. cwd = workspace copy; TASK_DIR = task directory.
set -euo pipefail
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR

# 1. tests/ must be byte-for-byte identical to the shipped fixture
#    (same file set, same sha256 for every file).
python3 - "$CHECKER_DIR" <<'EOF'
import hashlib
import json
import os
import sys

task_dir = sys.argv[1]
with open(os.path.join(task_dir, "expected", "tests_sha256.json")) as f:
    exp = json.load(f)

got_files = []
for dirpath, dirnames, filenames in os.walk("tests"):
    dirnames[:] = [d for d in dirnames if d != "__pycache__"]
    for fn in filenames:
        if fn.endswith(".pyc"):
            continue
        got_files.append(os.path.relpath(os.path.join(dirpath, fn), "tests"))

if sorted(got_files) != sorted(exp.keys()):
    print(f"FAIL: tests/ file set changed. found={sorted(got_files)} expected={sorted(exp.keys())}")
    sys.exit(1)

for rel, h in exp.items():
    with open(os.path.join("tests", rel), "rb") as fh:
        if hashlib.sha256(fh.read()).hexdigest() != h:
            print(f"FAIL: tests/{rel} was modified")
            sys.exit(1)
print("tests/ intact")
EOF

# 2. Full test suite must be green.
python3 -m pytest -q tests/
