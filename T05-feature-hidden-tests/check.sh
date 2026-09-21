#!/usr/bin/env bash
# cwd = copy of the workspace after the agent finished; TASK_DIR = task directory.
set -euo pipefail
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR

[ -f ratelimiter.py ] || { echo "FAIL: ratelimiter.py missing"; exit 1; }

python3 - "$CHECKER_DIR/expected/fixture.sha256" <<'PY'
import hashlib
import pathlib
import sys

expected = {}
for line in pathlib.Path(sys.argv[1]).read_text().splitlines():
    digest, rel = line.split("  ", 1)
    expected[rel] = digest
for rel, digest in expected.items():
    path = pathlib.Path(rel)
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise SystemExit(f"FAIL: guarded fixture file changed: {rel}")
print("fixture inputs intact")
PY

export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
python3 -m pytest -q -p no:cacheprovider "$CHECKER_DIR/hidden/test_hidden.py"
