#!/usr/bin/env bash
# cwd = copy of the workspace after the agent finished; TASK_DIR = task directory.
set -euo pipefail
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR

BAD=$(tr -d '[:space:]' < "$CHECKER_DIR/expected/bad_commit.txt")
FIRST=$(tr -d '[:space:]' < "$CHECKER_DIR/expected/first_commit.txt")
ORIG_HEAD=$(tr -d '[:space:]' < "$CHECKER_DIR/expected/orig_head.txt")

[ -d pricer/.git ] || { echo "FAIL: pricer/.git missing"; exit 1; }
[ -f regression.txt ] || { echo "FAIL: regression.txt missing"; exit 1; }

# 1. regression.txt names the bad commit (whitespace-tolerant, nothing else).
GOT=$(tr -d '[:space:]' < regression.txt)
if [ "$GOT" != "$BAD" ]; then
    echo "FAIL: regression.txt has '$GOT', expected '$BAD'"
    exit 1
fi

cd pricer

# 2. tests/ and conftest.py are byte-identical to the originals.
python3 - "$CHECKER_DIR/expected/tests.sha256" <<'PY'
import hashlib
import pathlib
import sys

paths = sorted([str(p) for p in pathlib.Path("tests").rglob("*.py")] + ["conftest.py"])
lines = ["%s  %s" % (hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest(), p)
         for p in paths]
expected = pathlib.Path(sys.argv[1]).read_text().strip().splitlines()
if lines != expected:
    sys.exit("FAIL: tests/ or conftest.py were modified (or files added/removed)")
PY

# 3. History not rewritten: all 30 original commits still reachable from HEAD.
git cat-file -e "$BAD" || { echo "FAIL: bad commit object missing"; exit 1; }
git merge-base --is-ancestor "$FIRST" HEAD \
    || { echo "FAIL: original first commit no longer an ancestor of HEAD"; exit 1; }
git merge-base --is-ancestor "$ORIG_HEAD" HEAD \
    || { echo "FAIL: original HEAD no longer an ancestor of HEAD (history rewritten?)"; exit 1; }

# 4. Full suite green at the current working tree.
python3 -m pytest -q -p no:cacheprovider
