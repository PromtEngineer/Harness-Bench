from datetime import date, timedelta

import pytest

import chronolib
from chronolib import (
    describe,
    format_date,
    format_duration,
    normalize_duration,
    parse_date,
    parse_duration,
)


def test_version():
    assert chronolib.__version__ == "0.3.0"


def test_parse_date():
    assert parse_date("2024-03-05") == date(2024, 3, 5)


def test_parse_date_rejects_bad_format():
    with pytest.raises(ValueError):
        parse_date("2024/03/05")
    with pytest.raises(ValueError):
        parse_date("05-03-2024")


def test_parse_duration_simple():
    assert parse_duration("1h30m") == timedelta(hours=1, minutes=30)


def test_parse_duration_full():
    assert parse_duration("2d4h5s") == timedelta(days=2, hours=4, seconds=5)


def test_parse_duration_rejects_garbage():
    with pytest.raises(ValueError):
        parse_duration("h30m")
    with pytest.raises(ValueError):
        parse_duration("90 minutes")


def test_format_date():
    assert format_date(date(2023, 12, 1)) == "2023-12-01"


def test_format_duration():
    assert format_duration(timedelta(hours=1, minutes=30)) == "1h30m"
    assert format_duration(timedelta(0)) == "0s"
    assert format_duration(timedelta(days=1, seconds=61)) == "1d1m1s"


def test_normalize_duration_roundtrip():
    assert normalize_duration("90m") == "1h30m"
    assert normalize_duration("3600s") == "1h"


def test_describe():
    assert describe(timedelta(minutes=90)) == "duration 1h30m"
