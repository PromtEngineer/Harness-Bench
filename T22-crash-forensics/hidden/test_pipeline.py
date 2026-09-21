"""Hidden unit tests for T22 (run with PYTHONPATH=<workspace>)."""
from orderflow.batch import BATCH, batches
from orderflow.models import LineItem
from orderflow.parse import parse_order
from orderflow.pricing import discount_pct, line_total_cents


def test_parse_missing_coupon_is_none():
    o = parse_order('{"order_id": "X1", "region": "north", '
                    '"items": [{"sku": "A", "qty": 1, "price_cents": 100}]}')
    assert o.coupon is None


def test_parse_with_coupon():
    o = parse_order('{"order_id": "X2", "region": "south", "coupon": "HALF", '
                    '"items": [{"sku": "A", "qty": 2, "price_cents": 250}]}')
    assert o.coupon == "HALF"
    assert o.items[0].qty == 2


def test_unknown_coupon_no_discount():
    assert discount_pct("BOGUS") == 0
    assert discount_pct(None) == 0
    assert discount_pct("SAVE25") == 25


def test_half_up_boundary():
    # 2 * 101 * 75 = 15150 -> 151.50 -> rounds UP to 152
    assert line_total_cents(LineItem("A", 2, 101), 25) == 152
    # 1 * 101 * 50 = 5050 -> 50.50 -> 51
    assert line_total_cents(LineItem("A", 1, 101), 50) == 51
    # plain truncation case stays: 1 * 100 * 90 = 9000 -> 90
    assert line_total_cents(LineItem("A", 1, 100), 10) == 90


def test_line_total_is_int():
    v = line_total_cents(LineItem("A", 3, 333), 10)
    assert isinstance(v, int) and not isinstance(v, bool)
    assert v == 899  # 3*333*90 = 89910 -> 899.10 -> 899


def test_batches_exact_multiple():
    seq = list(range(2 * BATCH))
    bs = batches(seq)
    assert [x for b in bs for x in b] == seq
    assert all(len(b) <= BATCH for b in bs)


def test_batches_partial_tail():
    seq = list(range(2 * BATCH + 7))
    bs = batches(seq)
    assert [x for b in bs for x in b] == seq
    assert len(bs[-1]) == 7


def test_batches_small():
    assert [x for b in batches([1, 2, 3]) for x in b] == [1, 2, 3]
    assert batches([]) == []
