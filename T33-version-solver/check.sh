#!/usr/bin/env bash
# Checker for T33-version-solver. cwd = workspace copy; TASK_DIR = task dir.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR
fail() { echo "CHECK FAIL: $*" >&2; exit 1; }
[ -n "${CHECKER_DIR:-}" ] || fail "TASK_DIR is not set"
[ -f resolver.py ] || fail "resolver.py is missing from the workspace root"

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

python3 - "$CHECKER_DIR" <<'PYEOF' || exit 1
import json, os, subprocess, sys
task_dir = sys.argv[1]
cases = [("sample", "requirements-sample.json",
          "expected-sample-lock.json", None)]
hd = os.path.join(task_dir, "hidden")
for name in sorted(os.listdir(hd)):
    if name.startswith("req-"):
        scen = name[4:-5]
        cases.append((scen, os.path.join(hd, name),
                      os.path.join(hd, f"lock-{scen}.json"), None))
for scen, req, want_path, _ in cases:
    out = f".t33-lock-{scen}.json"
    try:
        p = subprocess.run([sys.executable, "resolver.py", "index.json",
                            req, out], capture_output=True, text=True,
                           timeout=120)
    except subprocess.TimeoutExpired:
        print(f"CHECK FAIL: {scen}: resolver exceeded 120s (runaway search?)")
        sys.exit(1)
    if p.returncode != 0:
        print(f"CHECK FAIL: {scen}: resolver crashed:\n{p.stderr[-500:]}")
        sys.exit(1)
    try:
        got = json.load(open(out))
    except Exception as e:
        print(f"CHECK FAIL: {scen}: bad lockfile: {e}")
        sys.exit(1)
    want = json.load(open(want_path))
    if got != want:
        print(f"CHECK FAIL: {scen}: lockfile mismatch")
        print(f"  expected: {json.dumps(want, sort_keys=True)}")
        print(f"  got:      {json.dumps(got, sort_keys=True)}")
        sys.exit(1)
print(f"all {len(cases)} scenarios match")
PYEOF
[ $? -eq 0 ] || exit 1
echo "CHECK PASS"
exit 0
