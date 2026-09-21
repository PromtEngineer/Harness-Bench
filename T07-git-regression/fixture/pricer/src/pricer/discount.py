"""Quantity-based bulk discounts.

Tier table:
    quantity >= 100  -> 15% off
    quantity >=  50  -> 10% off
    quantity >=  10  ->  5% off
    otherwise        ->  no discount
"""


def discount_pct(quantity: int) -> int:
    """Discount percentage for a given quantity (see tier table above)."""
    if quantity >= 100:
        return 15
    if quantity >= 50:
        return 10
    if quantity >= 10:
        return 5
    return 0


def bulk_total_cents(unit_cents: int, quantity: int) -> int:
    """Discounted total in cents."""
    gross = unit_cents * quantity
    pct = discount_pct(quantity)
    return gross * (100 - pct) // 100
