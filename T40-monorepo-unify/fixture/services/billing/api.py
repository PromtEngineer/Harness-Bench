"""Billing service API."""
from .utils import dates, ids, money


def invoice_total_cents(lines):
    """lines: [(qty, unit_price_float_cents)]. Rounded per line."""
    return sum(money.round_cents(qty * price) for qty, price in lines)


def invoice_id(n):
    return ids.make_id("INV", n)


def format_total(cents, currency="USD"):
    return money.format_money(cents, currency)


def due_date(invoice_date_str, net_days):
    d = dates.parse_date(invoice_date_str)
    return dates.format_date(dates.add_business_days(d, net_days))
