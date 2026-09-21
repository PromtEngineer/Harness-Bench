"""Anti-overfit tests: same root causes, fresh inputs."""
from textstat.ngrams import bigram_counts, bigrams
from textstat.readability import reading_ease
from textstat.tokenize import words
from textstat.wordfreq import count_freq, top_n


def test_tokenize_fresh_hyphens():
    assert words("six-and-a-half meters") == ["six-and-a-half", "meters"]
    assert words("rock'n'roll lives") == ["rock'n'roll", "lives"]


def test_tokenize_hyphen_not_glue_across_space():
    assert words("pre- and post-war") == ["pre", "and", "post-war"]


def test_bigrams_fresh():
    assert bigrams(["p", "q", "r", "s"]) == [("p", "q"), ("q", "r"),
                                             ("r", "s")]
    assert len(bigrams(list("abcdefgh"))) == 7


def test_bigram_counts_fresh():
    assert bigram_counts(["u", "v", "u", "v", "u"]) == {
        ("u", "v"): 2, ("v", "u"): 2}


def test_readability_fresh():
    # 5 words, 2 sentences; one vowel group per word
    assert reading_ease("Big dogs run past red.", 2) == 119.7


def test_readability_fresh_fractional_syllables():
    # tokens: purple=2 haze=2 -> 4 syllables over 2 words
    assert reading_ease("purple haze", 1) == 35.61


def test_wordfreq_fresh_isolation():
    count_freq(["seed"])
    assert count_freq(["only"]) == {"only": 1}
    assert top_n(["k"], 3) == [("k", 1)]
    assert top_n(["j", "j"], 3) == [("j", 2)]


def test_wordfreq_explicit_dict_still_works():
    d = {}
    count_freq(["a"], d)
    count_freq(["a", "b"], d)
    assert d == {"a": 2, "b": 1}
