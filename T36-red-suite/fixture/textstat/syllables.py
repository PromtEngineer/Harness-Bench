"""Syllable estimation (correct; used by readability)."""


def estimate(word):
    """Count vowel groups; minimum 1 for any non-empty word."""
    w = word.lower()
    groups = 0
    prev_vowel = False
    for ch in w:
        is_vowel = ch in "aeiouy"
        if is_vowel and not prev_vowel:
            groups += 1
        prev_vowel = is_vowel
    return max(1, groups) if w else 0
