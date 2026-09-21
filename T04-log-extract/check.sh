#!/usr/bin/env bash
# T04-log-extract checker. cwd = workspace copy; TASK_DIR = task directory.
set -euo pipefail
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR

python3 - "$CHECKER_DIR" <<'EOF'
import hashlib
import json
import os
import sys

task_dir = sys.argv[1]

# 1. Log file must be untouched.
with open(os.path.join(task_dir, "expected", "log_sha256.txt")) as f:
    exp_hash = f.read().strip()
if not os.path.exists("logs/app.log"):
    print("FAIL: logs/app.log is missing")
    sys.exit(1)
h = hashlib.sha256()
with open("logs/app.log", "rb") as fh:
    for chunk in iter(lambda: fh.read(1 << 20), b""):
        h.update(chunk)
if h.hexdigest() != exp_hash:
    print("FAIL: logs/app.log was modified")
    sys.exit(1)

# 2. answer.json exact match.
with open(os.path.join(task_dir, "expected", "answer.json")) as f:
    exp = json.load(f)

if not os.path.exists("answer.json"):
    print("FAIL: answer.json not found in workspace root")
    sys.exit(1)
try:
    with open("answer.json") as f:
        got = json.load(f)
except Exception as e:
    print(f"FAIL: answer.json is not valid JSON: {e}")
    sys.exit(1)

if not isinstance(got, dict) or set(got.keys()) != {"request_id", "upstream_service", "error_count"}:
    print(f"FAIL: answer.json must have exactly the keys request_id, upstream_service, error_count")
    sys.exit(1)
if got["request_id"] != exp["request_id"]:
    print(f"FAIL: request_id: expected {exp['request_id']!r}, got {got['request_id']!r}")
    sys.exit(1)
if got["upstream_service"] != exp["upstream_service"]:
    print(f"FAIL: upstream_service: expected {exp['upstream_service']!r}, got {got['upstream_service']!r}")
    sys.exit(1)
if isinstance(got["error_count"], bool) or not isinstance(got["error_count"], int) or got["error_count"] != exp["error_count"]:
    print(f"FAIL: error_count: expected {exp['error_count']}, got {got['error_count']!r}")
    sys.exit(1)

print("PASS")
EOF
