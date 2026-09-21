#!/usr/bin/env bash
# cwd = copy of the workspace after the agent finished; TASK_DIR = task directory.
set -euo pipefail
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR

# 1. tests/ byte-identical to the shipped fixture.
python3 - "$CHECKER_DIR/expected/tests.sha256" <<'PY'
import hashlib
import pathlib
import sys

paths = sorted(
    p for p in pathlib.Path("tests").rglob("*")
    if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
)
lines = ["%s  %s" % (hashlib.sha256(p.read_bytes()).hexdigest(), p) for p in paths]
expected = pathlib.Path(sys.argv[1]).read_text().strip().splitlines()
if lines != expected:
    sys.exit("FAIL: tests/ was modified (or files added/removed)")
PY

# 2. Structure: three concern modules, thin facade, file size limits.
python3 - <<'PY'
import pathlib
import re
import sys

src = pathlib.Path("src")
for name in ("parsing.py", "validation.py", "rendering.py"):
    path = src / name
    if not path.is_file():
        sys.exit(f"FAIL: {path} missing")
    if not re.search(r"^def \w+", path.read_text(), re.M):
        sys.exit(f"FAIL: {path} defines no top-level functions")

mega = src / "megamodule.py"
text = mega.read_text()
n = len(text.splitlines())
if n > 60:
    sys.exit(f"FAIL: src/megamodule.py has {n} lines (max 60)")
for mod in ("parsing", "validation", "rendering"):
    if not re.search(rf"^\s*(from\s+{mod}\s+import|import\s+{mod}\b)", text, re.M):
        sys.exit(f"FAIL: src/megamodule.py does not import from {mod}")
if re.search(r"^(def |class )", text, re.M):
    sys.exit("FAIL: src/megamodule.py must not define functions or classes")

for path in src.rglob("*.py"):
    count = len(path.read_text().splitlines())
    if count > 150:
        sys.exit(f"FAIL: {path} has {count} lines (max 150)")
print("structure OK")
PY

# 3. Behavior preserved: full suite green.
python3 -m pytest -q -p no:cacheprovider tests
