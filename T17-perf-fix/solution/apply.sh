#!/usr/bin/env bash
# Reference solution for T17-perf-fix. cwd = workspace copy.
# Replaces the O(n^2) all-pairs scan in report.py with an O(total tags)
# per-user counting scheme. Identical semantics, identical serialization.
set -euo pipefail

cat > report.py <<'PYEOF'
#!/usr/bin/env python3
"""Tag co-occurrence report over events.csv.

Counting semantics (fixed -- any optimization must preserve these exactly):

- events.csv columns: event_id, user, tags (pipe-separated; tags are unique
  within a single event).
- Two events "co-occur" when they belong to the same user.
- For every unordered pair of distinct events (i, j) of the same user, every
  tag a of event i and tag b of event j with a != b contributes exactly 1 to
  the co-occurrence count of the unordered tag pair (min(a, b), max(a, b)).
- tag_totals[t] = number of events whose tag list contains t.

Output (output.json):
- "pairs": the top 20 tag pairs, sorted by count descending, ties broken by
  the pair's first tag ascending, then second tag ascending. Each entry is
  {"count": <int>, "tags": [<first>, <second>]} with first < second.
- "tag_totals": {tag: total} for every tag that appears in events.csv.
- Serialized with json.dumps(result, indent=2, sort_keys=True) plus a
  trailing newline.

Fast implementation notes:
For one user, the number of (event_i, event_j, i != j, ordered) pairs with
tag a in event i and tag b in event j equals C_a * C_b - B_ab, where C_t is
the number of that user's events containing tag t and B_ab is the number of
that user's events containing both a and b. Summing the naive loop's two
directions over unordered event pairs gives exactly that ordered-pair count,
so per-user tallies reproduce the quadratic scan's numbers exactly.
"""
import csv
import json
from collections import defaultdict


def load_events(path):
    events = []
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            tags = row["tags"].split("|") if row["tags"] else []
            events.append((row["event_id"], row["user"], tags))
    return events


def compute(events):
    pair_counts = defaultdict(int)
    tag_totals = defaultdict(int)
    per_user_counts = defaultdict(lambda: defaultdict(int))
    per_user_both = defaultdict(lambda: defaultdict(int))
    for _eid, user, tags in events:
        counts = per_user_counts[user]
        both = per_user_both[user]
        for t in tags:
            tag_totals[t] += 1
            counts[t] += 1
        for x in range(len(tags)):
            a = tags[x]
            for y in range(x + 1, len(tags)):
                b = tags[y]
                key = (a, b) if a < b else (b, a)
                both[key] += 1
    for user, counts in per_user_counts.items():
        both = per_user_both[user]
        tags_sorted = sorted(counts)
        m = len(tags_sorted)
        for x in range(m):
            a = tags_sorted[x]
            ca = counts[a]
            for y in range(x + 1, m):
                b = tags_sorted[y]
                v = ca * counts[b] - both.get((a, b), 0)
                if v:
                    pair_counts[(a, b)] += v
    return pair_counts, tag_totals


def render(pair_counts, tag_totals):
    ranked = sorted(pair_counts.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1]))
    top = [{"count": c, "tags": [a, b]} for (a, b), c in ranked[:20]]
    return {"pairs": top, "tag_totals": dict(sorted(tag_totals.items()))}


def main():
    events = load_events("events.csv")
    pair_counts, tag_totals = compute(events)
    result = render(pair_counts, tag_totals)
    with open("output.json", "w") as fh:
        fh.write(json.dumps(result, indent=2, sort_keys=True))
        fh.write("\n")


if __name__ == "__main__":
    main()
PYEOF

echo "T17 reference solution applied (report.py rewritten with O(n) algorithm)"
