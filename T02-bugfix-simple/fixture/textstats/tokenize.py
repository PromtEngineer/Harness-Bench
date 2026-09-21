"""Tokenization helpers for textstats."""
import re

_WORD_RE = re.compile(r"[A-Za-z0-9']+")


def tokenize(text):
    """Return lowercase word tokens in order of appearance.

    A token is a maximal run of letters, digits, or apostrophes.
    """
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]


def sentences(text):
    """Split text into non-empty, stripped sentence strings on ., ! or ?."""
    parts = re.split(r"[.!?]+", text)
    return [p.strip() for p in parts if p.strip()]
