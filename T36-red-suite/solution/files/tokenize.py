"""Word tokenization.

Contract: a word is a maximal run of letters, where hyphens and
apostrophes BETWEEN letters keep the word together: "well-known" and
"don't" are single tokens. Case is preserved.
"""
import re

_WORD = re.compile(r"[A-Za-z]+(?:['-][A-Za-z]+)*")


def words(text):
    return _WORD.findall(text)
