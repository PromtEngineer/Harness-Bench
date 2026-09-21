from pricer.discount import bulk_total_cents, discount_pct


def test_tiers():
    assert discount_pct(1) == 0
    assert discount_pct(9) == 0
    assert discount_pct(10) == 5
    assert discount_pct(50) == 10
    assert discount_pct(100) == 15


def test_no_discount_small_qty():
    assert bulk_total_cents(500, 3) == 1500


def test_bulk_rounds_half_up():
    # 333 * 10 = 3330 gross; 5% off -> 3163.5 cents -> rounds up to 3164
    assert bulk_total_cents(333, 10) == 3164


def test_bulk_fifty_exact():
    # 999 * 50 = 49950 gross; 10% off -> 44955 exactly (no rounding needed)
    assert bulk_total_cents(999, 50) == 44955


def test_bulk_hundred_rounding():
    # 101 * 101 = 10201 gross; 15% off -> 8670.85 -> rounds up to 8671
    assert bulk_total_cents(101, 101) == 8671
