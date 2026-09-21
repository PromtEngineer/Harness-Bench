"""Date helpers."""
from datetime import date, timedelta

DATE_FMT = "%d/%m/%Y"


def parse_date(s):
    d, m, y = s.split("/")
    return date(int(y), int(m), int(d))


def format_date(d):
    return f"{d.day:02d}/{d.month:02d}/{d.year:04d}"


def add_business_days(d, n):
    """Skip Saturdays and Sundays."""
    step = 1 if n >= 0 else -1
    remaining = abs(n)
    while remaining:
        d += timedelta(days=step)
        if d.weekday() < 5:
            remaining -= 1
    return d
