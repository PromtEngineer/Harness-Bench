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
    for _eid, _user, tags in events:
        for t in tags:
            tag_totals[t] += 1
    n = len(events)
    for i in range(n):
        user_i = events[i][1]
        tags_i = events[i][2]
        for j in range(i + 1, n):
            if events[j][1] != user_i:
                continue
            for a in tags_i:
                for b in events[j][2]:
                    if a == b:
                        continue
                    if a < b:
                        pair_counts[(a, b)] += 1
                    else:
                        pair_counts[(b, a)] += 1
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
