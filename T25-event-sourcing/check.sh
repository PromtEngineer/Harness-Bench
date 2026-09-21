#!/usr/bin/env bash
# Checker for T25-event-sourcing. cwd = workspace copy; TASK_DIR = task dir.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR
fail() { echo "CHECK FAIL: $*" >&2; exit 1; }
[ -n "${CHECKER_DIR:-}" ] || fail "TASK_DIR is not set"

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

[ -f state.json ] || fail "state.json is missing from the workspace root"
python3 - "$CHECKER_DIR/expected/state.json" <<'PYEOF' || exit 1
import json, sys
def die(m):
    print(f"CHECK FAIL: {m}", file=sys.stderr); sys.exit(1)
try:
    got = json.load(open("state.json"))
except Exception as e:
    die(f"state.json is not valid JSON: {e}")
want = json.load(open(sys.argv[1]))
if not isinstance(got, dict) or set(got) != {"stock", "stats"}:
    die("state.json must have exactly the keys 'stock' and 'stats'")
def is_int(x): return isinstance(x, int) and not isinstance(x, bool)
if not all(is_int(v) for v in got["stock"].values()):
    die("all stock values must be JSON integers")
if not all(is_int(v) for v in got["stats"].values()):
    die("all stats values must be JSON integers")
if got["stats"] != want["stats"]:
    for k in want["stats"]:
        if got["stats"].get(k) != want["stats"][k]:
            die(f"stats.{k}: got {got['stats'].get(k)!r}, expected {want['stats'][k]!r}")
    die(f"stats keys mismatch: {sorted(got['stats'])}")
if got["stock"] != want["stock"]:
    gk, wk = set(got["stock"]), set(want["stock"])
    for k in sorted(wk - gk)[:3]:
        print(f"CHECK FAIL: stock slot {k} missing (want {want['stock'][k]})",
              file=sys.stderr)
    for k in sorted(gk - wk)[:3]:
        print(f"CHECK FAIL: unexpected stock slot {k} (got {got['stock'][k]})",
              file=sys.stderr)
    for k in sorted(gk & wk):
        if got["stock"][k] != want["stock"][k]:
            print(f"CHECK FAIL: stock {k}: got {got['stock'][k]}, "
                  f"expected {want['stock'][k]}", file=sys.stderr)
            break
    sys.exit(1)
print("state.json matches the reference reduction")
PYEOF
[ $? -eq 0 ] || exit 1
echo "CHECK PASS"
exit 0
