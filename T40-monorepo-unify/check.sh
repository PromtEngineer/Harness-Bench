#!/usr/bin/env bash
# Checker for T40-monorepo-unify. cwd = workspace copy; TASK_DIR = task dir.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR
fail() { echo "CHECK FAIL: $*" >&2; exit 1; }
[ -n "${CHECKER_DIR:-}" ] || fail "TASK_DIR is not set"

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

# structural: corelib exists, utils dirs gone, services import corelib
for m in money dates ids retry; do
  [ -f "corelib/$m.py" ] || fail "corelib/$m.py is missing"
done
for svc in billing fulfil notify; do
  [ -d "services/$svc/utils" ] && fail "services/$svc/utils still exists"
  grep -q "from corelib import\|from corelib\." "services/$svc/api.py" \
    || fail "services/$svc/api.py does not import from corelib"
done
# retired variant markers must be gone everywhere
for marker in "CHECK_MOD = 89" "CHECK_MOD = 93" "BACKOFF_BASE = 2.0" \
              'ROUND_MODE = "bankers"' 'ROUND_MODE = "truncate"' \
              'DATE_FMT = "%Y-%m-%d"'; do
  if grep -rF --include="*.py" "$marker" . >/dev/null 2>&1; then
    fail "retired variant still present somewhere: $marker"
  fi
done
N=$(grep -rF --include="*.py" -l "CHECK_MOD = 97" . | grep -v "^./corelib/" | wc -l)
[ "$N" -eq 0 ] || fail "CHECK_MOD = 97 duplicated outside corelib/"

export PYTHONPATH="$(pwd)"
timeout 120 python3 -m pytest -q -p no:cacheprovider tests/ \
  || fail "visible invariant tests failed"
timeout 120 python3 -m pytest -q -p no:cacheprovider \
  "$CHECKER_DIR/hidden/test_unified.py" || fail "hidden canonical-behavior tests failed"
echo "CHECK PASS"
exit 0
