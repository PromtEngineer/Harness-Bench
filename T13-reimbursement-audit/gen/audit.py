#!/usr/bin/env python3
"""Reference auditor for T13-reimbursement-audit.

Parses the generated fixture (ledger.csv + receipt files + rates.json) and
computes the ground-truth expected/violations.json. Cross-checks the result
against gen/planted.json (intended violations) and fails loudly on mismatch.

Run from the task directory:  python3 gen/audit.py
Can also be pointed at any workspace: python3 gen/audit.py <workspace> <out.json>
"""
import csv
import datetime
import json
import os
import re
import sys
from decimal import Decimal, ROUND_HALF_UP

TASK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TIERS = {
    "London": 1, "Paris": 1, "New York": 1, "Zurich": 1,
    "Berlin": 2, "Madrid": 2, "Chicago": 2, "Manchester": 2,
    "Lyon": 3, "Porto": 3, "Austin": 3, "Leeds": 3,
}
MEAL_CAP = {1: Decimal("80.00"), 2: Decimal("60.00"), 3: Decimal("45.00")}
HOTEL_CAP = {1: Decimal("250.00"), 2: Decimal("180.00"), 3: Decimal("140.00")}
TAXI_CAP = Decimal("50.00")
RECEIPT_THRESHOLD = Decimal("25.00")


def parse_receipt(path):
    """Return (currency, local_amount: Decimal, nights: int)."""
    with open(path) as f:
        text = f.read()
    base = os.path.basename(path)
    kind = base.split("-")[0]
    nights = 1
    if kind == "HF":
        m = re.search(r"TOTAL CHARGED\s*:\s*([A-Z]{3})\s+([0-9.]+)", text)
        n = re.search(r"Nights\s*:\s*(\d+)", text)
        nights = int(n.group(1))
        cur, amt = m.group(1), m.group(2)
    elif kind == "TX":
        m = re.search(r"FARE\s+([0-9.]+)", text)
        c = re.search(r"CURRENCY\s+([A-Z]{3})", text)
        cur, amt = c.group(1), m.group(1)
    elif kind == "RB":
        m = re.search(r"TOTAL\s+([A-Z]{3})\s+([0-9.]+)", text)
        cur, amt = m.group(1), m.group(2)
    elif kind == "RL":
        m = re.search(r"PRICE:\s*([A-Z]{3})\s+([0-9.]+)", text)
        cur, amt = m.group(1), m.group(2)
    elif kind == "EV":
        m = re.search(r"Amount due:\s*([0-9.]+)\s+([A-Z]{3})", text)
        cur, amt = m.group(2), m.group(1)
    else:
        raise ValueError(f"unknown receipt kind: {base}")
    return cur, Decimal(amt), nights


def audit(workspace):
    with open(os.path.join(workspace, "rates.json")) as f:
        rates = {k: Decimal(str(v)) for k, v in json.load(f)["usd_per_unit"].items()}

    def to_usd(amount, currency):
        return (amount * rates[currency]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    violations = []
    with open(os.path.join(workspace, "ledger.csv")) as f:
        for row in csv.DictReader(f):
            cid = row["claim_id"]
            claimed = Decimal(row["claimed_usd"])
            cat = row["category"]
            city = row["city"]
            weekday = datetime.date.fromisoformat(row["date"]).weekday()
            tier = TIERS[city]
            rf = row["receipt_file"].strip()

            rule = None
            excess = None
            converted = None
            nights = 1
            if rf:
                cur, local, nights = parse_receipt(os.path.join(workspace, rf))
                converted = to_usd(local, cur)

            if not rf and claimed > RECEIPT_THRESHOLD:
                rule, excess = "missing-receipt", claimed - RECEIPT_THRESHOLD
            elif rf and claimed > converted:
                rule, excess = "over-claim", claimed - converted
            elif cat == "meals" and weekday >= 5 and row["travel_day_flag"] != "yes":
                rule, excess = "weekend-meal", claimed
            elif cat == "taxi" and claimed > TAXI_CAP:
                rule, excess = "taxi-over-cap", claimed - TAXI_CAP
            elif cat == "meals" and claimed > MEAL_CAP[tier]:
                rule, excess = "meal-over-cap", claimed - MEAL_CAP[tier]
            elif cat == "hotel" and claimed > HOTEL_CAP[tier] * nights:
                rule, excess = "hotel-over-cap", claimed - HOTEL_CAP[tier] * nights

            if rule:
                violations.append({
                    "claim_id": cid,
                    "rule": rule,
                    "excess_usd": float(excess.quantize(Decimal("0.01"))),
                })
    violations.sort(key=lambda v: v["claim_id"])
    return violations


def main():
    workspace = sys.argv[1] if len(sys.argv) > 1 else os.path.join(TASK, "fixture")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(TASK, "expected", "violations.json")
    violations = audit(workspace)

    planted_path = os.path.join(TASK, "gen", "planted.json")
    if os.path.exists(planted_path):
        with open(planted_path) as f:
            planted = json.load(f)
        got = {v["claim_id"]: v["rule"] for v in violations}
        assert got == planted, f"auditor/planted mismatch:\n got={got}\n want={planted}"
        assert len(violations) == 12
        assert len({v["rule"] for v in violations}) >= 5

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(violations, f, indent=2)
        f.write("\n")
    print(f"wrote {out}: {len(violations)} violations, "
          f"{len({v['rule'] for v in violations})} rule types")
    for v in violations:
        print(f"  {v['claim_id']}  {v['rule']:16s}  {v['excess_usd']:.2f}")


if __name__ == "__main__":
    main()
