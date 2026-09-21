from pricer.tax import sales_tax_cents, total_tax_cents

import pytest


def test_sales_tax_rounds_half_up():
    assert sales_tax_cents(10000, 875) == 875
    assert sales_tax_cents(999, 875) == 87   # 87.41 -> 87
    assert sales_tax_cents(1000, 850) == 85


def test_sales_tax_rejects_negative_rate():
    with pytest.raises(ValueError):
        sales_tax_cents(100, -1)


def test_total_tax_multiple_rates():
    assert total_tax_cents(10000, [500, 250]) == 500 + 250
    assert total_tax_cents(10000, []) == 0
