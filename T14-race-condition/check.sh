#!/usr/bin/env bash
# T14-race-condition checker. cwd = workspace copy, TASK_DIR = task dir.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR

if [ -z "${CHECKER_DIR:-}" ]; then
  echo "FAIL: TASK_DIR not set" >&2
  exit 2
fi

# 1. repro.py must be untouched (covers NUM_JOBS/NUM_WORKERS/seed/asserts).
python3 - "$CHECKER_DIR" <<'PYEOF' || exit 1
import hashlib, os, sys
task_dir = sys.argv[1]
want = open(os.path.join(task_dir, "expected", "repro.sha256")).read().split()[0]
if not os.path.exists("repro.py"):
    print("FAIL: repro.py missing"); sys.exit(1)
got = hashlib.sha256(open("repro.py", "rb").read()).hexdigest()
if got != want:
    print("FAIL: repro.py was modified"); sys.exit(1)
print("OK: repro.py unmodified")
PYEOF

# 2. jobqueue must exist and contain no sleeping of any kind.
if [ ! -d jobqueue ]; then
  echo "FAIL: jobqueue/ missing"
  exit 1
fi
if grep -rni "sleep" jobqueue/ >/dev/null 2>&1; then
  echo "FAIL: sleeping/backoff found in jobqueue/:"
  grep -rni "sleep" jobqueue/
  exit 1
fi
echo "OK: no sleep in jobqueue/"

# 3. 20 consecutive green runs of the stress repro.
for i in $(seq 1 20); do
  if ! python3 repro.py > /tmp/t14_run_out.$$ 2>&1; then
    echo "FAIL: repro run $i/20 failed:"
    cat /tmp/t14_run_out.$$
    rm -f /tmp/t14_run_out.$$
    exit 1
  fi
done
rm -f /tmp/t14_run_out.$$
echo "PASS: repro.py passed 20/20 consecutive runs"
