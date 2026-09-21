"""Base pricing rules. All money in integer cents."""


def round_price(cents_float):
    """Round to whole cents, half up (contract: 250.5 -> 251)."""
    whole = int(cents_float)
    frac = cents_float - whole
    return whole + 1 if frac >= 0.5 else whole


def unit_price(base_cents, qty):
    """Price for qty units, no discounts."""
    return base_cents * qty
