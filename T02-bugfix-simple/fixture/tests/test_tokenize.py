from textstats.tokenize import sentences, tokenize


def test_tokenize_lowercases():
    assert tokenize("Hello WORLD") == ["hello", "world"]


def test_tokenize_strips_punctuation():
    assert tokenize("well, well... done!") == ["well", "well", "done"]


def test_tokenize_keeps_apostrophes():
    assert tokenize("don't stop") == ["don't", "stop"]


def test_sentences_split():
    assert sentences("One. Two! Three?") == ["One", "Two", "Three"]
