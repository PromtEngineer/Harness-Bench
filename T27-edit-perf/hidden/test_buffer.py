"""Hidden Buffer semantics tests (PYTHONPATH = workspace)."""
from edbuf import Buffer


def test_insert_bounds():
    b = Buffer("hello")
    b.insert(0, "A")
    b.insert(6, "Z")
    b.insert(999, "!")       # clamped to end
    b.insert(-4, "<")        # clamped to start
    assert b.get_slice(0, 100) == "<AhelloZ!"


def test_delete_bounds():
    b = Buffer("abcdefgh")
    b.delete(6, 99)          # clamps n
    assert b.get_slice(0, 99) == "abcdef"
    b.delete(-3, 2)          # pos clamps to 0
    assert b.get_slice(0, 99) == "cdef"
    b.delete(99, 5)          # no-op
    assert b.get_slice(0, 99) == "cdef"
    b.delete(0, 0)
    assert b.get_slice(0, 99) == "cdef"


def test_slice_bounds():
    b = Buffer("0123456789")
    assert b.get_slice(4, 3) == "456"
    assert b.get_slice(8, 99) == "89"
    assert b.get_slice(-2, 3) == "012"
    assert b.get_slice(99, 5) == ""
    assert b.get_slice(3, 0) == ""


def test_interleaved():
    b = Buffer("")
    for i in range(200):
        b.insert(i, str(i % 10))
    assert b.get_slice(0, 5) == "01234"
    b.delete(0, 100)
    b.insert(50, "XYZ")
    got = b.get_slice(48, 7)
    assert got == "89XYZ01", got


def test_empty_start():
    b = Buffer()
    assert b.get_slice(0, 10) == ""
    b.insert(5, "abc")       # clamped to 0
    assert b.get_slice(0, 10) == "abc"
