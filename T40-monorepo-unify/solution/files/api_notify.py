"""Notification service API."""
from corelib import dates, ids, money, retry


def amount_line(cents, currency):
    return f"Amount due: {money.format_money(cents, currency)}"


def digest_id(n):
    return ids.make_id("DIG", n)


def send_window(date_str, business_days_ahead):
    d = dates.parse_date(date_str)
    return dates.format_date(dates.add_business_days(d, business_days_ahead))


def webhook_backoff():
    return retry.retry_plan()
