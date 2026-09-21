# pricer

A tiny pricing library. All money amounts are integer cents; tax rates are
basis points. Pure Python, no dependencies.

Run the tests with `python3 -m pytest`.

## Usage

```python
from pricer.core import line_total_cents

line_total_cents(499, 3)  # -> 1497
```

## Bulk discounts

Quantity tiers: 10+ items -> 5% off, 50+ -> 10% off, 100+ -> 15% off.
Totals are rounded to the nearest cent.

## Changelog

- 0.3.0: cart totals, currency parsing, multi-rate tax.
