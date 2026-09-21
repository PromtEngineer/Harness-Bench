import tax


def test_tax_half_up():
    # 1143 * 875bp = 100.0125 -> 100 ; 1149*875 = 100.5375 -> 101
    assert tax.tax_cents(1143) == 100
    assert tax.tax_cents(1149) == 101


def test_tax_zero():
    assert tax.tax_cents(0) == 0
