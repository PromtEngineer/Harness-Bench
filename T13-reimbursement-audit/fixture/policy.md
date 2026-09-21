# Corporate Travel Reimbursement Policy (rev. 2026-02)

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
