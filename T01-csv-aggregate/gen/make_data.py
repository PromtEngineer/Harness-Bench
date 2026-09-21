#!/usr/bin/env python3
"""Build-time generator for T01-csv-aggregate. Deterministic (seed 20260101).

Writes fixture/data/<region>/sales-2026-<MM>.csv (9 files) and
expected/results.json (ground truth, computed in integer cents).
"""
import csv
import json
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(ROOT, "fixture")
EXPECTED = os.path.join(ROOT, "expected")

REGIONS = ["north", "south", "west"]
MONTHS = ["2026-01", "2026-02", "2026-03"]
DAYS = {"2026-01": 31, "2026-02": 28, "2026-03": 31}

PLAIN_SKUS = [
    "WGT-100", "WGT-200", "GAD-050", "GAD-075",
    "THB-300", "SPR-410", "CBL-220", "BRK-990",
]
# These sku names contain commas (and one contains double quotes) so the CSV
# writer quotes them -> exercises real CSV parsing on the agent side.
COMMA_SKUS = [
    "KIT, DELUXE 12PC",
    "BUNDLE, STARTER (A,B)",
    "CABLE PACK, 3M/5M",
    'TOOL SET, "PRO", V2',
]


def main():
    rng = random.Random(20260101)
    totals = {r: {"revenue_cents": 0, "units": 0} for r in REGIONS}
    for region in REGIONS:
        outdir = os.path.join(FIXTURE, "data", region)
        os.makedirs(outdir, exist_ok=True)
        for month in MONTHS:
            n = rng.randint(190, 212)
            rows = []
            for _ in range(n):
                day = rng.randint(1, DAYS[month])
                date = f"{month}-{day:02d}"
                if rng.random() < 0.12:
                    sku = rng.choice(COMMA_SKUS)
                else:
                    sku = rng.choice(PLAIN_SKUS)
                units = rng.randint(1, 40)
                price_cents = rng.randint(199, 24999)
                rows.append((date, region, sku, units, price_cents))
            rows.sort(key=lambda r: r[0])
            path = os.path.join(outdir, f"sales-{month}.csv")
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["date", "region", "sku", "units", "unit_price_usd"])
                for date, reg, sku, units, pc in rows:
                    w.writerow([date, reg, sku, units, f"{pc / 100:.2f}"])
                    totals[reg]["revenue_cents"] += units * pc
                    totals[reg]["units"] += units

    os.makedirs(EXPECTED, exist_ok=True)
    results = {
        r: {
            "revenue_usd": round(totals[r]["revenue_cents"] / 100, 2),
            "units": totals[r]["units"],
        }
        for r in REGIONS
    }
    with open(os.path.join(EXPECTED, "results.json"), "w") as f:
        json.dump(results, f, indent=2)
        f.write("\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
