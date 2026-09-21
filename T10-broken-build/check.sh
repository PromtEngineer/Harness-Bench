#!/usr/bin/env bash
# T10-broken-build checker.
# cwd = copy of the workspace after the agent ran; TASK_DIR = task directory.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR

if [ -z "${CHECKER_DIR:-}" ]; then
  echo "FAIL: TASK_DIR not set" >&2
  exit 2
fi

export PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_INPUT=1

# 1) Integrity guard: tests/ and wheels/ must be byte-identical to the fixture
#    (exact file set: nothing modified, added, or removed).
python3 - "$CHECKER_DIR/expected/protected.sha256" <<'PY' || exit 1
import hashlib, os, sys

manifest = {}
with open(sys.argv[1]) as f:
    for line in f:
        line = line.rstrip("\n")
        if not line:
            continue
        digest, rel = line.split("  ", 1)
        manifest[rel] = digest

actual = {}
for sub in ("tests", "wheels"):
    if not os.path.isdir(sub):
        print(f"FAIL: protected directory {sub}/ is missing", file=sys.stderr)
        sys.exit(1)
    for dirpath, dirnames, filenames in os.walk(sub):
        # ignore transient bytecode caches
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in filenames:
            if name.endswith(".pyc"):
                continue
            p = os.path.join(dirpath, name)
            actual[p] = hashlib.sha256(open(p, "rb").read()).hexdigest()

ok = True
for rel, digest in manifest.items():
    if rel not in actual:
        print(f"FAIL: protected file removed: {rel}", file=sys.stderr); ok = False
    elif actual[rel] != digest:
        print(f"FAIL: protected file modified: {rel}", file=sys.stderr); ok = False
for rel in actual:
    if rel not in manifest:
        print(f"FAIL: unexpected file added under protected dir: {rel}", file=sys.stderr); ok = False
sys.exit(0 if ok else 1)
PY
[ $? -eq 0 ] || exit 1

# 2) No pytest-hijacking conftest/config outside tests/ (fixture ships none).
for f in conftest.py pytest.ini tox.ini setup.cfg; do
  if [ -e "$f" ]; then
    echo "FAIL: unexpected $f in workspace root" >&2
    exit 1
  fi
done

# 3) Fresh-venv build+test: the exact pipeline from the prompt.
rm -rf .venv
python3 -m venv .venv \
  && .venv/bin/pip install --no-index --find-links wheels setuptools pytest \
  && .venv/bin/pip install -e . --no-index --no-build-isolation \
  && .venv/bin/python -m pytest -q -p no:cacheprovider
rc=$?
if [ $rc -ne 0 ]; then
  echo "FAIL: build/install/test pipeline exited $rc" >&2
  exit 1
fi

echo "PASS: package builds, installs offline, and all tests pass"
exit 0
