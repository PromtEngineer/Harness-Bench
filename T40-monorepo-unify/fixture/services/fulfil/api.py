"""Fulfilment service API."""
from .utils import dates, ids, retry


def package_id(n):
    return ids.make_id("PKG", n)


def eta(ship_date_str, transit_days):
    d = dates.parse_date(ship_date_str)
    return dates.format_date(dates.add_business_days(d, transit_days))


def carrier_retry_plan():
    return retry.retry_plan()


def is_valid_package(ref):
    return ids.verify_id(ref)
