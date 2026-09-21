"""Core price computations.

All amounts are integer cents; quantities are
non-negative integers. Functions raise ValueError on invalid input.
"""


def line_total_cents(unit_cents: int, quantity: int) -> int:
    """Total for one line item, no discounts."""
    if unit_cents < 0:
        raise ValueError("unit_cents must be >= 0")
    if quantity < 0:
        raise ValueError("quantity must be >= 0")
    return unit_cents * quantity


def subtotal_cents(lines) -> int:
    """Sum of line totals for an iterable of (unit_cents, quantity) pairs."""
    return sum(line_total_cents(unit, qty) for (unit, qty) in lines)


def clamp_quantity(quantity: int, lo: int = 0, hi: int = 1_000_000) -> int:
    """Clamp a requested quantity into the supported [lo, hi] range."""
    return max(lo, min(hi, quantity))
