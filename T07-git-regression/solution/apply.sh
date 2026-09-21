#!/usr/bin/env bash
# cwd = workspace copy. Applies the reference solution.
set -euo pipefail

# 1. Find the regression commit from the repo itself (first commit at which
#    tests/test_bulk.py fails == the "Simplify discount math" commit).
BAD=$(git -C pricer log --format=%H --grep='Simplify discount math')
printf '%s\n' "$BAD" > regression.txt

# 2. Restore half-up rounding in bulk_total_cents at HEAD (working tree fix).
python3 - <<'PY'
import pathlib

p = pathlib.Path("pricer/src/pricer/discount.py")
src = p.read_text()
buggy = """    \"\"\"Discounted total in cents.\"\"\"
    gross = unit_cents * quantity
    pct = discount_pct(quantity)
    return gross * (100 - pct) // 100"""
fixed = """    \"\"\"Discounted total in cents, rounded half-up to the nearest cent.\"\"\"
    gross = unit_cents * quantity
    pct = discount_pct(quantity)
    return (gross * (100 - pct) + 50) // 100"""
assert buggy in src, "unexpected discount.py contents"
p.write_text(src.replace(buggy, fixed))
PY
