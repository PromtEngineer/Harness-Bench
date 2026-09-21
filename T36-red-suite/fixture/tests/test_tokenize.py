from textstat.tokenize import words


def test_simple_split():
    assert words("the quick fox") == ["the", "quick", "fox"]


def test_punctuation_split():
    assert words("stop. go, now!") == ["stop", "go", "now"]


def test_case_preserved():
    assert words("Hello World") == ["Hello", "World"]


def test_hyphenated_single_token():
    assert words("a well-known trick") == ["a", "well-known", "trick"]


def test_contraction_single_token():
    assert words("don't stop") == ["don't", "stop"]


def test_double_hyphen_chain():
    assert words("state-of-the-art stuff") == ["state-of-the-art", "stuff"]


def test_leading_trailing_symbols():
    assert words("--dashes-- 'quotes'") == ["dashes", "quotes"]


def test_numbers_ignored():
    assert words("route 66 rocks") == ["route", "rocks"]


def test_empty():
    assert words("") == []


def test_only_symbols():
    assert words("!!! ---") == []
