"""Hidden tests: canonical behaviors per DECISIONS.md."""
from datetime import date

from corelib import dates, ids, money, retry
from services.billing import api as billing
from services.fulfil import api as fulfil
from services.notify import api as notify


# D2: half-up rounding everywhere, notify's symbol table everywhere
def test_round_cents_half_up():
    assert money.round_cents(0.5) == 1
    assert money.round_cents(1.5) == 2      # bankers would say 2 too...
    assert money.round_cents(2.5) == 3      # ...but not here (bankers: 2)
    assert money.round_cents(-0.5) == -1
    assert money.round_cents(2.4) == 2
    assert money.ROUND_MODE == "half_up"


def test_symbols_are_notifys():
    assert money.SYMBOLS["EUR"] == "\u20ac"
    assert money.SYMBOLS["JPY"] == "\u00a5"
    assert money.format_money(150, "EUR") == "\u20ac1.50"


def test_billing_gets_half_up_via_api():
    # 3 * 100.5 -> three lines of 301.5?? no: one line qty 3 price 100.5
    # = 301.5 -> 302 with half-up, 301 with truncate, 302 bankers;
    # 1 * 102.5 -> 103 half-up vs 102 bankers: separates all variants
    assert billing.invoice_total_cents([(1, 102.5)]) == 103
    assert billing.invoice_total_cents([(1, 101.5), (1, 102.5)]) == 205


def test_notify_formats_with_rich_symbols_and_half_up_totals():
    assert notify.amount_line(99, "GBP") == "Amount due: \u00a30.99"
    assert notify.amount_line(-1250, "JPY") == "Amount due: -\u00a512.50"


# D3: day-first dates for every service, including billing (changed!)
def test_dates_are_day_first():
    assert dates.DATE_FMT == "%d/%m/%Y"
    assert dates.format_date(date(2026, 8, 6)) == "06/08/2026"
    assert dates.parse_date("31/12/2026") == date(2026, 12, 31)


def test_billing_due_date_format_changed():
    assert billing.due_date("07/08/2026", 1) == "10/08/2026"


def test_fulfil_eta_unchanged():
    assert fulfil.eta("07/08/2026", 3) == "12/08/2026"


def test_notify_send_window():
    assert notify.send_window("06/08/2026", 2) == "10/08/2026"


# D4: checksum mod 97 for every service
def test_checksum_mod_97():
    assert ids.CHECK_MOD == 97
    body = "INV000123"
    total = sum((i + 1) * ord(ch) for i, ch in enumerate(body))
    assert billing.invoice_id(123) == f"{body}-{total % 97:02d}"


def test_all_services_agree_on_checksum():
    b = billing.invoice_id(500)[-2:]
    f = fulfil.package_id(500)[-2:]
    n = notify.digest_id(500)[-2:]
    bodies = ["INV000500", "PKG000500", "DIG000500"]
    for got, body in zip((b, f, n), bodies):
        total = sum((i + 1) * ord(ch) for i, ch in enumerate(body))
        assert got == f"{total % 97:02d}"


def test_cross_service_verify():
    # a billing id must verify with fulfil's checker (same corelib now)
    assert fulfil.is_valid_package(billing.invoice_id(42))


# D5: backoff base 1.5 for every service
def test_backoff_curve():
    assert retry.BACKOFF_BASE == 1.5
    assert retry.backoff_ms(2) == 150
    assert retry.backoff_ms(3) == 225
    assert fulfil.carrier_retry_plan() == [0, 150, 225, 337, 506]
    assert notify.webhook_backoff() == [0, 150, 225, 337, 506]
