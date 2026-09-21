"""Cart-level totals built on discounts and tax."""

from .discount import bulk_total_cents
from .tax import sales_tax_cents


def cart_total_cents(lines, tax_rate_bp: int = 0) -> int:
    """Total for (unit_cents, quantity) lines: bulk pricing plus tax."""
    subtotal = sum(bulk_total_cents(unit, qty) for (unit, qty) in lines)
    return subtotal + sales_tax_cents(subtotal, tax_rate_bp)
