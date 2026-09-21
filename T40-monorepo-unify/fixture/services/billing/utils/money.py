"""Money helpers."""

ROUND_MODE = "half_up"
SYMBOLS = {"USD": "$", "EUR": "EUR ", "GBP": "GBP "}


def round_cents(x):
    """Round a float amount of cents to an integer."""
    whole = int(x)
    frac = x - whole
    if frac >= 0.5:
        return whole + 1
    if frac <= -0.5:
        return whole - 1
    return whole


def format_money(cents, currency="USD"):
    """Format integer cents for display."""
    sym = SYMBOLS.get(currency, currency + " ")
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{sym}{cents // 100}.{cents % 100:02d}"
