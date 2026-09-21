from textstat.ngrams import bigram_counts
from textstat.readability import reading_ease
from textstat.syllables import estimate
from textstat.tokenize import words
from textstat.wordfreq import count_freq


def test_syllables_basic():
    assert estimate("cat") == 1
    assert estimate("window") == 2
    assert estimate("readability") == 5


def test_syllables_vowel_groups():
    assert estimate("queue") == 1
    assert estimate("rhythm") == 1


def test_pipeline_tokens_to_freq():
    toks = words("Red fish, blue fish.")
    assert count_freq(toks) == {"red": 1, "fish": 2, "blue": 1}


def test_pipeline_bigrams_of_tokens():
    toks = words("to be or not to be")
    counts = bigram_counts(toks)
    assert counts[("to", "be")] == 2
    assert sum(counts.values()) == len(toks) - 1


def test_pipeline_hyphen_freq():
    toks = words("The well-known well-known trick")
    freq = count_freq(toks)
    assert freq["well-known"] == 2


def test_readability_is_stable():
    a = reading_ease("Some simple words appear here.", 1)
    b = reading_ease("Some simple words appear here.", 1)
    assert a == b


def test_syllables_empty():
    assert estimate("") == 0


def test_freq_of_empty_text():
    assert count_freq(words("")) == {}
