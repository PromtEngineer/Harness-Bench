"""Money helpers."""

ROUND_MODE = "bankers"
SYMBOLS = {"USD": "$", "EUR": "EUR ", "GBP": "GBP "}


def round_cents(x):
    """Round a float amount of cents to an integer."""
    return int(round(x))


def format_money(cents, currency="USD"):
    """Format integer cents for display."""
    sym = SYMBOLS.get(currency, currency + " ")
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{sym}{cents // 100}.{cents % 100:02d}"
