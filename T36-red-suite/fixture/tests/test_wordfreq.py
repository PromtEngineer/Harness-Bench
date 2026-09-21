from textstat.wordfreq import count_freq, top_n


def test_casefolded():
    assert count_freq(["The", "the", "THE"]) == {"the": 3}


def test_fresh_result_each_call():
    assert count_freq(["alpha"]) == {"alpha": 1}
    assert count_freq(["beta"]) == {"beta": 1}


def test_isolated_counts():
    first = count_freq(["x", "y"])
    second = count_freq(["z"])
    assert second == {"z": 1}
    assert first == {"x": 1, "y": 1}


def test_top_n_basic():
    toks = ["a", "b", "a", "c", "b", "a"]
    assert top_n(toks, 2) == [("a", 3), ("b", 2)]


def test_top_n_tie_alphabetical():
    assert top_n(["b", "a"], 2) == [("a", 1), ("b", 1)]


def test_top_n_does_not_leak_between_calls():
    assert top_n(["m"], 1) == [("m", 1)]
    assert top_n(["n"], 1) == [("n", 1)]


def test_empty_tokens():
    assert count_freq([]) == {}


def test_counts_values():
    got = count_freq(["dog", "cat", "dog"])
    assert got == {"dog": 2, "cat": 1}
