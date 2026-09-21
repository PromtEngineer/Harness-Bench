#!/usr/bin/env bash
# T09-multi-csv-reconcile checker.
# cwd = copy of the workspace after the agent ran; TASK_DIR = task directory.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR

if [ -z "${CHECKER_DIR:-}" ]; then
  echo "FAIL: TASK_DIR not set" >&2
  exit 2
fi

if [ ! -f reconciled.csv ]; then
  echo "FAIL: reconciled.csv not found in workspace" >&2
  exit 1
fi

python3 - "$CHECKER_DIR/expected/fixture.sha256" <<'PY' || exit 1
import hashlib
import pathlib
import sys

expected = {}
for line in pathlib.Path(sys.argv[1]).read_text().splitlines():
    digest, rel = line.split("  ", 1)
    expected[rel] = digest
actual = {
    str(path.as_posix()): hashlib.sha256(path.read_bytes()).hexdigest()
    for root in (pathlib.Path("warehouse"),)
    for path in root.rglob("*") if path.is_file()
}
actual["rates.json"] = hashlib.sha256(pathlib.Path("rates.json").read_bytes()).hexdigest()
if actual != expected:
    missing = sorted(set(expected) - set(actual))
    added = sorted(set(actual) - set(expected))
    changed = sorted(k for k in set(actual) & set(expected) if actual[k] != expected[k])
    raise SystemExit(
        f"FAIL: input files changed: missing={missing} added={added} changed={changed}"
    )
print("fixture inputs intact")
PY

python3 - "$CHECKER_DIR/expected/reconciled.csv" reconciled.csv <<'PY'
import sys

exp_raw = open(sys.argv[1], "rb").read()
got_raw = open(sys.argv[2], "rb").read()
exp = exp_raw.decode("ascii").splitlines()
try:
    got = got_raw.decode("ascii").splitlines()
except UnicodeDecodeError as exc:
    print(f"FAIL: reconciled.csv must be plain ASCII: {exc}", file=sys.stderr)
    sys.exit(1)
if exp_raw == got_raw:
    print("PASS: reconciled.csv matches expected output")
    sys.exit(0)

print("FAIL: reconciled.csv does not match expected output", file=sys.stderr)
if len(exp) != len(got):
    print(f"  expected {len(exp)} lines, got {len(got)}", file=sys.stderr)
shown = 0
for i in range(max(len(exp), len(got))):
    e = exp[i] if i < len(exp) else "<missing>"
    g = got[i] if i < len(got) else "<missing>"
    if e != g:
        print(f"  line {i+1}: expected {e!r} got {g!r}", file=sys.stderr)
        shown += 1
        if shown >= 5:
            break
sys.exit(1)
PY
exit $?
