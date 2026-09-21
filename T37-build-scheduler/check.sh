#!/usr/bin/env bash
# Checker for T37-build-scheduler. cwd = workspace copy; TASK_DIR = task dir.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR
fail() { echo "CHECK FAIL: $*" >&2; exit 1; }
[ -n "${CHECKER_DIR:-}" ] || fail "TASK_DIR is not set"
[ -f scheduler.py ] || fail "scheduler.py is missing from the workspace root"

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

run_set() {  # run_set NAME JOBSFILE
  local name="$1" jobsfile="$2"
  local out=".t37-sched-$name.json"
  timeout 60 python3 scheduler.py "$jobsfile" "$out" >/dev/null 2>&1 \
    || fail "$name: scheduler crashed or exceeded 60s"
  [ -f "$out" ] || fail "$name: no schedule written"
  python3 "$CHECKER_DIR/hidden/validator.py" "$jobsfile" "$out" \
    || fail "$name: schedule invalid"
}
run_set "visible" jobs.json
run_set "hidden-a" "$CHECKER_DIR/hidden/hidden-a.json"
run_set "hidden-b" "$CHECKER_DIR/hidden/hidden-b.json"
echo "CHECK PASS"
exit 0
