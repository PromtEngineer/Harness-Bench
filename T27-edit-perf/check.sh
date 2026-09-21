#!/usr/bin/env bash
# Checker for T27-edit-perf. cwd = workspace copy; TASK_DIR = task dir.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR
fail() { echo "CHECK FAIL: $*" >&2; exit 1; }
[ -n "${CHECKER_DIR:-}" ] || fail "TASK_DIR is not set"
[ -f edbuf/buffer.py ] || fail "edbuf/buffer.py is missing"

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

PYTHONPATH="$(pwd)" timeout 60 python3 -m pytest -q -p no:cacheprovider \
  "$CHECKER_DIR/hidden/test_buffer.py" || fail "Buffer semantics tests failed"

run_budget() {  # run_budget NAME DOC OPS EXPECTED_DIGEST_FILE
  local name="$1" doc="$2" ops="$3" want="$4"
  python3 - "$name" "$doc" "$ops" "$want" <<'PYEOF' || exit 1
from pathlib import Path
import subprocess
import sys
import time

name, doc, ops, digest_path = sys.argv[1:]
started = time.monotonic()
try:
    proc = subprocess.run(
        [sys.executable, "driver.py", doc, ops],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=150,
        check=False,
    )
except subprocess.TimeoutExpired:
    print(f"CHECK FAIL: {name}: exceeded the 150s hard timeout", file=sys.stderr)
    raise SystemExit(1)

elapsed = time.monotonic() - started
if proc.returncode != 0:
    print(f"CHECK FAIL: {name}: driver exited {proc.returncode}", file=sys.stderr)
    raise SystemExit(1)
print(f"{name}: {elapsed:.3f}s")
if elapsed >= 90.0:
    print(f"CHECK FAIL: {name}: took {elapsed:.3f}s (budget 90s)", file=sys.stderr)
    raise SystemExit(1)

got = proc.stdout.rstrip("\n")
want = "DIGEST " + Path(digest_path).read_text(encoding="ascii").strip()
if got != want:
    print(f"CHECK FAIL: {name}: digest mismatch (got {got!r})", file=sys.stderr)
    raise SystemExit(1)
PYEOF
}
run_budget "full workload" doc/full.txt ops/full.ops "$CHECKER_DIR/hidden/full.digest"
run_budget "hidden workload" "$CHECKER_DIR/hidden/hidden.txt" \
  "$CHECKER_DIR/hidden/hidden.ops" "$CHECKER_DIR/hidden/hidden.digest"
echo "CHECK PASS"
exit 0
