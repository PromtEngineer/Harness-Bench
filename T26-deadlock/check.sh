#!/usr/bin/env bash
# Checker for T26-deadlock. cwd = workspace copy; TASK_DIR = task dir.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR
fail() { echo "CHECK FAIL: $*" >&2; exit 1; }
[ -n "${CHECKER_DIR:-}" ] || fail "TASK_DIR is not set"
[ -f bankcore/accounts.py ] || fail "bankcore/accounts.py is missing"

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

grep -q "threading" bankcore/accounts.py || fail "accounts.py no longer uses threading"
OUT=$(timeout 60 python3 stress.py 2>&1)
[ "$OUT" = "OK" ] || fail "stress.py did not print OK (got: $OUT)"
timeout 180 python3 "$CHECKER_DIR/hidden/driver.py" || fail "concurrency driver failed"
echo "CHECK PASS"
exit 0
