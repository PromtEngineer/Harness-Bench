#!/usr/bin/env bash
# Checker for T30-unicode-dedupe. cwd = workspace copy; TASK_DIR = task dir.
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

[ -f dedup.json ] || fail "dedup.json is missing from the workspace root"
python3 - "$CHECKER_DIR/expected/dedup.json" <<'PYEOF' || exit 1
import json, sys
def die(m):
    print(f"CHECK FAIL: {m}", file=sys.stderr); sys.exit(1)
try:
    got = json.load(open("dedup.json"))
except Exception as e:
    die(f"dedup.json is not valid JSON: {e}")
want = json.load(open(sys.argv[1]))
if not isinstance(got, dict) or set(got) != {"clusters", "stats"}:
    die("dedup.json must have exactly the keys 'clusters' and 'stats'")
def is_int(x): return isinstance(x, int) and not isinstance(x, bool)
if not (isinstance(got["clusters"], list)
        and all(isinstance(c, list) and all(is_int(i) for i in c)
                for c in got["clusters"])):
    die("clusters must be a list of lists of integers")
if not all(is_int(v) for v in got["stats"].values()):
    die("stats values must be JSON integers")
if got["stats"] != want["stats"]:
    for k in want["stats"]:
        if got["stats"].get(k) != want["stats"][k]:
            die(f"stats.{k}: got {got['stats'].get(k)!r}, "
                f"expected {want['stats'][k]!r}")
    die("stats keys mismatch")
if got["clusters"] != want["clusters"]:
    gmap = {}
    for c in got["clusters"]:
        for i in c:
            gmap[i] = tuple(c)
    wmap = {}
    for c in want["clusters"]:
        for i in c:
            wmap[i] = tuple(c)
    shown = 0
    for i in sorted(wmap):
        if gmap.get(i) != wmap[i] and shown < 3:
            die(f"row {i}: expected cluster {list(wmap[i])}, "
                f"got {list(gmap.get(i, ()))}")
    die("cluster list mismatch (ordering or membership)")
print("dedup.json matches")
PYEOF
[ $? -eq 0 ] || exit 1
echo "CHECK PASS"
exit 0
