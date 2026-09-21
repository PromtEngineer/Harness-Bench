#!/usr/bin/env bash
# cwd = copy of the workspace after the agent finished; TASK_DIR = task directory.
set -euo pipefail
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR

[ -f report.json ] || { echo "FAIL: report.json missing"; exit 1; }

python3 - "$CHECKER_DIR/expected/fixture.sha256" <<'PY'
import hashlib
import pathlib
import sys

for line in pathlib.Path(sys.argv[1]).read_text().splitlines():
    digest, rel = line.split("  ", 1)
    path = pathlib.Path(rel)
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise SystemExit(f"FAIL: guarded fixture file changed: {rel}")
print("fixture inputs intact")
PY

python3 - "$CHECKER_DIR/expected/report.json" <<'PY'
import json
import math
import sys

expected = json.load(open(sys.argv[1]))
try:
    got = json.load(open("report.json"))
except Exception as exc:  # noqa: BLE001
    sys.exit(f"FAIL: report.json is not valid JSON: {exc}")

if not isinstance(got, dict):
    sys.exit("FAIL: report.json must be a JSON object")
if set(got) != set(expected):
    sys.exit(f"FAIL: keys {sorted(got)} != {sorted(expected)}")
if isinstance(got["q1"], bool) or not isinstance(got["q1"], int):
    sys.exit("FAIL: q1 must be a JSON integer")
if not isinstance(got["q2"], str):
    sys.exit("FAIL: q2 must be a JSON string")
if not isinstance(got["q3"], dict):
    sys.exit("FAIL: q3 must be a JSON object")
if any(isinstance(v, bool) or not isinstance(v, (int, float))
       or not math.isfinite(float(v)) for v in got["q3"].values()):
    sys.exit("FAIL: q3 values must be finite JSON numbers")
if not (isinstance(got.get("q4"), list)
        and all(isinstance(v, int) and not isinstance(v, bool) for v in got["q4"])
        and got["q4"] == sorted(got["q4"])):
    sys.exit(f"FAIL: q4 must be an ascending list, got {got.get('q4')!r}")
if (isinstance(got["q5"], bool) or not isinstance(got["q5"], (int, float))
        or not math.isfinite(float(got["q5"]))):
    sys.exit("FAIL: q5 must be a finite JSON number")
for key in ("q1", "q2", "q3", "q4", "q5"):
    if type(got[key]) is not type(expected[key]) and key in ("q1", "q2", "q4"):
        sys.exit(f"FAIL: {key}: wrong JSON type")
    if got[key] != expected[key]:
        sys.exit(f"FAIL: {key}: got {got[key]!r}, expected {expected[key]!r}")
print("PASS")
PY
