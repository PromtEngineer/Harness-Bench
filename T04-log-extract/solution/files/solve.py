#!/usr/bin/env python3
"""Reference solution for T04-log-extract. Run with cwd = workspace root."""
import collections
import json
import re

counts = collections.Counter()
upstream_by_rid = {}

with open("logs/app.log") as f:
    for line in f:
        if "status=500" not in line or " path=/api/checkout " not in line:
            continue
        rid = re.search(r"request_id=(\S+)", line).group(1)
        counts[rid] += 1
        m = re.search(r"upstream=(\S+)", line)
        if m:
            upstream_by_rid[rid] = m.group(1)

winners = [(rid, n) for rid, n in counts.items() if n >= 3]
assert len(winners) == 1, winners
rid, n = winners[0]

answer = {
    "request_id": rid,
    "upstream_service": upstream_by_rid[rid],
    "error_count": n,
}
with open("answer.json", "w") as f:
    json.dump(answer, f, indent=2)
    f.write("\n")
print(json.dumps(answer))
