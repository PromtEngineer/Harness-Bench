#!/usr/bin/env bash
# T15-migrate-callbacks checker. cwd = workspace copy, TASK_DIR = task dir.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR

if [ -z "${CHECKER_DIR:-}" ]; then
  echo "FAIL: TASK_DIR not set" >&2
  exit 2
fi

# 1. tests/ must be exactly the shipped files (no edits, no additions).
python3 - "$CHECKER_DIR" <<'PYEOF' || exit 1
import glob, hashlib, os, sys
task_dir = sys.argv[1]
fails = []
known = {}
for line in open(os.path.join(task_dir, "expected", "tests.sha256")):
    digest, rel = line.strip().split("  ", 1)
    known[rel] = digest
for rel, digest in known.items():
    if not os.path.exists(rel):
        fails.append(f"guarded test file missing: {rel}")
    elif hashlib.sha256(open(rel, "rb").read()).hexdigest() != digest:
        fails.append(f"guarded test file modified: {rel}")
extra = {p for p in glob.glob("tests/**/*.py", recursive=True)
         if "__pycache__" not in p} - set(known)
if extra:
    fails.append(f"unexpected python files added under tests/: {sorted(extra)}")
if fails:
    for m in fails:
        print(f"FAIL: {m}")
    sys.exit(1)
print("OK: tests/ unmodified")
PYEOF

if [ ! -d taskflow ]; then
  echo "FAIL: taskflow/ missing"
  exit 1
fi

# 2. structural asserts on the migrated library
if grep -rni -e "on_ok" -e "on_err" -e "callback" --include='*.py' taskflow/; then
  echo "FAIL: callback-style identifiers still present in taskflow/ (see above)"
  exit 1
fi
echo "OK: no on_ok/on_err/callback in taskflow/"

ASYNC_COUNT=$(grep -rho "async def" --include='*.py' taskflow/ | wc -l | tr -d '[:space:]')
if [ "${ASYNC_COUNT:-0}" -lt 6 ]; then
  echo "FAIL: only ${ASYNC_COUNT:-0} 'async def' in taskflow/ (need >= 6)"
  exit 1
fi
echo "OK: $ASYNC_COUNT async def functions"

MODS=$(grep -rl "import asyncio" --include='*.py' taskflow/ | wc -l | tr -d '[:space:]')
if [ "${MODS:-0}" -lt 3 ]; then
  echo "FAIL: only ${MODS:-0} modules import asyncio (need >= 3)"
  exit 1
fi
echo "OK: $MODS modules import asyncio"

# 3. The required fan-out must use asyncio.gather and must actually overlap
#    source coroutines. The behavioral probe deadlocks under sequential awaits.
python3 - <<'PYEOF' || exit 1
import ast
import asyncio
from pathlib import Path

uses_gather = False
for path in Path("taskflow").rglob("*.py"):
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "asyncio"
                and node.func.attr == "gather"):
            uses_gather = True
if not uses_gather:
    raise SystemExit("FAIL: taskflow/ must call asyncio.gather for source fan-out")

from taskflow import pipeline
from taskflow.api import PipelineConfig


async def probe():
    started = 0
    all_started = asyncio.Event()

    async def fetch(name):
        nonlocal started
        started += 1
        if started == 3:
            all_started.set()
        await asyncio.wait_for(all_started.wait(), timeout=1.0)
        return []

    async def transform(records, config):
        return records

    async def collect(records):
        return {"count": 0, "total": 0, "by_source": {}}

    pipeline.source.fetch = fetch
    pipeline.transform.transform_records = transform
    pipeline.sink.collect = collect
    result = await asyncio.wait_for(
        pipeline.run(PipelineConfig(sources=["alpha", "beta", "gamma"])),
        timeout=2.0,
    )
    if started != 3 or result.records != []:
        raise AssertionError("source fan-out probe returned an invalid result")


asyncio.run(probe())
print("OK: asyncio.gather fan-out overlaps source coroutines")
PYEOF

# 4. behavior: all 10 tests green
if ! python3 -m pytest tests/ -q; then
  echo "FAIL: pytest failed"
  exit 1
fi
echo "PASS: structure migrated and all tests green"
