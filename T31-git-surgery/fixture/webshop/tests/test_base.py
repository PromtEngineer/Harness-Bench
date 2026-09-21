import cart
import format as fmt
import pricing


def test_unit_price():
    assert pricing.unit_price(199, 3) == 597


def test_cart_total_shape():
    sub, t, tot = cart.cart_total([(1000, 2), (500, 1)])
    assert sub == 2500
    assert tot == sub + t


def test_format():
    assert fmt.cents_to_str(12345) == "123.45"
    assert fmt.cents_to_str(7) == "0.07"
