from pricer.currency import format_cents, parse_cents


def test_format_cents():
    assert format_cents(1234) == "$12.34"
    assert format_cents(5) == "$0.05"
    assert format_cents(0) == "$0.00"


def test_format_negative():
    assert format_cents(-50) == "-$0.50"
    assert format_cents(-1234) == "-$12.34"


def test_parse_cents():
    assert parse_cents("$12.34") == 1234
    assert parse_cents("-$0.50") == -50
    assert parse_cents("7") == 700
    assert parse_cents("3.5") == 350
