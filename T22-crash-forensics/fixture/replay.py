#!/usr/bin/env python3
"""Replay the order feed through the pipeline and write report.json."""
from orderflow.parse import parse_order
from orderflow.report import write_report

with open("data/orders.ndjson") as fh:
    orders = [parse_order(line) for line in fh if line.strip()]

report = write_report(orders)
print(f"settled {report['orders']} orders, net {report['net_cents']} cents")
