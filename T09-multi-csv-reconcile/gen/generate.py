#!/usr/bin/env python3
"""Deterministic fixture + expected-output generator for T09-multi-csv-reconcile.

Generates six warehouse inventory files (each in a different format), rates.json,
and expected/reconciled.csv. All derived from one seeded random stream.
A rounding guard retries with the next seed if any SKU's USD total lands too
close to a half-cent boundary (so any standard 2dp rounding gives the same result).
"""
import csv
import io
import json
import math
import os
import random
import sys

TASK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(TASK, "fixture")
EXPECTED = os.path.join(TASK, "expected")

EUR_USD = 1.09
LETTERS = ["a", "b", "c", "d", "e", "f"]


def build_rows(seed):
    rng = random.Random(seed)
    skus = [f"SKU-{n:04d}" for n in rng.sample(range(100, 9900), 60)]
    rows = []  # (warehouse, sku, qty, unit_cost, currency, date)
    for sku in skus:
        k = rng.choices([1, 2, 3, 4], weights=[30, 35, 25, 10])[0]
        homes = rng.sample(LETTERS, k)
        for wh in homes:
            if wh == "f" and rng.random() < 0.55:
                qty = rng.randint(1000, 9500)
            else:
                qty = rng.randint(1, 950)
            if wh == "f" and rng.random() < 0.35:
                cost = round(rng.uniform(1000.0, 4800.0), 2)
            else:
                cost = round(rng.uniform(0.55, 890.0), 2)
            ccy = rng.choice(["USD", "USD", "EUR"])
            date = (rng.randint(2023, 2025), rng.randint(1, 12), rng.randint(1, 28))
            rows.append((wh, sku, qty, cost, ccy, date))
    # a few intra-warehouse duplicate SKUs (same sku twice in one warehouse)
    dup_pool = [r for r in rows if r[0] in ("c", "d")]
    for r in rng.sample(dup_pool, 5):
        wh, sku, _, _, _, _ = r
        qty = rng.randint(1, 400)
        cost = round(rng.uniform(1.0, 400.0), 2)
        ccy = rng.choice(["USD", "EUR"])
        date = (rng.randint(2023, 2025), rng.randint(1, 12), rng.randint(1, 28))
        rows.append((wh, sku, qty, cost, ccy, date))
    rng.shuffle(rows)
    return skus, rows


def totals(rows):
    agg = {}
    for wh, sku, qty, cost, ccy, _ in rows:
        usd = cost * EUR_USD if ccy == "EUR" else cost
        u, v, ws = agg.get(sku, (0, 0.0, set()))
        agg[sku] = (u + qty, v + qty * usd, ws | {wh})
    return agg


def rounding_safe(agg):
    for _, (_, v, _) in agg.items():
        # distance of v*1000 from an exact ...5 (half-cent) boundary
        frac = (v * 1000.0) % 10.0
        if abs(frac - 5.0) < 0.25:
            return False
    return True


def fmt_date(d, style):
    y, m, day = d
    if style == "iso":
        return f"{y:04d}-{m:02d}-{day:02d}"
    if style == "eu":
        return f"{day:02d}.{m:02d}.{y:04d}"
    if style == "us":
        return f"{m:02d}/{day:02d}/{y:04d}"
    raise ValueError(style)


def thousands(n):
    return f"{n:,}"


def thousands_f(x):
    return f"{x:,.2f}"


def write_files(rows):
    by = {w: [] for w in LETTERS}
    for r in rows:
        by[r[0]].append(r)
    for w in LETTERS:
        os.makedirs(os.path.join(FIX, "warehouse", w), exist_ok=True)

    # a: plain CSV
    with open(os.path.join(FIX, "warehouse", "a", "inventory.csv"), "w", newline="\n") as f:
        wtr = csv.writer(f, lineterminator="\n")
        wtr.writerow(["sku", "qty", "unit_cost", "currency", "updated"])
        for _, sku, qty, cost, ccy, d in by["a"]:
            wtr.writerow([sku, qty, f"{cost:.2f}", ccy, fmt_date(d, "iso")])

    # b: CSV, different column names and order
    with open(os.path.join(FIX, "warehouse", "b", "stock.csv"), "w", newline="\n") as f:
        wtr = csv.writer(f, lineterminator="\n")
        wtr.writerow(["item_code", "cost_per_unit", "count", "ccy", "as_of"])
        for _, sku, qty, cost, ccy, d in by["b"]:
            wtr.writerow([sku, f"{cost:.2f}", qty, ccy, fmt_date(d, "iso")])

    # c: TSV
    with open(os.path.join(FIX, "warehouse", "c", "inventory.tsv"), "w", newline="\n") as f:
        wtr = csv.writer(f, delimiter="\t", lineterminator="\n")
        wtr.writerow(["sku", "qty", "unit_cost", "currency", "updated"])
        for _, sku, qty, cost, ccy, d in by["c"]:
            wtr.writerow([sku, qty, f"{cost:.2f}", ccy, fmt_date(d, "iso")])

    # d: JSON lines
    with open(os.path.join(FIX, "warehouse", "d", "inventory.jsonl"), "w", newline="\n") as f:
        for _, sku, qty, cost, ccy, d in by["d"]:
            f.write(json.dumps({"sku": sku, "qty": qty, "unit_cost": round(cost, 2),
                                "currency": ccy, "updated": fmt_date(d, "iso")},
                               separators=(", ", ": ")) + "\n")

    # e: semicolon CSV, decimal commas, DD.MM.YYYY
    with open(os.path.join(FIX, "warehouse", "e", "inventory.csv"), "w", newline="\n") as f:
        wtr = csv.writer(f, delimiter=";", lineterminator="\n")
        wtr.writerow(["sku", "qty", "unit_cost", "currency", "updated"])
        for _, sku, qty, cost, ccy, d in by["e"]:
            wtr.writerow([sku, qty, f"{cost:.2f}".replace(".", ","), ccy, fmt_date(d, "eu")])

    # f: comma CSV with thousands separators (quoted), MM/DD/YYYY
    with open(os.path.join(FIX, "warehouse", "f", "inventory.csv"), "w", newline="\n") as f:
        wtr = csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        wtr.writerow(["sku", "qty", "unit_cost", "currency", "updated"])
        for _, sku, qty, cost, ccy, d in by["f"]:
            wtr.writerow([sku, thousands(qty), thousands_f(cost), ccy, fmt_date(d, "us")])

    with open(os.path.join(FIX, "rates.json"), "w", newline="\n") as f:
        json.dump({"EUR_USD": EUR_USD}, f)
        f.write("\n")


def write_expected(agg):
    os.makedirs(EXPECTED, exist_ok=True)
    buf = io.StringIO()
    buf.write("sku,total_units,total_value_usd,warehouses\n")
    for sku in sorted(agg):
        u, v, ws = agg[sku]
        buf.write(f"{sku},{u},{v:.2f},{''.join(sorted(ws))}\n")
    with open(os.path.join(EXPECTED, "reconciled.csv"), "w", newline="\n") as f:
        f.write(buf.getvalue())


def main():
    seed = 90901
    for attempt in range(200):
        skus, rows = build_rows(seed + attempt)
        agg = totals(rows)
        if rounding_safe(agg):
            print(f"seed={seed + attempt} rows={len(rows)} skus={len(agg)}")
            write_files(rows)
            write_expected(agg)
            return
    print("no rounding-safe seed found", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
