"""Invariant behaviors — these pass before and after the unification."""
from services.billing import api as billing
from services.fulfil import api as fulfil
from services.notify import api as notify


def test_billing_whole_amounts():
    # whole-cent lines are rounding-mode independent
    assert billing.invoice_total_cents([(2, 500.0), (1, 250.0)]) == 1250


def test_billing_id_shape():
    ref = billing.invoice_id(123)
    assert ref.startswith("INV000123-") and len(ref.split("-")[1]) == 2


def test_fulfil_id_roundtrip():
    assert fulfil.is_valid_package(fulfil.package_id(7))
    assert not fulfil.is_valid_package("PKG000007-99")


def test_notify_amount_contains_value():
    line = notify.amount_line(123456, "USD")
    assert "1234.56" in line and line.startswith("Amount due: ")


def test_retry_plans_start_at_zero():
    assert fulfil.carrier_retry_plan()[0] == 0
    assert notify.webhook_backoff()[0] == 0


def test_business_day_math():
    # Friday 07/08/2026 + 1 business day = Monday 10/08/2026
    assert fulfil.eta("07/08/2026", 1) == "10/08/2026"
