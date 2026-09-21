import pricing


def test_half_up():
    assert pricing.round_price(250.5) == 251
    assert pricing.round_price(250.4999) == 250
    assert pricing.round_price(99.5) == 100


def test_whole():
    assert pricing.round_price(100.0) == 100
