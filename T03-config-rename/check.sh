#!/usr/bin/env bash
# T03-config-rename checker. cwd = workspace copy; TASK_DIR = task directory.
set -euo pipefail
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR

# 1. No "Orion" anywhere outside vendor/.
if grep -rn --exclude-dir=vendor --exclude-dir=__pycache__ --exclude-dir=.pytest_cache --exclude-dir=.git "Orion" . ; then
  echo "FAIL: 'Orion' still present outside vendor/"
  exit 1
fi

# 2. "Nova" present in every required file.
for f in src/app/config.py src/app/cli.py pyproject.toml docs/README.md docs/guide.md deploy/compose.yaml tests/test_cli.py; do
  if ! grep -q "Nova" "$f"; then
    echo "FAIL: 'Nova' missing from $f"
    exit 1
  fi
done

# 3. vendor/ and tests/ byte-for-byte unchanged (and tests/ file set unchanged).
python3 - "$CHECKER_DIR" <<'EOF'
import hashlib
import json
import os
import sys

task_dir = sys.argv[1]
with open(os.path.join(task_dir, "expected", "guarded_sha256.json")) as f:
    exp = json.load(f)

for rel, h in exp.items():
    if not os.path.exists(rel):
        print(f"FAIL: guarded file {rel} is missing")
        sys.exit(1)
    with open(rel, "rb") as fh:
        if hashlib.sha256(fh.read()).hexdigest() != h:
            print(f"FAIL: guarded file {rel} was modified")
            sys.exit(1)

guarded_tests = sorted(r for r in exp if r.startswith("tests/"))
got_tests = []
for dirpath, dirnames, filenames in os.walk("tests"):
    dirnames[:] = [d for d in dirnames if d != "__pycache__"]
    for fn in filenames:
        if fn.endswith(".pyc"):
            continue
        got_tests.append(os.path.join(dirpath, fn))
if sorted(got_tests) != guarded_tests:
    print(f"FAIL: tests/ file set changed. found={sorted(got_tests)} expected={guarded_tests}")
    sys.exit(1)
print("guarded files intact")
EOF

# 4. Test suite green.
python3 -m pytest -q
