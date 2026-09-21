"""Date helpers."""
from datetime import date, timedelta

DATE_FMT = "%Y-%m-%d"


def parse_date(s):
    y, m, d = s.split("-")
    return date(int(y), int(m), int(d))


def format_date(d):
    return f"{d.year:04d}-{d.month:02d}-{d.day:02d}"


def add_business_days(d, n):
    """Skip Saturdays and Sundays."""
    step = 1 if n >= 0 else -1
    remaining = abs(n)
    while remaining:
        d += timedelta(days=step)
        if d.weekday() < 5:
            remaining -= 1
    return d
