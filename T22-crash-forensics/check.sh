#!/usr/bin/env bash
# Checker for T22-crash-forensics. cwd = workspace copy; TASK_DIR = task dir.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR
fail() { echo "CHECK FAIL: $*" >&2; exit 1; }
[ -n "${CHECKER_DIR:-}" ] || fail "TASK_DIR is not set"
[ -d orderflow ] || fail "orderflow/ package is missing"

python3 - "$CHECKER_DIR/expected/fixture.sha256" <<'PYEOF' || exit 1
import hashlib, sys
ok = True
for line in open(sys.argv[1]).read().splitlines():
    if not line.strip():
        continue
    want, path = line.split(None, 1)
    try:
        have = hashlib.sha256(open(path.strip(), "rb").read()).hexdigest()
    except FileNotFoundError:
        print(f"CHECK FAIL: guarded file {path.strip()} is missing", file=sys.stderr)
        ok = False
        continue
    if have != want:
        print(f"CHECK FAIL: {path.strip()} was modified (sha256 mismatch)", file=sys.stderr)
        ok = False
sys.exit(0 if ok else 1)
PYEOF
[ $? -eq 0 ] || exit 1

rm -f report.json
timeout 120 python3 replay.py >/dev/null 2>&1 || fail "replay.py failed"
[ -f report.json ] || fail "replay.py did not write report.json"

python3 - "$CHECKER_DIR/expected/report.json" <<'PYEOF' || exit 1
import json, sys
got = json.load(open("report.json"))
want = json.load(open(sys.argv[1]))
if got != want:
    for k in want:
        if got.get(k) != want[k]:
            print(f"CHECK FAIL: report.json field {k!r}: got {got.get(k)!r}, "
                  f"expected {want[k]!r}", file=sys.stderr)
            break
    sys.exit(1)
def is_int(x): return isinstance(x, int) and not isinstance(x, bool)
for k in ("orders", "gross_cents", "discount_cents", "net_cents"):
    if not is_int(got[k]):
        print(f"CHECK FAIL: {k} must be a JSON integer", file=sys.stderr)
        sys.exit(1)
print("report.json matches")
PYEOF
[ $? -eq 0 ] || exit 1

PYTHONPATH="$(pwd)" timeout 120 python3 -m pytest -q -p no:cacheprovider \
  "$CHECKER_DIR/hidden/test_pipeline.py" \
  || fail "hidden unit tests failed"

echo "CHECK PASS"
exit 0
