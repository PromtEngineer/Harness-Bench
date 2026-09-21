"""Formatting helpers: ISO dates and compact duration strings."""

from datetime import date, timedelta

from chronolib.parse import parse_duration


def format_date(value):
    """Format a datetime.date as 'YYYY-MM-DD'."""
    if not isinstance(value, date):
        raise TypeError("format_date expects datetime.date")
    return value.isoformat()


def format_duration(delta):
    """Format a timedelta as a compact duration like '1h30m'.

    Zero components are omitted; a zero duration formats as '0s'.
    Negative durations are not supported.
    """
    if not isinstance(delta, timedelta):
        raise TypeError("format_duration expects datetime.timedelta")
    total = int(delta.total_seconds())
    if total < 0:
        raise ValueError("negative durations are not supported")
    if total == 0:
        return "0s"
    parts = []
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        amount, total = divmod(total, size)
        if amount:
            parts.append(f"{amount}{unit}")
    return "".join(parts)


def normalize_duration(text):
    """Canonicalize a duration string, e.g. '90m' -> '1h30m'."""
    return format_duration(parse_duration(text))
