#!/usr/bin/env python3
"""Deterministic fixture generator for T13-reimbursement-audit.

Writes fixture/ (ledger.csv, policy.md, rates.json, expenses/receipts/*.txt)
and gen/planted.json (intended violations, for cross-checking by audit.py).

Fixed seed. Run from the task directory:  python3 gen/make_fixture.py
"""
import json
import os
import random
import shutil
from decimal import Decimal, ROUND_HALF_UP

SEED = 20260313
TASK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(TASK, "fixture")

RATES = {"USD": "1.00", "EUR": "1.08", "GBP": "1.26"}

TIERS = {
    "London": 1, "Paris": 1, "New York": 1, "Zurich": 1,
    "Berlin": 2, "Madrid": 2, "Chicago": 2, "Manchester": 2,
    "Lyon": 3, "Porto": 3, "Austin": 3, "Leeds": 3,
}
MEAL_CAP = {1: "80.00", 2: "60.00", 3: "45.00"}
HOTEL_CAP = {1: "250.00", 2: "180.00", 3: "140.00"}
TAXI_CAP = "50.00"

EMPLOYEES = ["a.kumar", "j.smith", "m.garcia", "l.chen", "t.novak", "s.osei"]

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

HOTELS = ["Grand Meridian", "Hotel Anker", "The Elm House", "Stadthaus Krone",
          "Riverside Suites", "Pension Aurora"]
TAXI_CO = ["CITY CAB CO", "METRO TAXI", "AIRPORT LINE CARS", "BLUE STAR CABS"]
RESTAURANTS = ["The Olive Branch", "Trattoria Lume", "Kantine 44", "The Copper Pot",
               "Bistro Meridien", "Harbour & Vine"]
PLACES = ["Airport", "Central Station", "Hotel", "Client Office", "Convention Ctr",
          "Old Town", "Tech Park"]


def d2(x: str | Decimal) -> Decimal:
    return Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def to_usd(local: str, currency: str) -> Decimal:
    return (Decimal(local) * Decimal(RATES[currency])).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)


def dow(iso: str) -> int:
    """0=Mon .. 6=Sun (Zeller-free: use datetime)."""
    import datetime
    return datetime.date.fromisoformat(iso).weekday()


