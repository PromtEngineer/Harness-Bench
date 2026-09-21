#!/usr/bin/env python3
"""Reference solution for T01-csv-aggregate. Run with cwd = workspace root."""
import csv
import json
import os

REGIONS = ["north", "south", "west"]
MONTHS = ["2026-01", "2026-02", "2026-03"]

results = {}
for region in REGIONS:
    revenue = 0.0
    units = 0
    for month in MONTHS:
        path = os.path.join("data", region, f"sales-{month}.csv")
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                u = int(row["units"])
                p = float(row["unit_price_usd"])
                revenue += u * p
                units += u
    results[region] = {"revenue_usd": round(revenue, 2), "units": units}

with open("results.json", "w") as f:
    json.dump(results, f, indent=2)
    f.write("\n")
print(json.dumps(results))
