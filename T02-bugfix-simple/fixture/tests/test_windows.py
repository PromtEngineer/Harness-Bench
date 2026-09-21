from textstats.windows import sliding_windows


def test_window_count():
    # 5 elements, window size 2 -> 4 windows
    assert len(sliding_windows([1, 2, 3, 4, 5], 2)) == 4


def test_full_length_window():
    # A window exactly as long as the sequence is a valid (single) window.
    assert sliding_windows(["a", "b", "c"], 3) == [("a", "b", "c")]


def test_last_window_contents():
    assert sliding_windows([1, 2, 3, 4], 2)[-1] == (3, 4)


def test_too_short_returns_empty():
    assert sliding_windows([1, 2], 5) == []


def test_step_skips_offsets():
    assert sliding_windows(list(range(8)), 3, step=2) == [
        (0, 1, 2),
        (2, 3, 4),
        (4, 5, 6),
    ]
