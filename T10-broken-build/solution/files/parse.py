"""Parsing helpers: strict ISO dates and compact duration strings."""

import re
from datetime import date, timedelta

_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_DUR_RE = re.compile(r"^(?:\d+[dhms])+$")
_DUR_TOKEN = re.compile(r"(\d+)([dhms])")

_UNIT_SECONDS = {"d": 86400, "h": 3600, "m": 60, "s": 1}


def parse_date(text):
    """Parse a strict ISO-8601 calendar date 'YYYY-MM-DD' into datetime.date."""
    m = _DATE_RE.match(text)
    if not m:
        raise ValueError(f"invalid date: {text!r} (expected YYYY-MM-DD)")
    year, month, day = (int(g) for g in m.groups())
    return date(year, month, day)


def parse_duration(text):
    """Parse a compact duration like '1h30m' or '2d4h5s' into a timedelta.

    Allowed units: d (days), h (hours), m (minutes), s (seconds).
    """
    if not isinstance(text, str) or not _DUR_RE.match(text):
        raise ValueError(f"invalid duration: {text!r}")
    total = 0
    for value, unit in _DUR_TOKEN.findall(text):
        total += int(value) * _UNIT_SECONDS[unit]
    return timedelta(seconds=total)


def describe(delta):
    """Human-readable description of a timedelta, e.g. 'duration 1h30m'."""
    # Imported lazily to avoid a circular import with chronolib.format.
    from chronolib.format import format_duration

    return "duration " + format_duration(delta)
