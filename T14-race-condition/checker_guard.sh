#!/usr/bin/env bash
# Sourced by every task checker before invoking Python from the submitted cwd.

if [ -z "${TASK_DIR:-}" ] || [ ! -d "$TASK_DIR" ]; then
  echo "FAIL: TASK_DIR is not set to a task directory" >&2
  return 1
fi

unset PYTHONPATH PYTHONHOME PYTHONSTARTUP PYTHONBREAKPOINT PYTHONWARNINGS
unset PYTHONINSPECT BASH_ENV ENV CDPATH
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
# Neutralize project-controlled collection/addopts overrides while preserving
# normal workspace discovery, and never write grader caches.
export PYTEST_ADDOPTS="--override-ini addopts= --override-ini testpaths= \
--override-ini python_files=test_*.py --override-ini python_classes=Test* \
--override-ini python_functions=test_* -p no:cacheprovider"

for path in \
  sitecustomize.py sitecustomize usercustomize.py usercustomize \
  pytest.py pytest json.py json hashlib.py hashlib subprocess.py subprocess \
  pytest.ini tox.ini setup.cfg; do
  if [ -e "$path" ]; then
    echo "FAIL: unexpected checker-control or stdlib-shadowing file: $path" >&2
    return 1
  fi
done

# Two fixtures intentionally contain an empty, sha256-guarded conftest.py.
# In every other case a root conftest can replace or suppress grader tests.
if [ -e conftest.py ]; then
  manifest="$TASK_DIR/expected/fixture.sha256"
  want=""
  if [ -f "$manifest" ]; then
    want=$(awk '$2 == "conftest.py" { print $1; exit }' "$manifest")
  fi
  if [ -z "$want" ]; then
    echo "FAIL: unexpected checker-control file: conftest.py" >&2
    return 1
  fi
  if command -v sha256sum >/dev/null 2>&1; then
    have=$(sha256sum conftest.py | awk '{ print $1 }')
  else
    have=$(shasum -a 256 conftest.py | awk '{ print $1 }')
  fi
  if [ "$have" != "$want" ]; then
    echo "FAIL: conftest.py is not the guarded fixture copy" >&2
    return 1
  fi
fi

# Python starts with the submitted cwd on sys.path. Reject any new root module
# or package that could shadow the standard library (or pytest) while grader
# scripts start. Isolated mode makes this scan independent of the submission.
python3 -I - "$TASK_DIR" <<'PYEOF' || return 1
from pathlib import Path
import sys

reserved = set(sys.stdlib_module_names) | {"pytest", "_pytest"}
task_id = Path(sys.argv[1]).name[:3]
allowed = {"T32": {"sched"}}.get(task_id, set())
for path in Path.cwd().iterdir():
    name = path.name if path.is_dir() else path.stem if path.suffix == ".py" else None
    if name in reserved and name not in allowed:
        print(
            f"FAIL: root module/package shadows grader dependency: {path.name}",
            file=sys.stderr,
        )
        raise SystemExit(1)
PYEOF
