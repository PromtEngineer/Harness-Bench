#!/usr/bin/env bash
# Checker for T35-optimizer-pass. cwd = workspace copy; TASK_DIR = task dir.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR
fail() { echo "CHECK FAIL: $*" >&2; exit 1; }
[ -n "${CHECKER_DIR:-}" ] || fail "TASK_DIR is not set"
[ -f minic/optimize.py ] || fail "minic/optimize.py is missing"

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
g = json.load(open(os.path.join(task_dir, "hidden", "grading.json")))
progs = {}
for name in g["budgets"]:
    ex = os.path.join("examples", name)
    hid = os.path.join(task_dir, "hidden", "progs", name)
    progs[name] = ex if os.path.exists(ex) else hid
ok = 0
for name, path in sorted(progs.items()):
    try:
        run = subprocess.run([sys.executable, "run.py", path, "--opt"],
                             capture_output=True, text=True, timeout=60)
        ir = subprocess.run([sys.executable, "compile.py", path, "--opt"],
                            capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        print(f"CHECK FAIL: {name}: 60s timeout"); sys.exit(1)
    if run.returncode != 0:
        print(f"CHECK FAIL: {name}: run.py --opt crashed:\n{run.stderr[-400:]}")
        sys.exit(1)
    if run.stdout != g["outputs"][name]:
        print(f"CHECK FAIL: {name}: SEMANTICS changed by optimization")
        print(f"  expected: {g['outputs'][name]!r}")
        print(f"  got:      {run.stdout!r}")
        sys.exit(1)
    if ir.returncode != 0:
        print(f"CHECK FAIL: {name}: compile.py --opt crashed"); sys.exit(1)
    count = len([l for l in ir.stdout.splitlines() if l.strip()])
    budget = g["budgets"][name]["budget"]
    if count > budget:
        print(f"CHECK FAIL: {name}: {count} ops, budget {budget} "
              f"(unoptimized {g['budgets'][name]['unopt']})")
        sys.exit(1)
    ok += 1
print(f"all {ok} programs: semantics preserved, budgets met")
PYEOF
[ $? -eq 0 ] || exit 1
echo "CHECK PASS"
exit 0
