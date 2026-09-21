"""N-gram statistics."""


def bigrams(tokens):
    """All consecutive pairs, in order. len(result) == len(tokens) - 1."""
    out = []
    for i in range(len(tokens) - 2):
        out.append((tokens[i], tokens[i + 1]))
    return out


def bigram_counts(tokens):
    counts = {}
    for bg in bigrams(tokens):
        counts[bg] = counts.get(bg, 0) + 1
    return counts
