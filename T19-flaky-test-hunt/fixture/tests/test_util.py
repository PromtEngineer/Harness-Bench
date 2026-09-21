import pytest

from statlib import util


def test_mean():
    assert util.mean([1.0, 2.0, 3.0, 6.0]) == 3.0
    with pytest.raises(ValueError):
        util.mean([])


def test_median():
    assert util.median([9, 1, 5]) == 5
    assert util.median([4.0, 1.0, 3.0, 2.0]) == 2.5


def test_clamp():
    assert util.clamp(5, 0, 3) == 3
    assert util.clamp(-2, 0, 3) == 0
    assert util.clamp(2, 0, 3) == 2
    with pytest.raises(ValueError):
        util.clamp(1, 3, 0)


def test_rolling_sum():
    assert util.rolling_sum([1, 2, 3, 4], 2) == [3.0, 5.0, 7.0]
    assert util.rolling_sum([1, 2], 3) == []
