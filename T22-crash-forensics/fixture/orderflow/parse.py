"""Parse the raw order feed (NDJSON, one order per line)."""
import json

from .models import LineItem, Order


def parse_order(line):
    """Parse one NDJSON line into an Order.

    Field notes: order_id, region and items are required; see README.md
    for the full feed contract.
    """
    o = json.loads(line)
    items = [
        LineItem(sku=i["sku"], qty=int(i["qty"]), price_cents=int(i["price_cents"]))
        for i in o["items"]
    ]
    coupon = o["coupon"]
    return Order(order_id=o["order_id"], region=o["region"],
                 coupon=coupon, items=items)
