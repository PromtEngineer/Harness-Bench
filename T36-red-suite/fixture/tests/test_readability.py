from textstat.readability import reading_ease


def test_known_score_simple():
    # 4 words, 2 sentences, syllables: the=1 cat=1 sat=1 down=1 -> 4
    assert reading_ease("The cat sat down.", 2) == 120.21


def test_fractional_ratio():
    # 3 words, 2 sentences: the words/sentences ratio 1.5 must NOT truncate
    assert reading_ease("Go far now.", 2) == 120.71


def test_syllable_ratio_fractional():
    # words: over=2 the=1 mountains=2 -> 5 syllables over 3 words
    assert reading_ease("over the mountains", 1) == 62.79


def test_returns_float_type():
    assert isinstance(reading_ease("plain words here", 1), float)


def test_empty_text():
    assert reading_ease("", 1) == 0.0


def test_zero_sentences():
    assert reading_ease("some words", 0) == 0.0
