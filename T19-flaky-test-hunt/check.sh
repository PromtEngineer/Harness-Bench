#!/usr/bin/env bash
# Checker for T19-flaky-test-hunt. cwd = copy of the workspace after the agent
# ran. env: TASK_DIR = absolute path of the task directory.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR

CACHE_FILE=/tmp/statlib_cache.tmp

fail() { echo "CHECK FAIL: $*" >&2; rm -f "$CACHE_FILE"; exit 1; }

[ -n "${CHECKER_DIR:-}" ] || fail "TASK_DIR is not set"
[ -d statlib ] || fail "statlib/ missing from the workspace"
[ -d tests ] || fail "tests/ missing from the workspace"

# 1. tests/ must be byte-identical to the shipped fixture (sha256 manifest:
#    no modified, deleted, or added files).
python3 - "$CHECKER_DIR/expected/tests.manifest" <<'PYEOF' || exit 1
import hashlib, os, sys
want = sorted(line for line in open(sys.argv[1]).read().splitlines() if line)
have = []
for root, dirs, files in os.walk("tests"):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for name in sorted(files):
        if name.endswith(".pyc"):
            continue
        path = os.path.join(root, name)
        h = hashlib.sha256(open(path, "rb").read()).hexdigest()
        have.append(f"{h}  {path.replace(os.sep, '/')}")
have.sort(key=lambda line: line.split("  ", 1)[1])
want.sort(key=lambda line: line.split("  ", 1)[1])
if have != want:
    print("CHECK FAIL: tests/ was modified", file=sys.stderr)
    for line in sorted(set(want) - set(have)):
        print(f"  missing or changed: {line}", file=sys.stderr)
    for line in sorted(set(have) - set(want)):
        print(f"  unexpected: {line}", file=sys.stderr)
    sys.exit(1)
PYEOF
[ $? -eq 0 ] || exit 1

# 2. The suite must pass 10/10 consecutive runs under cycling PYTHONHASHSEED.
#    The scratch file is cleared once before the loop, NOT between runs, so
#    leftover-state bugs surface on the second run.
LOG="$(mktemp)"
rm -f "$CACHE_FILE"
for seed in 0 1 2 42 99 7 13 21 34 55; do
    if ! PYTHONHASHSEED=$seed python3 -m pytest -q -p no:cacheprovider tests/ >"$LOG" 2>&1; then
        cat "$LOG" >&2
        fail "test suite failed with PYTHONHASHSEED=$seed"
    fi
done
rm -f "$LOG"
echo "suite passed 10/10 runs under cycling PYTHONHASHSEED"

# 3. Mutation guard: re-introduce each original library bug into a scratch
#    copy of the workspace; the unchanged test suite must FAIL (under at
#    least one of the listed hash seeds for the set-order bugs).
run_mutated() {
    # $1 = mutation number; remaining args = PYTHONHASHSEED values to try.
    # Returns 0 iff the suite FAILED under at least one seed (bug detected).
    local m="$1"; shift
    local scratch rc
    scratch="$(mktemp -d)"
    cp -R . "$scratch/ws" || { rm -rf "$scratch"; fail "could not copy workspace"; }
    if ! python3 "$CHECKER_DIR/mutations/m$m.py" "$scratch/ws"; then
        rm -rf "$scratch"
        fail "mutation m$m could not be applied: the solution diverged structurally from the required module/function layout (see mutations/README.md)"
    fi
    rc=1
    for seed in "$@"; do
        if ! ( cd "$scratch/ws" && PYTHONHASHSEED=$seed python3 -m pytest -q -p no:cacheprovider tests/ >/dev/null 2>&1 ); then
            rc=0
            break
        fi
    done
    rm -rf "$scratch"
    return $rc
}

run_mutated 1 0 1 42 \
    || fail "mutation m1 (unsorted unique_labels) was NOT detected by the unchanged test suite"
echo "mutation m1 detected"

touch "$CACHE_FILE"
run_mutated 2 0 \
    || fail "mutation m2 (fixed scratch path, no cleanup) was NOT detected by the unchanged test suite"
rm -f "$CACHE_FILE"
echo "mutation m2 detected"

run_mutated 3 0 1 42 \
    || fail "mutation m3 (set-order float accumulation) was NOT detected by the unchanged test suite"
echo "mutation m3 detected"

rm -f "$CACHE_FILE"
echo "CHECK PASS"
exit 0
