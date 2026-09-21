from textstats.metrics import bigram_counts, max_window_sum, mean


def test_mean():
    assert mean([2, 4, 6]) == 4


def test_max_window_sum_includes_final_window():
    # windows of size 2: (1,2)=3, (2,3)=5, (3,9)=12
    assert max_window_sum([1, 2, 3, 9], 2) == 12


def test_bigram_counts():
    counts = bigram_counts(["a", "b", "a", "b"])
    assert counts[("a", "b")] == 2
    assert counts[("b", "a")] == 1
