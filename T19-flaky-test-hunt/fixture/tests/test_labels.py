from statlib import labels


def test_unique_labels_sorted():
    data = [
        "zebra", "  Alpha", "mango", "alpha", "Kiwi ", "zebra", "banana",
        "Quince", "fig", "date", "Nectarine", "ugli", "cherry", "papaya",
        "elder", "banana",
    ]
    assert labels.unique_labels(data) == [
        "alpha", "banana", "cherry", "date", "elder", "fig", "kiwi",
        "mango", "nectarine", "papaya", "quince", "ugli", "zebra",
    ]


def test_label_histogram():
    assert labels.label_histogram(["b", "A", "b", " a "]) == {"a": 2, "b": 2}


def test_normalize():
    assert labels.normalize("  MiXeD Case ") == "mixed case"
