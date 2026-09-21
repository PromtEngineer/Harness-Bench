#!/usr/bin/env bash
# Build script for T17-perf-fix. Regenerates fixture data, expected outputs,
# and cross-checks naive fixture vs reference solution on a subsample.
set -euo pipefail
TASK="$(cd "$(dirname "$0")/.." && pwd)"

echo "== generating events.csv (seed 170017) =="
python3 "$TASK/gen/gen_events.py" "$TASK/fixture/events.csv"
wc -l "$TASK/fixture/events.csv"

echo "== producing expected/output.json with the reference solution =="
WS="$(mktemp -d)/ws"
mkdir -p "$WS"
cp "$TASK/fixture/events.csv" "$TASK/fixture/report.py" "$WS/"
( cd "$WS" && bash "$TASK/solution/apply.sh" >/dev/null )
python3 - "$WS" <<'PYEOF'
import subprocess, sys, time
ws = sys.argv[1]
t0 = time.monotonic()
subprocess.run([sys.executable, "report.py"], cwd=ws, check=True)
print(f"reference solution full-run wall time: {time.monotonic()-t0:.2f}s (budget 5.0)")
PYEOF
cp "$WS/output.json" "$TASK/expected/output.json"

echo "== cross-check: naive fixture vs reference on 1500-row subsample =="
SUB_N="$(mktemp -d)"; SUB_F="$(mktemp -d)"
head -n 1501 "$TASK/fixture/events.csv" > "$SUB_N/events.csv"
cp "$SUB_N/events.csv" "$SUB_F/events.csv"
cp "$TASK/fixture/report.py" "$SUB_N/report.py"     # naive
cp "$WS/report.py" "$SUB_F/report.py"               # fast reference
python3 - "$SUB_N" <<'PYEOF'
import subprocess, sys, time
t0 = time.monotonic()
subprocess.run([sys.executable, "report.py"], cwd=sys.argv[1], check=True)
naive = time.monotonic() - t0
scale = (80000/1500)**2
print(f"naive on 1500 rows: {naive:.2f}s -> extrapolated full run ~{naive*scale:.0f}s")
assert naive * scale > 120, "naive extrapolation must exceed 120s"
PYEOF
( cd "$SUB_F" && python3 report.py )
cmp "$SUB_N/output.json" "$SUB_F/output.json" \
  && echo "subsample outputs BYTE-IDENTICAL (naive == reference)"

echo "== hashing guarded fixture file =="
python3 - "$TASK" <<'PYEOF'
import hashlib, sys, os
task = sys.argv[1]
h = hashlib.sha256(open(os.path.join(task, "fixture", "events.csv"), "rb").read()).hexdigest()
open(os.path.join(task, "expected", "events.sha256"), "w").write(h + "  events.csv\n")
print("events.csv sha256:", h)
PYEOF

rm -rf "$(dirname "$WS")" "$SUB_N" "$SUB_F"
echo "== T17 build OK =="
