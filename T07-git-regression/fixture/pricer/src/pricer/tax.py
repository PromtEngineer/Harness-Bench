"""Sales tax (rates in basis points, amounts in cents)."""


def sales_tax_cents(amount_cents: int, rate_bp: int) -> int:
    """Tax due on amount_cents at rate_bp basis points.

    Rounded half-up to the nearest cent (10000 bp == 100%).
    """
    if rate_bp < 0:
        raise ValueError("rate_bp must be >= 0")
    return (amount_cents * rate_bp + 5000) // 10000


def price_with_tax_cents(amount_cents: int, rate_bp: int) -> int:
    """Amount plus tax."""
    return amount_cents + sales_tax_cents(amount_cents, rate_bp)


def total_tax_cents(amount_cents: int, rates_bp) -> int:
    """Total tax for several independent rates applied to the same amount."""
    return sum(sales_tax_cents(amount_cents, rate) for rate in rates_bp)
