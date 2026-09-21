#!/usr/bin/env bash
# T01-csv-aggregate checker. cwd = workspace copy; TASK_DIR = task directory.
set -euo pipefail
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR

python3 - "$CHECKER_DIR" <<'EOF'
import hashlib
import json
import math
import os
import sys

task_dir = sys.argv[1]

# 1. Fixture data must be untouched.
with open(os.path.join(task_dir, "expected", "data_sha256.json")) as f:
    data_hashes = json.load(f)
actual_data_files = set()
for root, dirs, files in os.walk("data"):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for name in files:
        if not name.endswith(".pyc"):
            actual_data_files.add(os.path.join(root, name))
if actual_data_files != set(data_hashes):
    print("FAIL: data/ file set changed")
    print(f"  missing: {sorted(set(data_hashes) - actual_data_files)}")
    print(f"  added:   {sorted(actual_data_files - set(data_hashes))}")
    sys.exit(1)
for rel, h in data_hashes.items():
    if not os.path.exists(rel):
        print(f"FAIL: fixture file {rel} is missing")
        sys.exit(1)
    with open(rel, "rb") as fh:
        if hashlib.sha256(fh.read()).hexdigest() != h:
            print(f"FAIL: fixture file {rel} was modified")
            sys.exit(1)

# 2. results.json vs ground truth.
with open(os.path.join(task_dir, "expected", "results.json")) as f:
    exp = json.load(f)

if not os.path.exists("results.json"):
    print("FAIL: results.json not found in workspace root")
    sys.exit(1)
try:
    def reject_constant(value):
        raise ValueError(f"non-standard JSON constant {value}")

    with open("results.json") as f:
        got = json.load(f, parse_constant=reject_constant)
except Exception as e:
    print(f"FAIL: results.json is not valid JSON: {e}")
    sys.exit(1)

if not isinstance(got, dict) or set(got.keys()) != set(exp.keys()):
    print(f"FAIL: top-level keys must be exactly {sorted(exp.keys())}, got {got if not isinstance(got, dict) else sorted(got.keys())}")
    sys.exit(1)

for region, e in exp.items():
    g = got[region]
    if not isinstance(g, dict) or set(g.keys()) != {"revenue_usd", "units"}:
        print(f"FAIL: {region}: keys must be exactly ['revenue_usd', 'units']")
        sys.exit(1)
    if isinstance(g["units"], bool) or not isinstance(g["units"], int):
        print(f"FAIL: {region}.units must be a JSON integer, got {g['units']!r}")
        sys.exit(1)
    if g["units"] != e["units"]:
        print(f"FAIL: {region}.units: expected {e['units']}, got {g['units']}")
        sys.exit(1)
    r = g["revenue_usd"]
    if (isinstance(r, bool) or not isinstance(r, (int, float))
            or not math.isfinite(float(r))):
        print(f"FAIL: {region}.revenue_usd must be a JSON number, got {r!r}")
        sys.exit(1)
    if abs(float(r) - e["revenue_usd"]) > 0.005:
        print(f"FAIL: {region}.revenue_usd: expected {e['revenue_usd']}, got {r}")
        sys.exit(1)

print("PASS")
EOF
