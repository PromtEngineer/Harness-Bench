#!/usr/bin/env bash
# Checker for T20-binary-protocol. cwd = copy of the workspace after the agent
# ran. env: TASK_DIR = absolute path of the task directory.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR

fail() { echo "CHECK FAIL: $*" >&2; exit 1; }

[ -n "${CHECKER_DIR:-}" ] || fail "TASK_DIR is not set"
[ -f format.md ] || fail "format.md is missing from the workspace"
[ -f data/records.slpk ] || fail "data/records.slpk is missing from the workspace"

# 1. Guarded fixture files must be unmodified.
python3 - "$CHECKER_DIR/expected/fixture.sha256" <<'PYEOF' || exit 1
import hashlib, sys
ok = True
for line in open(sys.argv[1]).read().splitlines():
    if not line.strip():
        continue
    want, path = line.split(None, 1)
    have = hashlib.sha256(open(path.strip(), "rb").read()).hexdigest()
    if have != want:
        print(f"CHECK FAIL: {path.strip()} was modified (sha256 {have} != {want})",
              file=sys.stderr)
        ok = False
sys.exit(0 if ok else 1)
PYEOF
[ $? -eq 0 ] || exit 1

# 2. summary.json must exist, be well-typed, and match the expected summary.
[ -f summary.json ] || fail "summary.json is missing from the workspace root"
python3 - "$CHECKER_DIR/expected/summary.json" <<'PYEOF' || exit 1
import json, sys

def die(msg):
    print(f"CHECK FAIL: {msg}", file=sys.stderr)
    sys.exit(1)

try:
    with open("summary.json") as fh:
        got = json.load(fh)
except Exception as exc:
    die(f"summary.json is not valid JSON: {exc}")
with open(sys.argv[1]) as fh:
    want = json.load(fh)

if not isinstance(got, dict):
    die("summary.json must be a JSON object")
if set(got) != set(want):
    die(f"summary.json keys {sorted(got)} != expected {sorted(want)}")

def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)

for key in ("record_count", "active_count", "deleted_count", "total_payload_bytes"):
    if not is_int(got[key]):
        die(f"{key} must be a JSON integer, got {type(got[key]).__name__}")
if not (isinstance(got["crc_failures"], list)
        and all(is_int(x) for x in got["crc_failures"])):
    die("crc_failures must be a list of integers")
if not (isinstance(got["top5_tags"], list) and len(got["top5_tags"]) == 5
        and all(isinstance(e, list) and len(e) == 2
                and isinstance(e[0], str) and is_int(e[1])
                for e in got["top5_tags"])):
    die("top5_tags must be a list of exactly 5 [name, count] pairs")

for key in sorted(want):
    if got[key] != want[key]:
        die(f"{key} mismatch: got {got[key]!r}, expected {want[key]!r}")
print("summary.json matches the expected summary")
PYEOF
[ $? -eq 0 ] || exit 1

echo "CHECK PASS"
exit 0
