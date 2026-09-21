# orderflow settlement pipeline

Processes the nightly order feed (data/orders.ndjson) into report.json.
Run: `python3 replay.py`

## Feed contract

One JSON object per line. Required fields: order_id, region, items
(list of {sku, qty, price_cents}). Optional field: coupon — a coupon
code string. Orders without a coupon get no discount. Unknown coupon
codes also mean no discount (marketing reuses retired codes; ignore them).

## Pricing (authoritative)

All money is integer cents. For each line item:

    line_net = round_half_up(qty * price_cents * (100 - discount_pct) / 100)

round_half_up: an exact .5 remainder rounds UP (away from zero; all
amounts here are non-negative). Compute in integers — floating point
must not appear anywhere in pricing. gross ignores discounts;
discount_cents = gross - net.

## Settlement

Orders are settled in batches of at most 50. EVERY order in the feed
must be settled exactly once — the report's totals cover the entire
feed. Partial trailing batches are settled like any other batch.

## Report

report.json: {"orders", "gross_cents", "discount_cents", "net_cents",
"by_region": {region: {"orders", "net_cents"}}} — regions sorted,
JSON with sort_keys, indent=2, trailing newline.
