from textstat.ngrams import bigram_counts, bigrams


def test_bigram_basic():
    assert bigrams(["a", "b", "c"]) == [("a", "b"), ("b", "c")]


def test_bigram_length_contract():
    toks = ["w1", "w2", "w3", "w4", "w5"]
    assert len(bigrams(toks)) == len(toks) - 1


def test_bigram_includes_last_pair():
    assert ("d", "e") in bigrams(["a", "b", "c", "d", "e"])


def test_bigram_pair():
    assert bigrams(["x", "y"]) == [("x", "y")]


def test_bigram_single():
    assert bigrams(["solo"]) == []


def test_bigram_empty():
    assert bigrams([]) == []


def test_bigram_counts():
    got = bigram_counts(["a", "b", "a", "b"])
    assert got == {("a", "b"): 2, ("b", "a"): 1}


def test_bigram_counts_repeats():
    got = bigram_counts(["x", "x", "x"])
    assert got == {("x", "x"): 2}
