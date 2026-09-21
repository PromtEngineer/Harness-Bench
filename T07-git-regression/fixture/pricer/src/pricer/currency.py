"""Currency formatting helpers."""


def format_cents(cents: int) -> str:
    """Format cents as dollars; negative amounts get a leading minus."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return "%s$%d.%02d" % (sign, cents // 100, cents % 100)


def parse_cents(text: str) -> int:
    """Parse "$12.34" / "-$0.50" / "7" style strings into integer cents."""
    t = text.strip().replace("$", "")
    sign = -1 if t.startswith("-") else 1
    t = t.lstrip("+-")
    if "." in t:
        dollars, _, frac = t.partition(".")
        frac = (frac + "00")[:2]
    else:
        dollars, frac = t, "00"
    return sign * (int(dollars or 0) * 100 + int(frac))
