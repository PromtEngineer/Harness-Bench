#!/usr/bin/env python3
"""Reference solution for T13-reimbursement-audit. cwd = workspace."""
import csv
import datetime
import json
import os
import re
from decimal import Decimal, ROUND_HALF_UP

TIERS = {
    "London": 1, "Paris": 1, "New York": 1, "Zurich": 1,
    "Berlin": 2, "Madrid": 2, "Chicago": 2, "Manchester": 2,
    "Lyon": 3, "Porto": 3, "Austin": 3, "Leeds": 3,
}
MEAL_CAP = {1: Decimal("80.00"), 2: Decimal("60.00"), 3: Decimal("45.00")}
HOTEL_CAP = {1: Decimal("250.00"), 2: Decimal("180.00"), 3: Decimal("140.00")}
TAXI_CAP = Decimal("50.00")
THRESHOLD = Decimal("25.00")


def parse_receipt(path):
    text = open(path).read()
    kind = os.path.basename(path).split("-")[0]
    nights = 1
    if kind == "HF":
        m = re.search(r"TOTAL CHARGED\s*:\s*([A-Z]{3})\s+([0-9.]+)", text)
        nights = int(re.search(r"Nights\s*:\s*(\d+)", text).group(1))
        cur, amt = m.group(1), m.group(2)
    elif kind == "TX":
        amt = re.search(r"FARE\s+([0-9.]+)", text).group(1)
        cur = re.search(r"CURRENCY\s+([A-Z]{3})", text).group(1)
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
        raise ValueError(path)
    return cur, Decimal(amt), nights


rates = {k: Decimal(str(v))
         for k, v in json.load(open("rates.json"))["usd_per_unit"].items()}


def to_usd(amount, currency):
    return (amount * rates[currency]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


violations = []
for row in csv.DictReader(open("ledger.csv")):
    claimed = Decimal(row["claimed_usd"])
    cat, city = row["category"], row["city"]
    weekday = datetime.date.fromisoformat(row["date"]).weekday()
    rf = row["receipt_file"].strip()
    converted, nights = None, 1
    if rf:
        cur, local, nights = parse_receipt(rf)
        converted = to_usd(local, cur)

    rule = excess = None
    if not rf and claimed > THRESHOLD:
        rule, excess = "missing-receipt", claimed - THRESHOLD
    elif rf and claimed > converted:
        rule, excess = "over-claim", claimed - converted
    elif cat == "meals" and weekday >= 5 and row["travel_day_flag"] != "yes":
        rule, excess = "weekend-meal", claimed
    elif cat == "taxi" and claimed > TAXI_CAP:
        rule, excess = "taxi-over-cap", claimed - TAXI_CAP
    elif cat == "meals" and claimed > MEAL_CAP[TIERS[city]]:
        rule, excess = "meal-over-cap", claimed - MEAL_CAP[TIERS[city]]
    elif cat == "hotel" and claimed > HOTEL_CAP[TIERS[city]] * nights:
        rule, excess = "hotel-over-cap", claimed - HOTEL_CAP[TIERS[city]] * nights

    if rule:
        violations.append({"claim_id": row["claim_id"], "rule": rule,
                           "excess_usd": float(excess)})

violations.sort(key=lambda v: v["claim_id"])
with open("violations.json", "w") as f:
    json.dump(violations, f, indent=2)
    f.write("\n")
print(f"wrote violations.json with {len(violations)} entries")
