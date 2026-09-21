"""Flesch-style reading ease.

score = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
computed in REAL arithmetic, then rounded to 2 decimals.
"""
from .syllables import estimate
from .tokenize import words as tokenize_words


def reading_ease(text, sentences):
    toks = tokenize_words(text)
    if not toks or sentences <= 0:
        return 0.0
    syl = sum(estimate(w) for w in toks)
    score = 206.835 - 1.015 * (len(toks) / sentences) \
        - 84.6 * (syl / len(toks))
    return round(score, 2)
