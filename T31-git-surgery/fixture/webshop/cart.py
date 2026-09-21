"""Shopping cart totaling."""
import pricing
import tax


def cart_total(items, rate_bp=tax.DEFAULT_RATE_BP):
    """items: list of (base_cents, qty). Returns (subtotal, tax, total)."""
    subtotal = 0
    for base_cents, qty in items:
        subtotal += pricing.unit_price(base_cents, qty)
    t = tax.tax_cents(subtotal, rate_bp)
    return subtotal, t, subtotal + t
