#!/usr/bin/env python3
"""Independent schedule validator. argv: <jobs.json> <schedule.json>"""
import json
import sys

def makespan(jobs, start):
    return max(start[j["id"]] + j["duration"] for j in jobs)


def validate(jobs, caps, start, budget):
    """Independent validator. Returns None if OK else an error string."""
    by_id = {j["id"]: j for j in jobs}
    if set(start) != set(by_id):
        return "schedule must assign a start to every job, exactly"
    for jid, s in start.items():
        if not isinstance(s, int) or isinstance(s, bool) or s < 0:
            return f"{jid}: start must be a non-negative integer"
    for j in jobs:
        for d in j["deps"]:
            if start[j["id"]] < start[d] + by_id[d]["duration"]:
                return (f"{j['id']} starts at {start[j['id']]} before dep "
                        f"{d} finishes at {start[d] + by_id[d]['duration']}")
    events = {}
    for j in jobs:
        s = start[j["id"]]
        events.setdefault(s, [0, 0])
        events.setdefault(s + j["duration"], [0, 0])
        events[s][0] += j["cpu"]
        events[s][1] += j["mem"]
        events[s + j["duration"]][0] -= j["cpu"]
        events[s + j["duration"]][1] -= j["mem"]
    cpu = mem = 0
    for t in sorted(events):
        cpu += events[t][0]
        mem += events[t][1]
        if cpu > caps["cpu"]:
            return f"cpu cap exceeded at tick {t}: {cpu} > {caps['cpu']}"
        if mem > caps["mem"]:
            return f"mem cap exceeded at tick {t}: {mem} > {caps['mem']}"
    ms = makespan(jobs, start)
    if ms > budget:
        return f"makespan {ms} exceeds budget {budget}"
    return None


doc = json.load(open(sys.argv[1]))
sched = json.load(open(sys.argv[2]))
if not isinstance(sched, dict) or "start" not in sched:
    print("VALIDATE FAIL: schedule.json must be {\"start\": {job: tick}}")
    sys.exit(1)
err = validate(doc["jobs"], doc["resources"], sched["start"],
               doc["makespan_budget"])
if err:
    print(f"VALIDATE FAIL: {err}")
    sys.exit(1)
ms = makespan(doc["jobs"], sched["start"])
print(f"VALIDATE OK: makespan {ms} <= budget {doc['makespan_budget']}")
