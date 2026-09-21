#!/usr/bin/env python3
"""Critical-path list scheduler. Usage: scheduler.py <jobs.json> <out.json>"""
import json
import sys

def critical_path_priority(jobs):
    by_id = {j["id"]: j for j in jobs}
    children = {j["id"]: [] for j in jobs}
    for j in jobs:
        for d in j["deps"]:
            children[d].append(j["id"])
    prio = {}

    def longest(jid):
        if jid in prio:
            return prio[jid]
        prio[jid] = by_id[jid]["duration"] + max(
            (longest(c) for c in children[jid]), default=0)
        return prio[jid]

    for j in jobs:
        longest(j["id"])
    return prio


def list_schedule(jobs, caps, priority=None):
    """Event-driven list scheduling. Returns {job_id: start_tick}."""
    by_id = {j["id"]: j for j in jobs}
    prio = priority or critical_path_priority(jobs)
    remaining_deps = {j["id"]: set(j["deps"]) for j in jobs}
    ready = sorted([jid for jid, deps in remaining_deps.items() if not deps],
                   key=lambda jid: (-prio[jid], jid))
    running = []  # (end, id)
    start = {}
    t = 0
    used = {"cpu": 0, "mem": 0}
    while len(start) < len(jobs):
        # start every ready job that fits, in priority order
        progressed = True
        while progressed:
            progressed = False
            for jid in list(ready):
                j = by_id[jid]
                if used["cpu"] + j["cpu"] <= caps["cpu"] and \
                   used["mem"] + j["mem"] <= caps["mem"]:
                    ready.remove(jid)
                    start[jid] = t
                    used["cpu"] += j["cpu"]
                    used["mem"] += j["mem"]
                    running.append((t + j["duration"], jid))
                    progressed = True
        if len(start) == len(jobs):
            break
        if not running:
            raise RuntimeError("stuck: nothing running, nothing startable")
        running.sort()
        t = running[0][0]
        finished = [jid for end, jid in running if end <= t]
        running = [(end, jid) for end, jid in running if end > t]
        for jid in finished:
            j = by_id[jid]
            used["cpu"] -= j["cpu"]
            used["mem"] -= j["mem"]
            for c in [x["id"] for x in jobs if jid in x["deps"]]:
                remaining_deps[c].discard(jid)
                if not remaining_deps[c] and c not in start and c not in ready:
                    ready.append(c)
        ready.sort(key=lambda jid: (-prio[jid], jid))
    return start


def main():
    doc = json.load(open(sys.argv[1]))
    start = list_schedule(doc["jobs"], doc["resources"])
    with open(sys.argv[2], "w") as fh:
        json.dump({"start": start}, fh, indent=2, sort_keys=True)
        fh.write("\n")
    ms = max(start[j["id"]] + j["duration"] for j in doc["jobs"])
    print(f"makespan {ms} (budget {doc['makespan_budget']})")


if __name__ == "__main__":
    main()
