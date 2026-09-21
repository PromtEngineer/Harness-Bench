#!/usr/bin/env python3
"""Recurrence scheduler over the fictional zones in ZONES.json.

Usage: python3 sched.py "<rule>" <start_utc_iso> <count>
"""
import calendar
import json
import sys
from datetime import date, datetime, timedelta

WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5,
            "sun": 6}


def nth_weekday(year, month, weekday, ordinal):
    """Date of the Nth <weekday> of a month; ordinal '1'..'4' or 'last'."""
    if ordinal == "last":
        d = date(year, month, calendar.monthrange(year, month)[1])
        while d.weekday() != weekday:
            d -= timedelta(days=1)
        return d
    d = date(year, month, 1)
    while d.weekday() != weekday:
        d += timedelta(days=1)
    return d + timedelta(days=7 * (int(ordinal) - 1))


class Zone:
    def __init__(self, cfg):
        self.base = timedelta(minutes=cfg["base_offset_min"])
        self.dst_cfg = cfg["dst"]
        self.delta = (timedelta(minutes=cfg["dst"]["delta_min"])
                      if cfg["dst"] else timedelta(0))

    def _rule_local(self, year, rule):
        h, m = map(int, rule["local_time"].split(":"))
        d = nth_weekday(year, rule["month"], WEEKDAYS[rule["weekday"]],
                        rule["ordinal"])
        return datetime(d.year, d.month, d.day, h, m)

    def transitions(self, year):
        """(dst_start_utc, dst_end_utc) for a year, or None."""
        if not self.dst_cfg:
            return None
        # start local_time is standard wall clock; end local_time is DST wall
        start_utc = self._rule_local(year, self.dst_cfg["start"]) - self.base
        end_utc = (self._rule_local(year, self.dst_cfg["end"])
                   - (self.base + self.delta))
        return start_utc, end_utc

    def offset_at(self, utc):
        tr = self.transitions(utc.year)
        if tr and tr[0] <= utc < tr[1]:
            return self.base + self.delta
        return self.base

    def local_to_utc(self, local):
        """Map a local wall time to UTC per the gap/overlap policies."""
        std_utc = local - self.base
        dst_utc = local - (self.base + self.delta)
        std_ok = self.offset_at(std_utc) == self.base
        dst_ok = (self.delta and
                  self.offset_at(dst_utc) == self.base + self.delta)
        if std_ok and dst_ok:
            return dst_utc          # ambiguous (fall-back): earlier instant
        if dst_ok:
            return dst_utc
        if std_ok:
            return std_utc
        # gap (spring-forward): first valid instant = the transition itself
        tr = self.transitions(local.year)
        return tr[0]


def parse_rule(rule):
    parts = rule.split()
    if parts[0] != "every" or "@" not in parts[-1]:
        raise ValueError(f"bad rule: {rule}")
    zone = parts[-1][1:]
    hh, mm = map(int, parts[-2].split(":"))
    spec = parts[1:-2]
    if spec == ["day"]:
        return ("daily", None, None), hh, mm, zone
    if len(spec) == 1 and spec[0] in WEEKDAYS:
        return ("weekly", WEEKDAYS[spec[0]], None), hh, mm, zone
    if len(spec) == 2 and spec[0] == "day":
        return ("monthday", int(spec[1]), None), hh, mm, zone
    if len(spec) == 2 and spec[1] in WEEKDAYS:
        ordn = {"1st": "1", "2nd": "2", "3rd": "3", "4th": "4",
                "last": "last"}[spec[0]]
        return ("monthly", WEEKDAYS[spec[1]], ordn), hh, mm, zone
    raise ValueError(f"bad rule: {rule}")


def occurrences(rule, start_utc, count):
    zones = {name: Zone(cfg)
             for name, cfg in json.load(open("ZONES.json")).items()}
    (kind, a, b), hh, mm, zname = parse_rule(rule)
    zone = zones[zname]
    # walk local dates starting a bit before start to be safe
    d = (start_utc - timedelta(days=3)).date()
    out = []
    while len(out) < count:
        emit = False
        if kind == "daily":
            emit = True
        elif kind == "weekly":
            emit = d.weekday() == a
        elif kind == "monthday":
            emit = d.day == a
        elif kind == "monthly":
            emit = d == nth_weekday(d.year, d.month, a, b)
        if emit:
            utc = zone.local_to_utc(datetime(d.year, d.month, d.day, hh, mm))
            if utc > start_utc:
                out.append(utc)
        d += timedelta(days=1)
    return out


def main():
    rule, start_s, count = sys.argv[1], sys.argv[2], int(sys.argv[3])
    start = datetime.fromisoformat(start_s.replace("Z", "+00:00"))
    start = start.replace(tzinfo=None)
    for utc in occurrences(rule, start, count):
        print(utc.strftime("%Y-%m-%dT%H:%M:%SZ"))


if __name__ == "__main__":
    main()
