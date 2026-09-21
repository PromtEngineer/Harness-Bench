#!/usr/bin/env bash
# T13-reimbursement-audit checker. cwd = workspace copy, TASK_DIR = task dir.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR

if [ -z "${CHECKER_DIR:-}" ]; then
  echo "FAIL: TASK_DIR not set" >&2
  exit 2
fi

python3 - "$CHECKER_DIR" <<'PYEOF'
import hashlib
import json
import math
import os
import sys

task_dir = sys.argv[1]
ws = os.getcwd()
fails = []

# 1. sha256-guard fixture inputs
guarded = {}
with open(os.path.join(task_dir, "expected", "fixture.sha256")) as f:
    for line in f:
        digest, rel = line.strip().split("  ", 1)
        guarded[rel] = digest
        p = os.path.join(ws, rel)
        if not os.path.exists(p):
            fails.append(f"guarded file missing: {rel}")
            continue
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        if h != digest:
            fails.append(f"guarded file modified: {rel}")
actual_guarded = {"ledger.csv", "policy.md", "rates.json"}
for root, dirs, files in os.walk("expenses"):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for name in files:
        if not name.endswith(".pyc"):
            actual_guarded.add(os.path.relpath(os.path.join(root, name), ws))
if actual_guarded != set(guarded):
    fails.append(
        "guarded input file set changed: "
        f"missing={sorted(set(guarded) - actual_guarded)} "
        f"added={sorted(actual_guarded - set(guarded))}"
    )

# 2. deliverable exists and parses
out_path = os.path.join(ws, "violations.json")
if not os.path.exists(out_path):
    fails.append("violations.json not found in workspace root")
else:
    try:
        def reject_constant(value):
            raise ValueError(f"non-standard JSON constant {value}")

        got = json.load(open(out_path), parse_constant=reject_constant)
    except Exception as e:
        fails.append(f"violations.json is not valid JSON: {e}")
        got = None
    with open(os.path.join(task_dir, "expected", "violations.json")) as f:
        want = json.load(f)
    if got is not None:
        if not isinstance(got, list):
            fails.append("violations.json must be a JSON array")
        elif len(got) != len(want):
            fails.append(f"expected {len(want)} violations, got {len(got)}")
        else:
            ids = [v.get("claim_id") for v in got if isinstance(v, dict)]
            if ids != sorted(ids):
                fails.append("array not sorted by claim_id ascending")
            for i, (g, w) in enumerate(zip(got, want)):
                if not isinstance(g, dict):
                    fails.append(f"entry {i}: not an object")
                    continue
                if set(g.keys()) != {"claim_id", "rule", "excess_usd"}:
                    fails.append(f"entry {i}: keys must be exactly claim_id/rule/excess_usd")
                    continue
                if g["claim_id"] != w["claim_id"]:
                    fails.append(f"entry {i}: claim_id {g['claim_id']!r} != {w['claim_id']!r}")
                    continue
                if g["rule"] != w["rule"]:
                    fails.append(f"{w['claim_id']}: rule {g['rule']!r} != {w['rule']!r}")
                if (not isinstance(g["excess_usd"], (int, float))
                        or isinstance(g["excess_usd"], bool)
                        or not math.isfinite(float(g["excess_usd"]))):
                    fails.append(f"{w['claim_id']}: excess_usd must be a number")
                elif abs(float(g["excess_usd"]) - w["excess_usd"]) > 0.01 + 1e-9:
                    fails.append(f"{w['claim_id']}: excess_usd {g['excess_usd']} "
                                 f"not within 0.01 of {w['excess_usd']}")

if fails:
    for m in fails:
        print(f"FAIL: {m}")
    sys.exit(1)
print("PASS: violations.json matches expected (12 violations)")
PYEOF
