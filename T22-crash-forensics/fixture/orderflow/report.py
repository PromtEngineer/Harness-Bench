"""Aggregate settled orders into report.json."""
import json

from .batch import batches
from .pricing import order_totals


def build_report(orders):
    gross = net = 0
    by_region = {}
    count = 0
    for batch in batches(orders):
        for order in batch:
            g, n = order_totals(order)
            gross += g
            net += n
            count += 1
            r = by_region.setdefault(order.region, {"orders": 0, "net_cents": 0})
            r["orders"] += 1
            r["net_cents"] += n
    return {
        "orders": count,
        "gross_cents": gross,
        "discount_cents": gross - net,
        "net_cents": net,
        "by_region": {k: by_region[k] for k in sorted(by_region)},
    }


def write_report(orders, path="report.json"):
    report = build_report(orders)
    with open(path, "w") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return report
