from statlib import cache


def test_parse_line():
    assert cache.parse_line(" 2.5 \n") == 2.5
    assert cache.parse_line("\n") is None


def test_cached_summary():
    out = cache.cached_summary([1.5, 2.5, 6.0])
    assert out == {"count": 3, "total": 10.0, "mean": 10.0 / 3}
