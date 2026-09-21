"""Aggregate metrics built on top of tokenize and windows."""
from collections import Counter

from .windows import sliding_windows


def mean(values):
    """Arithmetic mean of a non-empty sequence of numbers."""
    values = list(values)
    if not values:
        raise ValueError("mean of empty sequence")
    return sum(values) / len(values)


def vocabulary_size(tokens):
    """Number of distinct tokens."""
    return len(set(tokens))


def max_window_sum(values, size):
    """Largest sum over any window of `size` consecutive values."""
    wins = sliding_windows(list(values), size)
    if not wins:
        raise ValueError("sequence shorter than window size")
    return max(sum(w) for w in wins)


def bigram_counts(tokens):
    """Counter mapping each adjacent token pair (bigram) to its count."""
    return Counter(sliding_windows(list(tokens), 2))
