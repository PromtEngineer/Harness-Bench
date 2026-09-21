from pricer.cart import cart_total_cents


def test_cart_no_tax():
    # (250,4): no tier; (200,10): 5% off 2000 -> 1900; (120,50): 10% off 6000 -> 5400
    assert cart_total_cents([(250, 4), (200, 10), (120, 50)]) == 1000 + 1900 + 5400


def test_cart_with_tax():
    # subtotal 8300; 8.75% tax -> 726.25 -> 726
    assert cart_total_cents([(250, 4), (200, 10), (120, 50)], tax_rate_bp=875) == 8300 + 726
