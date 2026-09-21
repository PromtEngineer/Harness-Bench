#!/usr/bin/env bash
# Checker for T17-perf-fix. cwd = copy of the workspace after the agent ran.
# env: TASK_DIR = absolute path of the task directory.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR

fail() { echo "CHECK FAIL: $*" >&2; exit 1; }

[ -n "${CHECKER_DIR:-}" ] || fail "TASK_DIR is not set"
[ -f events.csv ] || fail "events.csv is missing from the workspace"
[ -f report.py ] || fail "report.py is missing from the workspace"

# 1. events.csv must be byte-identical to the shipped fixture (sha256 guard).
python3 - "$CHECKER_DIR/expected/events.sha256" events.csv <<'PYEOF' || exit 1
import hashlib, sys
want = open(sys.argv[1]).read().split()[0]
have = hashlib.sha256(open(sys.argv[2], "rb").read()).hexdigest()
if have != want:
    print(f"CHECK FAIL: events.csv was modified (sha256 {have} != {want})", file=sys.stderr)
    sys.exit(1)
PYEOF
[ $? -eq 0 ] || exit 1

# 2. Remove any pre-built output and rerun report.py under a hard 30s timeout,
#    measuring wall time. It must finish successfully in under 5.0 seconds.
rm -f output.json
python3 - <<'PYEOF'
import subprocess, sys, time
t0 = time.monotonic()
try:
    proc = subprocess.run([sys.executable, "report.py"], timeout=30)
except subprocess.TimeoutExpired:
    print("CHECK FAIL: report.py exceeded the 30s hard timeout", file=sys.stderr)
    sys.exit(1)
elapsed = time.monotonic() - t0
if proc.returncode != 0:
    print(f"CHECK FAIL: report.py exited with code {proc.returncode}", file=sys.stderr)
    sys.exit(1)
print(f"report.py wall time: {elapsed:.2f}s")
if elapsed >= 5.0:
    print(f"CHECK FAIL: report.py took {elapsed:.2f}s (must be < 5.0s)", file=sys.stderr)
    sys.exit(1)
PYEOF
[ $? -eq 0 ] || exit 1

# 3. output.json must be byte-identical to the reference output.
[ -f output.json ] || fail "report.py did not produce output.json"
cmp -s output.json "$CHECKER_DIR/expected/output.json" \
    || fail "output.json differs from the expected reference output (byte comparison)"

echo "CHECK PASS"
exit 0
