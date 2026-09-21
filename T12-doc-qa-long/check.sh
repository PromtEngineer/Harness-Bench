#!/usr/bin/env bash
# T12-doc-qa-long checker.
# cwd = copy of the workspace after the agent ran; TASK_DIR = task directory.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR

if [ -z "${CHECKER_DIR:-}" ]; then
  echo "FAIL: TASK_DIR not set" >&2
  exit 2
fi

if [ ! -f answers.json ]; then
  echo "FAIL: answers.json not found in workspace" >&2
  exit 1
fi

python3 - "$CHECKER_DIR/expected/fixture.sha256" <<'PY' || exit 1
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

python3 - "$CHECKER_DIR/expected/answers.json" answers.json <<'PY'
import json
import sys

with open(sys.argv[1]) as f:
    expected = json.load(f)
try:
    with open(sys.argv[2]) as f:
        got = json.load(f)
except Exception as e:
    print(f"FAIL: answers.json is not valid JSON: {e}", file=sys.stderr)
    sys.exit(1)

if not isinstance(got, dict):
    print("FAIL: answers.json must be a JSON object", file=sys.stderr)
    sys.exit(1)

ok = True
extra = set(got) - set(expected)
if extra:
    print(f"FAIL: unexpected keys: {sorted(extra)}", file=sys.stderr)
    ok = False

def same(a, b):
    # type-strict: 128 != 128.0 != "128"; arrays element-wise strict
    if type(a) is not type(b):
        return False
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b

for key in expected:
    if key not in got:
        print(f"FAIL: missing key {key}", file=sys.stderr)
        ok = False
    elif not same(expected[key], got[key]):
        print(f"FAIL: {key}: wrong answer (got {json.dumps(got[key])})", file=sys.stderr)
        ok = False

if ok:
    print("PASS: all 8 answers correct")
    sys.exit(0)
sys.exit(1)
PY
exit $?
