"""Batching for the settlement step. Every order must be processed
exactly once (README.md, "Settlement")."""

BATCH = 50


def batches(seq):
    """Split seq into consecutive batches of at most BATCH items."""
    out = []
    for i in range(0, len(seq), BATCH):
        out.append(seq[i:i + BATCH])
    return out
