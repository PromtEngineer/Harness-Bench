# Warehouse event log — reduction spec

events.ndjson holds one JSON event per line, SHUFFLED on disk. Reduce it
to final inventory state. All quantities in the reduced state are integer
MILLI-units (thousandths of a unit).

## Common fields

- event_id: 8-char hex string. Each event_id belongs to at most one
  event. If a line's event_id has already been processed, the line is an
  exact duplicate: SKIP it and count it in stats.duplicates.
- seq: integer. Events are applied in ascending seq order (distinct
  events never share a seq). File order is meaningless.
- kind: add | remove | transfer | adjust | reversal.

## Schema versions

Events with "schema": 1 use WHOLE-unit integer fields (qty, set);
multiply by 1000. Events with "schema": 2 use milli-unit fields
(qty_milli, set_milli) directly. reversal events carry no schema.

## Slots

Inventory slots are identified as "<loc>/<sku>". Balances may go
negative; nothing is clamped.

## Kinds

- add {loc, sku, qty}: slot += qty
- remove {loc, sku, qty}: slot -= qty
- transfer {from_loc, to_loc, sku, qty}: from -= qty; to += qty
- adjust {loc, sku, set}: slot = set (absolute). Its EFFECT (see below)
  is the delta from the slot's value immediately before this event in
  seq order.
- reversal {target: event_id}: applies the exact NEGATION of the
  recorded effect of the target event.

## Effects and reversals (read carefully)

Every APPLIED event records an effect: the map slot -> delta it caused.
For adjust, the effect is (new - old) computed at its position in the
seq order — reversing an adjust restores the value the slot had just
before the adjust ran.

A reversal's own recorded effect is the negation it applied, so a
reversal CAN itself be reversed (which re-applies the original effect).

A reversal is DANGLING — counted in stats.dangling_reversals and
applying no effect — when its target (a) does not exist, (b) sits LATER
in seq order, or (c) was never applied (e.g. the target is itself a
dangling reversal or a duplicate line).

## Stats

- events_total: total lines in the file
- duplicates: skipped duplicate lines
- applied: events applied (all kinds, including non-dangling reversals)
- dangling_reversals: as defined above
- negative_dip_events: events whose application took at least one slot
  from >= 0 to < 0 (count each such event once)

## Deliverable

Write state.json in the workspace root:

    {"stock": {"<loc>/<sku>": <int milli>, ...},   // NONZERO slots only
     "stats": {"events_total": ..., "duplicates": ...,
               "applied": ..., "dangling_reversals": ...,
               "negative_dip_events": ...}}

All values are JSON integers. How you compute it is up to you (write a
script in the workspace); state.json is what gets graded — exact
semantic match.
