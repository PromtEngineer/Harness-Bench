#!/usr/bin/env bash
# Checker for T39-spreadsheet-calc. cwd = workspace copy; TASK_DIR = task dir.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR
fail() { echo "CHECK FAIL: $*" >&2; exit 1; }
[ -n "${CHECKER_DIR:-}" ] || fail "TASK_DIR is not set"
[ -f calc.py ] || fail "calc.py is missing from the workspace root"

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

run_sheet() {  # run_sheet NAME IN EXPECTED
  local name="$1" input="$2" want="$3"
  local out=".t39-$name.tsv"
  timeout 120 python3 calc.py "$input" "$out" >/dev/null 2>&1 \
    || fail "$name: calc.py crashed or exceeded 120s"
  cmp -s "$out" "$want" || {
    diff "$want" "$out" 2>/dev/null | head -6 >&2
    fail "$name: output differs from expected"
  }
}
run_sheet "sample" sample.tsv sample.expected.tsv
for sheet in "$CHECKER_DIR"/hidden/*.tsv; do
  case "$sheet" in *.expected.tsv) continue ;; esac
  name="$(basename "$sheet" .tsv)"
  run_sheet "$name" "$sheet" "$CHECKER_DIR/hidden/$name.expected.tsv"
done
echo "CHECK PASS"
exit 0
