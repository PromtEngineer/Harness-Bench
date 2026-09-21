#!/usr/bin/env bash
# Checker for T32-calendar-rules. cwd = workspace copy; TASK_DIR = task dir.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR
fail() { echo "CHECK FAIL: $*" >&2; exit 1; }
[ -n "${CHECKER_DIR:-}" ] || fail "TASK_DIR is not set"
[ -f sched.py ] || fail "sched.py is missing from the workspace root"

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

python3 - "$CHECKER_DIR/hidden/vectors.json" <<'PYEOF' || exit 1
import json, subprocess, sys
vectors = json.load(open(sys.argv[1]))
for i, v in enumerate(vectors):
    try:
        p = subprocess.run(
            [sys.executable, "sched.py", v["rule"], v["start"],
             str(v["count"])],
            capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        print(f"CHECK FAIL: vector {i} ({v['rule']!r}): 60s timeout",
              file=sys.stderr)
        sys.exit(1)
    got = p.stdout.strip().splitlines()
    if p.returncode != 0 or got != v["expect"]:
        print(f"CHECK FAIL: vector {i}: {v['rule']!r} from {v['start']}",
              file=sys.stderr)
        print(f"  expected: {v['expect']}", file=sys.stderr)
        print(f"  got:      {got}  (rc={p.returncode})", file=sys.stderr)
        sys.exit(1)
print(f"all {len(vectors)} vectors pass")
PYEOF
[ $? -eq 0 ] || exit 1
echo "CHECK PASS"
exit 0
