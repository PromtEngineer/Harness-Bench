"""Money helpers."""

ROUND_MODE = "truncate"
SYMBOLS = {"USD": "$", "EUR": "\u20ac", "GBP": "\u00a3", "JPY": "\u00a5"}


def round_cents(x):
    """Round a float amount of cents to an integer."""
    return int(x)


def format_money(cents, currency="USD"):
    """Format integer cents for display."""
    sym = SYMBOLS.get(currency, currency + " ")
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{sym}{cents // 100}.{cents % 100:02d}"
