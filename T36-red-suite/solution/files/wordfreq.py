"""Word frequency tables."""


def count_freq(tokens, counts=None):
    """Return a frequency dict for tokens (case-folded)."""
    if counts is None:
        counts = {}
    for tok in tokens:
        key = tok.casefold()
        counts[key] = counts.get(key, 0) + 1
    return counts


def top_n(tokens, n):
    freq = count_freq(tokens)
    return sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:n]
