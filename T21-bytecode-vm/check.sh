#!/usr/bin/env bash
# Checker for T21-bytecode-vm. cwd = workspace copy; TASK_DIR = task dir.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR
fail() { echo "CHECK FAIL: $*" >&2; exit 1; }
[ -n "${CHECKER_DIR:-}" ] || fail "TASK_DIR is not set"
[ -f vm.py ] || fail "vm.py is missing from the workspace root"

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

TMP="$(mktemp -d /tmp/t21-check-XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
for prog in "$CHECKER_DIR"/hidden/*.svm; do
  name="$(basename "$prog" .svm)"
  timeout 20 python3 vm.py "$prog" >"$TMP/got" 2>"$TMP/err"
  code=$?
  echo "EXIT=$code" >>"$TMP/got"
  if ! cmp -s "$TMP/got" "$CHECKER_DIR/hidden/$name.expected"; then
    echo "--- expected ($name):" >&2; head -8 "$CHECKER_DIR/hidden/$name.expected" >&2
    echo "--- got:" >&2; head -8 "$TMP/got" >&2
    fail "hidden program $name: output or exit code mismatch"
  fi
done
echo "CHECK PASS"
exit 0
