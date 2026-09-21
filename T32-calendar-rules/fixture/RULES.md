# Recurrence rules and zone semantics

## Zones (ZONES.json)

Each zone has base_offset_min (minutes east of UTC; may be negative or
non-hour like +345) and an optional dst block:

- delta_min: minutes added to the base offset while DST is active.
- start: DST begins at `local_time` WALL CLOCK IN STANDARD TIME on the
  Nth weekday of the month (ordinal "1".."4" or "last"). At that wall
  time, clocks jump forward by delta_min.
- end: DST ends at `local_time` WALL CLOCK IN DST on its day; clocks
  fall back by delta_min.

DST is active from the start instant (inclusive) to the end instant
(exclusive), both well-defined in UTC. Assume start month < end month
(northern-style) and that rule days never collide.

### Local -> UTC policies (graded exactly)

- Spring-forward gap (local times that never happen): map to the FIRST
  VALID INSTANT, i.e. the transition instant itself.
- Fall-back overlap (local times that happen twice): use the EARLIER
  instant (the DST one).

## Rule syntax

    every day <HH:MM> @<Zone>                 daily
    every <wd> <HH:MM> @<Zone>                weekly   (mon..sun)
    every <1st|2nd|3rd|4th|last> <wd> <HH:MM> @<Zone>  monthly by weekday
    every day <D> <HH:MM> @<Zone>             monthly by day number 1..31
                                              (months without day D skip)

## CLI contract

    python3 sched.py "<rule>" <start_utc_iso> <count>

start_utc_iso looks like 2026-03-19T00:00:00Z. Print exactly <count>
lines: the first <count> occurrences STRICTLY AFTER the start instant,
as UTC in the format YYYY-MM-DDTHH:MM:SSZ, in chronological order.

## Worked examples (verify your implementation against ALL of these)

    $ python3 sched.py "every day 02:30 @Meridian" 2026-03-19T00:00:00Z 3
    2026-03-19T00:30:00Z
    2026-03-20T00:00:00Z      <- 02:30 falls in the 02:00->03:00 gap
    2026-03-20T23:30:00Z

    $ python3 sched.py "every day 02:30 @Meridian" 2026-11-06T00:00:00Z 3
    2026-11-06T23:30:00Z
    2026-11-07T23:30:00Z      <- ambiguous 02:30 -> earlier (DST) instant
    2026-11-09T00:30:00Z

    $ python3 sched.py "every mon 09:15 @Umbra" 2026-08-05T00:00:00Z 2
    2026-08-10T03:30:00Z      <- +05:45 zone, no DST
    2026-08-17T03:30:00Z

    $ python3 sched.py "every day 12:15 @Polaris" 2026-05-08T00:00:00Z 3
    2026-05-08T12:15:00Z
    2026-05-09T12:00:00Z      <- 30-minute DST gap 12:00->12:30
    2026-05-10T11:45:00Z
