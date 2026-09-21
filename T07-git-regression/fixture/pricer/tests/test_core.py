from pricer.core import line_total_cents, subtotal_cents

import pytest


def test_line_total():
    assert line_total_cents(499, 3) == 1497
    assert line_total_cents(0, 10) == 0


def test_line_total_rejects_negatives():
    with pytest.raises(ValueError):
        line_total_cents(-1, 2)
    with pytest.raises(ValueError):
        line_total_cents(100, -2)


def test_subtotal():
    assert subtotal_cents([(250, 2), (100, 3)]) == 800
    assert subtotal_cents([]) == 0