# ---------------------------------------------------------------------------
# Claim table.
# fields: cid, category, layout, city, date(ISO), currency, local, nights,
#         has_receipt, flag(travel_day yes/no), claimed(None => = converted),
#         planted(rule slug or None)
# layout in {HF, TX, RB, RL, EV}; None for missing-receipt rows.
C = [
    ("C001", "meals", "RB", "Paris",      "2026-03-09", "EUR", "41.20", 1, True,  "no",  None,     None),
    ("C002", "meals", "RB", "Madrid",     "2026-03-15", "EUR", "30.00", 1, True,  "yes", None,     None),
    ("C003", "meals", None, "London",     "2026-03-10", None,  None,    1, False, "no",  "42.75",  "missing-receipt"),
    ("C004", "hotel", "HF", "Berlin",     "2026-03-09", "EUR", "158.00", 1, True, "no",  None,     None),
    ("C005", "meals", "RB", "Berlin",     "2026-03-14", "EUR", "33.00", 1, True,  "no",  None,     "weekend-meal"),
    ("C006", "taxi",  "TX", "New York",   "2026-03-10", "USD", "23.40", 1, True,  "no",  None,     None),
    ("C007", "meals", "RB", "Paris",      "2026-03-12", "EUR", "52.30", 1, True,  "no",  "62.76",  "over-claim"),
    ("C008", "rail",  "RL", "London",     "2026-03-13", "GBP", "34.00", 1, True,  "no",  None,     None),
    ("C009", "taxi",  "TX", "London",     "2026-03-09", "GBP", "47.00", 1, True,  "no",  None,     "taxi-over-cap"),
    ("C010", "hotel", "HF", "New York",   "2026-03-11", "USD", "210.00", 1, True, "no",  None,     None),
    ("C011", "taxi",  None, "New York",   "2026-03-11", None,  None,    1, False, "no",  "31.00",  "missing-receipt"),
    ("C012", "meals", "RB", "Chicago",    "2026-03-12", "USD", "54.75", 1, True,  "no",  None,     None),
    ("C013", "meals", "RB", "Berlin",     "2026-03-11", "EUR", "64.00", 1, True,  "no",  None,     "meal-over-cap"),
    ("C014", "rail",  "EV", "Lyon",       "2026-03-16", "EUR", "28.90", 1, True,  "no",  None,     None),
    ("C015", "taxi",  "EV", "Madrid",     "2026-03-13", "EUR", "18.50", 1, True,  "no",  None,     None),
    ("C016", "hotel", "HF", "Lyon",       "2026-03-16", "EUR", "150.00", 1, True, "no",  None,     "hotel-over-cap"),
    ("C017", "meals", "RB", "London",     "2026-03-17", "GBP", "47.30", 1, True,  "no",  None,     None),
    ("C018", "hotel", "HF", "Zurich",     "2026-03-18", "EUR", "205.00", 1, True, "no",  None,     None),
    ("C019", "rail",  "RL", "Manchester", "2026-03-17", "GBP", "41.50", 1, True,  "no",  "70.69",  "over-claim"),
    ("C020", "taxi",  "TX", "Berlin",     "2026-03-12", "EUR", "21.75", 1, True,  "no",  None,     None),
    ("C021", "taxi",  None, "Porto",      "2026-03-18", None,  None,    1, False, "no",  "19.50",  None),
    ("C022", "meals", "RB", "Porto",      "2026-03-19", "EUR", "24.60", 1, True,  "no",  None,     None),
    ("C023", "meals", "RB", "Austin",     "2026-03-22", "USD", "27.10", 1, True,  "no",  None,     "weekend-meal"),
    ("C024", "hotel", "HF", "Manchester", "2026-03-19", "GBP", "132.00", 1, True, "no",  None,     None),
    ("C025", "taxi",  "TX", "Austin",     "2026-03-20", "USD", "50.00", 1, True,  "no",  None,     None),
    ("C026", "rail",  "RL", "Paris",      "2026-03-20", "EUR", "61.00", 1, True,  "no",  None,     None),
    ("C027", "taxi",  "TX", "Chicago",    "2026-03-18", "USD", "63.75", 1, True,  "no",  None,     "taxi-over-cap"),
    ("C028", "meals", "RB", "Leeds",      "2026-03-16", "GBP", "22.40", 1, True,  "no",  None,     None),
    ("C029", "hotel", "HF", "Porto",      "2026-03-17", "EUR", "118.00", 1, True, "no",  None,     None),
    ("C030", "hotel", "HF", "Berlin",     "2026-03-16", "EUR", "166.67", 1, True, "no",  None,     None),
    ("C031", "meals", "RB", "Zurich",     "2026-03-19", "EUR", "82.50", 1, True,  "no",  None,     "meal-over-cap"),
    ("C032", "rail",  "EV", "Leeds",      "2026-03-20", "GBP", "19.80", 1, True,  "no",  None,     None),
    ("C033", "taxi",  "TX", "Paris",      "2026-03-13", "EUR", "26.40", 1, True,  "no",  None,     None),
    ("C034", "meals", "RB", "New York",   "2026-03-21", "USD", "44.00", 1, True,  "yes", None,     None),
    ("C035", "hotel", "HF", "London",     "2026-03-17", "GBP", "420.00", 2, True, "no",  None,     "hotel-over-cap"),
    ("C036", "meals", "RB", "Manchester", "2026-03-18", "GBP", "39.90", 1, True,  "no",  None,     None),
    ("C037", "taxi",  "EV", "Zurich",     "2026-03-19", "EUR", "33.20", 1, True,  "no",  None,     None),
    ("C038", "meals", "RB", "New York",   "2026-03-16", "USD", "80.00", 1, True,  "no",  None,     None),
    ("C039", "hotel", "HF", "Chicago",    "2026-03-17", "USD", "175.00", 1, True, "no",  None,     None),
    ("C040", "rail",  "RL", "London",     "2026-03-18", "GBP", "56.00", 1, True,  "no",  None,     None),
]

# Unreferenced distractor receipts: (rid, layout, city, date, currency, local, category)
DISTRACTORS = [
    ("RB-9901", "RB", "Paris",  "2026-03-11", "EUR", "18.20", "meals"),
    ("TX-9902", "TX", "London", "2026-03-12", "GBP", "12.00", "taxi"),
    ("RL-9903", "RL", "Berlin", "2026-03-13", "EUR", "22.00", "rail"),
]


