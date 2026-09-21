#!/usr/bin/env python3
"""Reference reducer for the warehouse event log (see SPEC.md)."""
import json

def reduce_events(lines):
    """Reference reducer. Returns the state dict per SPEC.md."""
    events = []
    seen_ids = set()
    duplicates = 0
    for line in lines:
        if not line.strip():
            continue
        e = json.loads(line)
        events.append(e)

    events_total = len(events)
    # order by seq; ids are unique among non-duplicates (spec guarantees it)
    ordered = sorted(events, key=lambda e: (e["seq"], e["event_id"]))

    stock = {}                # "loc/sku" -> qty_milli
    effects = {}              # event_id -> {slot: delta} for APPLIED events
    applied = 0
    dangling = 0
    dips = 0

    def qty_of(e, field_v2, field_v1):
        if e.get("schema") == 1:
            return int(e[field_v1]) * 1000
        return int(e[field_v2])

    for e in ordered:
        eid = e["event_id"]
        if eid in seen_ids:
            duplicates += 1
            continue
        seen_ids.add(eid)
        kind = e["kind"]
        effect = {}
        if kind == "add":
            effect[f"{e['loc']}/{e['sku']}"] = qty_of(e, "qty_milli", "qty")
        elif kind == "remove":
            effect[f"{e['loc']}/{e['sku']}"] = -qty_of(e, "qty_milli", "qty")
        elif kind == "transfer":
            q = qty_of(e, "qty_milli", "qty")
            src = f"{e['from_loc']}/{e['sku']}"
            dst = f"{e['to_loc']}/{e['sku']}"
            effect[src] = effect.get(src, 0) - q
            effect[dst] = effect.get(dst, 0) + q
        elif kind == "adjust":
            slot = f"{e['loc']}/{e['sku']}"
            target_val = qty_of(e, "set_milli", "set")
            effect[slot] = target_val - stock.get(slot, 0)
        elif kind == "reversal":
            tgt = e["target"]
            if tgt not in effects:
                dangling += 1
                continue
            effect = {slot: -d for slot, d in effects[tgt].items()}
        else:
            raise ValueError(f"unknown kind {kind!r}")

        dipped = False
        for slot, delta in effect.items():
            old = stock.get(slot, 0)
            new = old + delta
            stock[slot] = new
            if old >= 0 and new < 0:
                dipped = True
        if dipped:
            dips += 1
        effects[eid] = effect
        applied += 1

    return {
        "stock": {k: v for k, v in sorted(stock.items()) if v != 0},
        "stats": {
            "events_total": events_total,
            "duplicates": duplicates,
            "applied": applied,
            "dangling_reversals": dangling,
            "negative_dip_events": dips,
        },
    }

state = reduce_events(open("events.ndjson").read().splitlines())
with open("state.json", "w") as fh:
    json.dump(state, fh, indent=2, sort_keys=True)
    fh.write("\n")
print("state.json written")
