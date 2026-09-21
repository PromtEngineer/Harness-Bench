#!/usr/bin/env python3
"""Reference solution for T09-multi-csv-reconcile. Run from the workspace root."""
import csv
import json


def num_int(s):
    return int(str(s).replace(",", "").strip())


def num_float_us(s):
    return float(str(s).replace(",", "").strip())


def num_float_eu(s):
    return float(str(s).strip().replace(".", "").replace(",", "."))


rows = []  # (warehouse, sku, qty, unit_cost_native, currency)

with open("warehouse/a/inventory.csv", newline="") as f:
    for r in csv.DictReader(f):
        rows.append(("a", r["sku"], int(r["qty"]), float(r["unit_cost"]), r["currency"]))

with open("warehouse/b/stock.csv", newline="") as f:
    for r in csv.DictReader(f):
        rows.append(("b", r["item_code"], int(r["count"]), float(r["cost_per_unit"]), r["ccy"]))

with open("warehouse/c/inventory.tsv", newline="") as f:
    for r in csv.DictReader(f, delimiter="\t"):
        rows.append(("c", r["sku"], int(r["qty"]), float(r["unit_cost"]), r["currency"]))

with open("warehouse/d/inventory.jsonl") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        rows.append(("d", o["sku"], int(o["qty"]), float(o["unit_cost"]), o["currency"]))

with open("warehouse/e/inventory.csv", newline="") as f:
    for r in csv.DictReader(f, delimiter=";"):
        rows.append(("e", r["sku"], int(r["qty"]), num_float_eu(r["unit_cost"]), r["currency"]))

with open("warehouse/f/inventory.csv", newline="") as f:
    for r in csv.DictReader(f):
        rows.append(("f", r["sku"], num_int(r["qty"]), num_float_us(r["unit_cost"]), r["currency"]))

rate = json.load(open("rates.json"))["EUR_USD"]

agg = {}
for wh, sku, qty, cost, ccy in rows:
    usd = cost * rate if ccy == "EUR" else cost
    u, v, ws = agg.get(sku, (0, 0.0, set()))
    agg[sku] = (u + qty, v + qty * usd, ws | {wh})

with open("reconciled.csv", "w", newline="\n") as f:
    f.write("sku,total_units,total_value_usd,warehouses\n")
    for sku in sorted(agg):
        u, v, ws = agg[sku]
        f.write(f"{sku},{u},{v:.2f},{''.join(sorted(ws))}\n")
