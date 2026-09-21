"""Label handling helpers.

API contract: functions returning collections of labels return them in
deterministic sorted order.
"""


def normalize(label):
    """Lowercase a label and strip surrounding whitespace."""
    return label.strip().lower()


def unique_labels(labels):
    """Return the distinct normalized labels as a sorted list."""
    seen = set()
    for label in labels:
        seen.add(normalize(label))
    return [label for label in seen]


def label_histogram(labels):
    """Return {normalized label: occurrences} with keys in sorted order."""
    hist = {}
    for label in labels:
        key = normalize(label)
        hist[key] = hist.get(key, 0) + 1
    return {key: hist[key] for key in sorted(hist)}
