"""Pricing rules. See README.md for the authoritative rounding contract."""

COUPONS = {"SAVE10": 10, "SAVE25": 25, "HALF": 50}


def discount_pct(coupon):
    """Percentage discount for a coupon code (unknown or missing -> 0)."""
    if coupon is None:
        return 0
    return COUPONS.get(coupon, 0)


def line_total_cents(item, pct):
    """Discounted total for one line item, in integer cents (round half up)."""
    num = item.qty * item.price_cents * (100 - pct)
    q, r = divmod(num, 100)
    return q + (1 if r * 2 >= 100 else 0)


def order_totals(order):
    """Return (gross_cents, net_cents) for an order."""
    pct = discount_pct(order.coupon)
    gross = sum(i.qty * i.price_cents for i in order.items)
    net = sum(line_total_cents(i, pct) for i in order.items)
    return gross, net
