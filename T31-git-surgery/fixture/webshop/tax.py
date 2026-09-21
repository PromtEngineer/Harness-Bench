"""Sales tax. Rates in basis points (1/100 of a percent)."""

DEFAULT_RATE_BP = 875  # 8.75%


def tax_cents(subtotal_cents, rate_bp=DEFAULT_RATE_BP):
    """Tax on a subtotal, rounded half up."""
    num = subtotal_cents * rate_bp
    q, r = divmod(num, 10000)
    return q + (1 if r * 2 >= 10000 else 0)
