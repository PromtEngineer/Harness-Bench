#!/usr/bin/env python3
"""Reference computation of expected/report.json from fixture/db/sales.db."""

import itertools
import json
import pathlib
import sqlite3
from collections import Counter, defaultdict

TASK = pathlib.Path(__file__).resolve().parent.parent
con = sqlite3.connect(TASK / "fixture" / "db" / "sales.db")
cur = con.cursor()

# Per-order totals and metadata.
totals = dict(cur.execute(
    "SELECT order_id, SUM(quantity * unit_price) FROM order_items GROUP BY order_id"))
orders = list(cur.execute("SELECT order_id, customer_id, region, status, order_date FROM orders"))

# q1: customer with highest lifetime net revenue (excluding refunded orders).
by_cust = defaultdict(float)
for oid, cid, region, status, d in orders:
    if status != "refunded":
        by_cust[cid] += totals.get(oid, 0.0)
ranked = sorted(by_cust.items(), key=lambda kv: (-kv[1], kv[0]))
assert ranked[0][1] - ranked[1][1] > 0.01, ranked[:3]
q1 = ranked[0][0]

# q2: 2025 month with highest net-revenue growth vs previous calendar month.
by_month = defaultdict(float)
for oid, cid, region, status, d in orders:
    if status != "refunded":
        by_month[d[:7]] += totals.get(oid, 0.0)
def prev_month(m):
    y, mo = int(m[:4]), int(m[5:7])
    return f"{y - 1}-12" if mo == 1 else f"{y}-{mo - 1:02d}"
growth = {m: by_month.get(m, 0.0) - by_month.get(prev_month(m), 0.0)
          for m in (f"2025-{i:02d}" for i in range(1, 13))}
g_ranked = sorted(growth.items(), key=lambda kv: (-kv[1], kv[0]))
assert g_ranked[0][1] - g_ranked[1][1] > 0.01, g_ranked[:3]
q2 = g_ranked[0][0]

# q3: median non-refunded order value per region (even count -> mean of middle two).
by_region = defaultdict(list)
for oid, cid, region, status, d in orders:
    if status != "refunded":
        by_region[region].append(totals.get(oid, 0.0))
q3 = {}
for region, vals in sorted(by_region.items()):
    vals.sort()
    n = len(vals)
    med = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2.0
    q3[region] = round(med, 2)

# q4: most frequent co-purchased product pair (distinct per order, all statuses).
pair_counts = Counter()
order_prods = defaultdict(set)
for oid, pid in cur.execute("SELECT order_id, product_id FROM order_items"):
    order_prods[oid].add(pid)
for pids in order_prods.values():
    for a, b in itertools.combinations(sorted(pids), 2):
        pair_counts[(a, b)] += 1
p_ranked = pair_counts.most_common(3)
assert p_ranked[0][1] > p_ranked[1][1], p_ranked
q4 = list(p_ranked[0][0])

# q5: gross revenue minus refunded-order revenue.
gross = sum(totals.values())
refunded = sum(totals.get(oid, 0.0)
               for oid, cid, region, status, d in orders if status == "refunded")
q5 = round(gross - refunded, 2)

report = {"q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5}
out = TASK / "expected" / "report.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
sol = TASK / "solution" / "files" / "report.json"
sol.parent.mkdir(parents=True, exist_ok=True)
sol.write_text(out.read_text())
print(json.dumps(report, sort_keys=True))
