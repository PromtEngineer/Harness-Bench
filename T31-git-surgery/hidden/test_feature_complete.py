"""Hidden tests run on the `fixed` branch checkout."""
import cart
import format as fmt
import pricing
import pricing_v2
import tax


# regressions must be GONE
def test_rounding_contract_restored():
    assert pricing.round_price(250.5) == 251
    assert pricing.round_price(0.5) == 1


def test_tax_contract_restored():
    assert tax.tax_cents(1149) == 101
    assert tax.tax_cents(1143) == 100


# every good feature commit's behavior must be PRESENT
def test_f1_tiers():
    assert pricing_v2.tiered_discount_bp(9) == 0
    assert pricing_v2.tiered_discount_bp(10) == 500
    assert pricing_v2.tiered_discount_bp(25) == 1000
    assert pricing_v2.tiered_discount_bp(100) == 1500


def test_f2_cart_uses_tiers():
    # 10 units @ 100c = 1000c gross, 5% tier -> 50c off -> 950
    assert cart.line_price(100, 10) == 950
    # tier discount rounding goes through round_price (half up):
    # 25 * 101c = 2525 gross, 10% -> 252.5 -> 253 off -> 2272
    assert cart.line_price(101, 25) == 2272


def test_f4_coupons():
    assert pricing_v2.coupon_bp("WELCOME5") == 500
    assert pricing_v2.coupon_bp("VIP15") == 1500
    assert pricing_v2.coupon_bp("NOPE") == 0


def test_f6_bulk():
    assert pricing_v2.bulk_unit_cents(100, 500) == 80
    assert pricing_v2.bulk_unit_cents(100, 499) == 100


def test_f8_currency_format():
    assert fmt.format_currency(123456789) == "$1,234,567.89"
    assert fmt.format_currency(50, "€") == "€0.50"


def test_cart_end_to_end():
    sub, t, tot = cart.cart_total([(100, 10), (200, 1)])
    assert sub == 950 + 200
    assert t == tax.tax_cents(1150)
    assert tot == sub + t