def fmt_date(iso: str, style: str) -> str:
    y, m, d = iso.split("-")
    if style == "iso":
        return iso
    if style == "ddmmyyyy":
        return f"{d}/{m}/{y}"
    if style == "mdy":
        return f"{MONTHS[int(m)-1]} {int(d)}, {y}"
    if style == "dmy":
        return f"{int(d)} {MONTHS[int(m)-1]} {y}"
    if style == "dots":
        return f"{y}.{m}.{d}"
    raise ValueError(style)


def render_receipt(rng, rid, layout, city, iso, currency, local, nights, category):
    if layout == "HF":
        hotel = rng.choice(HOTELS)
        nightly = (Decimal(local) / nights).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        import datetime
        checkout = (datetime.date.fromisoformat(iso) + datetime.timedelta(days=nights)).isoformat()
        return "\n".join([
            "=" * 34,
            f"   {hotel.upper()} — GUEST FOLIO",
            "=" * 34,
            f"Folio No   : {rid}",
            f"Guest      : (corporate account)",
            f"City       : {city}",
            f"Check-in   : {fmt_date(iso, 'iso')}",
            f"Check-out  : {checkout}",
            f"Nights     : {nights}",
            f"Room rate  : {nightly} {currency} per night",
            "-" * 34,
            f"TOTAL CHARGED : {currency} {local}",
            "Payment: corporate card",
            "",
        ])
    if layout == "TX":
        co = rng.choice(TAXI_CO)
        a, b = rng.sample(PLACES, 2)
        return "\n".join([
            f"*** {co} ***",
            "RECEIPT",
            f"Ref  : {rid}",
            f"Date : {fmt_date(iso, 'ddmmyyyy')}",
            f"City : {city}",
            f"Pickup : {a}",
            f"Dropoff: {b}",
            f"FARE {local}",
            f"CURRENCY {currency}",
            "Thank you for riding",
            "",
        ])
    if layout == "RB":
        name = rng.choice(RESTAURANTS)
        service = (Decimal(local) * Decimal("0.09")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        food = Decimal(local) - service
        return "\n".join([
            name,
            f"{city} — table {rng.randint(2, 14)}",
            f"Receipt #{rid}",
            f"Date: {fmt_date(iso, 'mdy')}",
            "-" * 28,
            " Covers: 1",
            f" Food          {food}",
            f" Service chg   {service}",
            "-" * 28,
            f" TOTAL {currency} {local}",
            "",
        ])
    if layout == "RL":
        a, b = rng.sample(PLACES, 2)
        return "\n".join([
            "NATIONAL RAIL / E-TICKET",
            f"Ticket: {rid}",
            f"Travel date: {fmt_date(iso, 'dmy')}",
            f"From: {a}   To: {b}",
            f"City of issue: {city}",
            f"Class: Standard  Coach {rng.choice('BCDE')} Seat {rng.randint(1, 60)}",
            f"PRICE: {currency} {local}",
            "Ticket conditions apply.",
            "",
        ])
    if layout == "EV":
        return "\n".join([
            "GENERIC EXPENSE VOUCHER",
            "-" * 30,
            f"Voucher ID: {rid}",
            f"Issued: {fmt_date(iso, 'dots')}",
            f"Location: {city}",
            f"Description: ground transport / misc ({category})",
            f"Amount due: {local} {currency}",
            "Approved by: ops-desk",
            "",
        ])
    raise ValueError(layout)


def main():
    rng = random.Random(SEED)
    if os.path.isdir(FIX):
        shutil.rmtree(FIX)
    os.makedirs(os.path.join(FIX, "expenses", "receipts"))

    # rates.json
    with open(os.path.join(FIX, "rates.json"), "w") as f:
        json.dump({"usd_per_unit": {k: float(v) for k, v in RATES.items()}}, f, indent=2)
        f.write("\n")

    # receipts + ledger
    id_counters = {"HF": 1040, "TX": 2200, "RB": 3300, "RL": 4400, "EV": 7300}
    ledger_rows = []
    planted = {}
    for i, (cid, cat, layout, city, iso, cur, local, nights, has_rcpt, flag,
            claimed_override, rule) in enumerate(C):
        emp = EMPLOYEES[i % len(EMPLOYEES)]
        if has_rcpt:
            id_counters[layout] += rng.randint(1, 9)
            rid = f"{layout}-{id_counters[layout]}"
            fname = f"expenses/receipts/{rid}.txt"
            text = render_receipt(rng, rid, layout, city, iso, cur, local, nights, cat)
            with open(os.path.join(FIX, fname), "w") as f:
                f.write(text)
            converted = to_usd(local, cur)
            claimed = Decimal(claimed_override) if claimed_override else converted
        else:
            fname = ""
            claimed = Decimal(claimed_override)
        ledger_rows.append(
            f"{cid},{fname},{emp},{city},{iso},{cat},{claimed},{flag}")
        if rule:
            planted[cid] = rule

    # distractor receipts
    for rid, layout, city, iso, cur, local, cat in DISTRACTORS:
        text = render_receipt(rng, rid, layout, city, iso, cur, local, 1, cat)
        with open(os.path.join(FIX, f"expenses/receipts/{rid}.txt"), "w") as f:
            f.write(text)

    with open(os.path.join(FIX, "ledger.csv"), "w") as f:
        f.write("claim_id,receipt_file,employee,city,date,category,claimed_usd,travel_day_flag\n")
        f.write("\n".join(ledger_rows) + "\n")

    # policy.md
    policy = f"""# Corporate Travel Reimbursement Policy (rev. 2026-02)

All claims in `ledger.csv` are submitted in USD (`claimed_usd`). Receipts are
issued in local currency (USD, EUR, or GBP).

## 1. Currency conversion

Convert receipt totals to USD using the fixed rates in `rates.json`
(`usd_per_unit`: USD 1.00, EUR 1.08, GBP 1.26):

    usd = local_amount * usd_per_unit[currency]

Round to 2 decimal places using ROUND HALF-UP **at conversion time** (i.e.
round the product once, immediately; all later comparisons use the rounded
value). Example: EUR 52.30 -> 52.30 * 1.08 = 56.484 -> **56.48 USD**.

## 2. City tiers

| Tier | Cities |
|------|--------|
| 1 | London, Paris, New York, Zurich |
| 2 | Berlin, Madrid, Chicago, Manchester |
| 3 | Lyon, Porto, Austin, Leeds |

## 3. Caps (all USD, compared against `claimed_usd`)

- **Meals per-diem cap** (per claim/day): Tier 1: 80.00, Tier 2: 60.00, Tier 3: 45.00.
- **Hotel nightly cap**: Tier 1: 250.00, Tier 2: 180.00, Tier 3: 140.00.
  A hotel claim covers the whole stay; the effective cap is `nightly_cap * nights`
  where `nights` is taken from the hotel folio.
- **Taxi cap**: 50.00 per trip (all tiers).
- Amounts **equal to** a cap are compliant; only amounts strictly greater are
  violations.
- Rail travel has no cap.

## 4. Receipts

A receipt is required for any claim with `claimed_usd` strictly greater than
25.00 USD. A claim's `receipt_file` column is empty when no receipt was
submitted. Claims of 25.00 or less need no receipt.

## 5. Weekend meals

Meal claims dated (ledger `date`, ISO) on a Saturday or Sunday are not
reimbursable **unless** the ledger `travel_day_flag` for that claim is `yes`.

## 6. Over-claiming

`claimed_usd` may not exceed the receipt total converted to USD per section 1.
"""
    with open(os.path.join(FIX, "policy.md"), "w") as f:
        f.write(policy)

    with open(os.path.join(TASK, "gen", "planted.json"), "w") as f:
        json.dump(planted, f, indent=2, sort_keys=True)
        f.write("\n")

    # sanity: planted weekend rows really are weekends; OK meal rows are not
    for (cid, cat, layout, city, iso, cur, local, nights, has_rcpt, flag,
         claimed_override, rule) in C:
        if rule == "weekend-meal":
            assert dow(iso) >= 5, (cid, iso)
        if cat == "meals" and rule is None and flag == "no" and has_rcpt:
            assert dow(iso) < 5, (cid, iso)
    n_receipts = len([p for p in os.listdir(os.path.join(FIX, "expenses/receipts"))])
    assert n_receipts == 40, n_receipts
    assert len(planted) == 12, planted
    assert len(set(planted.values())) >= 5
    print(f"fixture written: 40 claims, {n_receipts} receipts, "
          f"{len(planted)} planted violations, {len(set(planted.values()))} rule types")


if __name__ == "__main__":
    main()
