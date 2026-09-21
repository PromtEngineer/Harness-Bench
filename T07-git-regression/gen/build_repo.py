#!/usr/bin/env python3
"""Build fixture/pricer: a deterministic 30-commit git repo with a mid-history
regression (commit 17 'Simplify discount math' drops half-up rounding).

Also writes expected/{bad_commit,first_commit,orig_head,tests.sha256}.
"""

import hashlib
import os
import pathlib
import shutil
import subprocess
from datetime import datetime, timedelta

TASK = pathlib.Path(__file__).resolve().parent.parent
REPO = TASK / "fixture" / "pricer"
if REPO.exists():
    shutil.rmtree(REPO)
REPO.mkdir(parents=True)

BASE_ENV = dict(
    os.environ,
    GIT_CONFIG_GLOBAL="/dev/null",
    GIT_CONFIG_SYSTEM="/dev/null",
    PYTHONDONTWRITEBYTECODE="1",
)

ALICE = ("Alice Doe", "alice@example.com")
BOB = ("Bob Ray", "bob@example.com")
T0 = datetime(2026, 2, 2, 9, 0, 0)


def git(*args, env=None):
    subprocess.run(["git", *args], cwd=REPO, check=True, env=env or BASE_ENV,
                   stdout=subprocess.PIPE)


def git_out(*args):
    return subprocess.check_output(["git", *args], cwd=REPO, env=BASE_ENV, text=True)


def write(rel, content):
    p = REPO / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def commit(n, msg, author):
    date = (T0 + timedelta(days=n - 1, hours=(n * 3) % 8, minutes=(n * 17) % 60)
            ).strftime("%Y-%m-%dT%H:%M:%S+0000")
    env = dict(
        BASE_ENV,
        GIT_AUTHOR_NAME=author[0], GIT_AUTHOR_EMAIL=author[1],
        GIT_COMMITTER_NAME="bench", GIT_COMMITTER_EMAIL="bench@local",
        GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date,
    )
    git("add", "-A", env=env)
    git("-c", "user.name=bench", "-c", "user.email=bench@local",
        "-c", "commit.gpgsign=false", "commit", "-q", "-m", msg, env=env)


def pytest_rc(*args):
    return subprocess.run(
        ["python3", "-m", "pytest", "-q", "-p", "no:cacheprovider", *args],
        cwd=REPO, env=BASE_ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    ).returncode


# ---------------------------------------------------------------------------
# File versions
# ---------------------------------------------------------------------------

CONFTEST = '''import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
'''

GITIGNORE = "__pycache__/\n*.pyc\n.pytest_cache/\n"

README_V1 = '''# pricer

A tiny pricing library. All money amounts are integer cents; tax rates are
basis points. Pure Python, no dependencies.

Run the tests with `python3 -m pytest`.
'''

README_V2 = README_V1 + '''
## Usage

```python
from pricer.core import line_total_cents

line_total_cents(499, 3)  # -> 1497
```
'''

README_V3 = README_V2 + '''
## Bulk discounts

Quantity tiers: 10+ items -> 5% off, 50+ -> 10% off, 100+ -> 15% off.
Totals are rounded to the nearest cent.
'''

README_V4 = README_V3 + '''
## Changelog

- 0.3.0: cart totals, currency parsing, multi-rate tax.
'''

INIT_V1 = '__version__ = "0.1.0"\n'

INIT_V2 = '''__version__ = "0.2.0"

from .cart import cart_total_cents
from .core import line_total_cents, subtotal_cents
from .currency import format_cents, parse_cents
from .discount import bulk_total_cents, discount_pct
from .tax import price_with_tax_cents, sales_tax_cents
'''

INIT_V3 = INIT_V2.replace('"0.2.0"', '"0.3.0"')

CORE_V1 = '''"""Core price computations (all amounts in integer cents)."""


def line_total_cents(unit_cents: int, quantity: int) -> int:
    """Total for one line item, no discounts."""
    if unit_cents < 0:
        raise ValueError("unit_cents must be >= 0")
    if quantity < 0:
        raise ValueError("quantity must be >= 0")
    return unit_cents * quantity
'''

CORE_V2 = CORE_V1 + '''

def subtotal_cents(lines) -> int:
    """Sum of line totals for an iterable of (unit_cents, quantity) pairs."""
    return sum(line_total_cents(unit, qty) for (unit, qty) in lines)
'''

CORE_V3 = CORE_V2 + '''

def clamp_quantity(quantity: int, lo: int = 0, hi: int = 1_000_000) -> int:
    """Clamp a requested quantity into the supported [lo, hi] range."""
    return max(lo, min(hi, quantity))
'''

CORE_V4 = CORE_V3.replace(
    '"""Core price computations (all amounts in integer cents)."""',
    '"""Core price computations.\n\nAll amounts are integer cents; quantities are\nnon-negative integers. Functions raise ValueError on invalid input.\n"""',
)

DISCOUNT_V1 = '''"""Quantity-based bulk discounts."""


def discount_pct(quantity: int) -> int:
    """Discount percentage for a given quantity."""
    if quantity >= 100:
        return 15
    if quantity >= 50:
        return 10
    if quantity >= 10:
        return 5
    return 0
'''

DISCOUNT_V2 = DISCOUNT_V1 + '''

def bulk_total_cents(unit_cents: int, quantity: int) -> int:
    """Discounted total in cents, rounded half-up to the nearest cent."""
    gross = unit_cents * quantity
    pct = discount_pct(quantity)
    return (gross * (100 - pct) + 50) // 100
'''

DISCOUNT_V3 = DISCOUNT_V2.replace(
    '"""Quantity-based bulk discounts."""',
    '''"""Quantity-based bulk discounts.

Tier table:
    quantity >= 100  -> 15% off
    quantity >=  50  -> 10% off
    quantity >=  10  ->  5% off
    otherwise        ->  no discount
"""''',
)

# Commit 17: THE REGRESSION - drops the +50 half-up rounding term (floor).
DISCOUNT_V4 = DISCOUNT_V3.replace(
    '''    """Discounted total in cents, rounded half-up to the nearest cent."""
    gross = unit_cents * quantity
    pct = discount_pct(quantity)
    return (gross * (100 - pct) + 50) // 100''',
    '''    """Discounted total in cents."""
    gross = unit_cents * quantity
    pct = discount_pct(quantity)
    return gross * (100 - pct) // 100''',
)

DISCOUNT_V5 = DISCOUNT_V4.replace(
    '    """Discount percentage for a given quantity."""',
    '    """Discount percentage for a given quantity (see tier table above)."""',
)

TAX_V1 = '''"""Sales tax (rates in basis points, amounts in cents)."""


def sales_tax_cents(amount_cents: int, rate_bp: int) -> int:
    """Tax due on amount_cents at rate_bp basis points, rounded half-up."""
    if rate_bp < 0:
        raise ValueError("rate_bp must be >= 0")
    return (amount_cents * rate_bp + 5000) // 10000
'''

TAX_V2 = TAX_V1 + '''

def price_with_tax_cents(amount_cents: int, rate_bp: int) -> int:
    """Amount plus tax."""
    return amount_cents + sales_tax_cents(amount_cents, rate_bp)
'''

TAX_V3 = TAX_V2.replace(
    '"""Tax due on amount_cents at rate_bp basis points, rounded half-up."""',
    '''"""Tax due on amount_cents at rate_bp basis points.

    Rounded half-up to the nearest cent (10000 bp == 100%).
    """''',
)

TAX_V4 = TAX_V3 + '''

def total_tax_cents(amount_cents: int, rates_bp) -> int:
    """Total tax for several independent rates applied to the same amount."""
    return sum(sales_tax_cents(amount_cents, rate) for rate in rates_bp)
'''

CURRENCY_V1 = '''"""Currency formatting helpers."""


def format_cents(cents: int) -> str:
    """Format an amount in cents as a dollar string, e.g. 1234 -> "$12.34"."""
    return "$%d.%02d" % (cents // 100, cents % 100)
'''

CURRENCY_V2 = '''"""Currency formatting helpers."""


def format_cents(cents: int) -> str:
    """Format cents as dollars; negative amounts get a leading minus."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return "%s$%d.%02d" % (sign, cents // 100, cents % 100)
'''

CURRENCY_V3 = CURRENCY_V2 + '''

def parse_cents(text: str) -> int:
    """Parse "$12.34" / "-$0.50" / "7" style strings into integer cents."""
    t = text.strip().replace("$", "")
    sign = -1 if t.startswith("-") else 1
    t = t.lstrip("+-")
    if "." in t:
        dollars, _, frac = t.partition(".")
        frac = (frac + "00")[:2]
    else:
        dollars, frac = t, "00"
    return sign * (int(dollars or 0) * 100 + int(frac))
'''

CART_V1 = '''"""Cart-level totals built on discounts and tax."""

from .discount import bulk_total_cents
from .tax import sales_tax_cents


def cart_total_cents(lines, tax_rate_bp: int = 0) -> int:
    """Total for (unit_cents, quantity) lines: bulk pricing plus tax."""
    subtotal = sum(bulk_total_cents(unit, qty) for (unit, qty) in lines)
    return subtotal + sales_tax_cents(subtotal, tax_rate_bp)
'''

TEST_CORE_V1 = '''from pricer.core import line_total_cents

import pytest


def test_line_total():
    assert line_total_cents(499, 3) == 1497
    assert line_total_cents(0, 10) == 0


def test_line_total_rejects_negatives():
    with pytest.raises(ValueError):
        line_total_cents(-1, 2)
    with pytest.raises(ValueError):
        line_total_cents(100, -2)
'''

TEST_CORE_V2 = TEST_CORE_V1.replace(
    "from pricer.core import line_total_cents",
    "from pricer.core import line_total_cents, subtotal_cents",
) + '''

def test_subtotal():
    assert subtotal_cents([(250, 2), (100, 3)]) == 800
    assert subtotal_cents([]) == 0
'''

TEST_BULK = '''from pricer.discount import bulk_total_cents, discount_pct


def test_tiers():
    assert discount_pct(1) == 0
    assert discount_pct(9) == 0
    assert discount_pct(10) == 5
    assert discount_pct(50) == 10
    assert discount_pct(100) == 15


def test_no_discount_small_qty():
    assert bulk_total_cents(500, 3) == 1500


def test_bulk_rounds_half_up():
    # 333 * 10 = 3330 gross; 5% off -> 3163.5 cents -> rounds up to 3164
    assert bulk_total_cents(333, 10) == 3164


def test_bulk_fifty_exact():
    # 999 * 50 = 49950 gross; 10% off -> 44955 exactly (no rounding needed)
    assert bulk_total_cents(999, 50) == 44955


def test_bulk_hundred_rounding():
    # 101 * 101 = 10201 gross; 15% off -> 8670.85 -> rounds up to 8671
    assert bulk_total_cents(101, 101) == 8671
'''

TEST_TAX_V1 = '''from pricer.tax import sales_tax_cents

import pytest


def test_sales_tax_rounds_half_up():
    assert sales_tax_cents(10000, 875) == 875
    assert sales_tax_cents(999, 875) == 87   # 87.41 -> 87
    assert sales_tax_cents(1000, 850) == 85


def test_sales_tax_rejects_negative_rate():
    with pytest.raises(ValueError):
        sales_tax_cents(100, -1)
'''

TEST_TAX_V2 = TEST_TAX_V1.replace(
    "from pricer.tax import sales_tax_cents",
    "from pricer.tax import sales_tax_cents, total_tax_cents",
) + '''

def test_total_tax_multiple_rates():
    assert total_tax_cents(10000, [500, 250]) == 500 + 250
    assert total_tax_cents(10000, []) == 0
'''

TEST_CURRENCY_V1 = '''from pricer.currency import format_cents


def test_format_cents():
    assert format_cents(1234) == "$12.34"
    assert format_cents(5) == "$0.05"
    assert format_cents(0) == "$0.00"
'''

TEST_CURRENCY_V2 = TEST_CURRENCY_V1.replace(
    "from pricer.currency import format_cents",
    "from pricer.currency import format_cents, parse_cents",
) + '''

def test_format_negative():
    assert format_cents(-50) == "-$0.50"
    assert format_cents(-1234) == "-$12.34"


def test_parse_cents():
    assert parse_cents("$12.34") == 1234
    assert parse_cents("-$0.50") == -50
    assert parse_cents("7") == 700
    assert parse_cents("3.5") == 350
'''

# Values chosen so floor == half-up (bug-neutral): cart tests stay green at HEAD.
TEST_CART = '''from pricer.cart import cart_total_cents


def test_cart_no_tax():
    # (250,4): no tier; (200,10): 5% off 2000 -> 1900; (120,50): 10% off 6000 -> 5400
    assert cart_total_cents([(250, 4), (200, 10), (120, 50)]) == 1000 + 1900 + 5400


def test_cart_with_tax():
    # subtotal 8300; 8.75% tax -> 726.25 -> 726
    assert cart_total_cents([(250, 4), (200, 10), (120, 50)], tax_rate_bp=875) == 8300 + 726
'''

# ---------------------------------------------------------------------------
# Commit sequence (exactly 30)
# ---------------------------------------------------------------------------

STEPS = [
    ({"README.md": README_V1, ".gitignore": GITIGNORE, "conftest.py": CONFTEST,
      "src/pricer/__init__.py": INIT_V1}, "Initial project scaffold", ALICE),
    ({"src/pricer/core.py": CORE_V1}, "Add core line total computation", ALICE),
    ({"tests/test_core.py": TEST_CORE_V1}, "Add core tests", BOB),
    ({"src/pricer/discount.py": DISCOUNT_V1}, "Add quantity discount tiers", ALICE),
    ({"src/pricer/discount.py": DISCOUNT_V2},
     "Add bulk pricing with half-up cent rounding", ALICE),
    ({"tests/test_bulk.py": TEST_BULK}, "Add bulk discount tests", BOB),
    ({"src/pricer/tax.py": TAX_V1}, "Add sales tax computation", ALICE),
    ({"tests/test_tax.py": TEST_TAX_V1}, "Add tax tests", BOB),
    ({"src/pricer/currency.py": CURRENCY_V1}, "Add currency formatting", BOB),
    ({"tests/test_currency.py": TEST_CURRENCY_V1}, "Add currency tests", BOB),
    ({"src/pricer/core.py": CORE_V2}, "Add subtotal helper", ALICE),
    ({"tests/test_core.py": TEST_CORE_V2}, "Cover subtotal helper", BOB),
    ({"README.md": README_V2}, "Document basic usage", ALICE),
    ({"src/pricer/tax.py": TAX_V2}, "Add tax-inclusive price helper", ALICE),
    ({"src/pricer/discount.py": DISCOUNT_V3}, "Document discount tiers", BOB),
    ({"src/pricer/currency.py": CURRENCY_V2},
     "Handle negative amounts in format_cents", BOB),
    ({"src/pricer/discount.py": DISCOUNT_V4}, "Simplify discount math", ALICE),  # BUG
    ({"src/pricer/core.py": CORE_V3}, "Validate quantity bounds", ALICE),
    ({"README.md": README_V3}, "Document bulk discount tiers", BOB),
    ({"src/pricer/tax.py": TAX_V3}, "Clarify tax rounding docs", ALICE),
    ({"src/pricer/cart.py": CART_V1}, "Add cart total computation", ALICE),
    ({"tests/test_cart.py": TEST_CART}, "Add cart tests", BOB),
    ({"src/pricer/currency.py": CURRENCY_V3}, "Add currency parsing", BOB),
    ({"tests/test_currency.py": TEST_CURRENCY_V2}, "Extend currency tests", BOB),
    ({"src/pricer/__init__.py": INIT_V2}, "Export public API", ALICE),
    ({"src/pricer/discount.py": DISCOUNT_V5}, "Clarify discount docstring", BOB),
    ({"src/pricer/tax.py": TAX_V4}, "Support multiple tax rates", ALICE),
    ({"tests/test_tax.py": TEST_TAX_V2}, "Cover multiple tax rates", BOB),
    ({"src/pricer/core.py": CORE_V4}, "Polish core docstrings", ALICE),
    ({"src/pricer/__init__.py": INIT_V3, "README.md": README_V4},
     "Release 0.3.0", ALICE),
]

assert len(STEPS) == 30
BUG_INDEX = 17  # 1-based commit number of the regression

git("init", "-q", "-b", "main")
for n, (files, msg, author) in enumerate(STEPS, start=1):
    for rel, content in files.items():
        write(rel, content)
    commit(n, msg, author)
    if n == BUG_INDEX - 1:
        assert pytest_rc() == 0, "suite must be green just before the bug commit"
    if n == BUG_INDEX:
        assert pytest_rc("tests/test_bulk.py") != 0, "bug commit must break test_bulk"

# HEAD state: only test_bulk fails.
assert pytest_rc("tests/test_bulk.py") != 0
assert pytest_rc("--ignore=tests/test_bulk.py") == 0

log = git_out("log", "--format=%H %s").strip().splitlines()
assert len(log) == 30, len(log)
bad = [line.split()[0] for line in log if "Simplify discount math" in line]
assert len(bad) == 1
bad_hash = bad[0]
assert log[30 - BUG_INDEX].startswith(bad_hash)
first_hash = log[-1].split()[0]
head_hash = log[0].split()[0]

expected = TASK / "expected"
expected.mkdir(exist_ok=True)
(expected / "bad_commit.txt").write_text(bad_hash + "\n")
(expected / "first_commit.txt").write_text(first_hash + "\n")
(expected / "orig_head.txt").write_text(head_hash + "\n")

paths = sorted(str(p.relative_to(REPO)) for p in (REPO / "tests").rglob("*.py"))
paths.append("conftest.py")
lines = ["%s  %s" % (hashlib.sha256((REPO / p).read_bytes()).hexdigest(), p)
         for p in sorted(paths)]
(expected / "tests.sha256").write_text("\n".join(lines) + "\n")

# Drop build-time bytecode caches from the shipped fixture.
for cache in REPO.rglob("__pycache__"):
    shutil.rmtree(cache)
if (REPO / ".pytest_cache").exists():
    shutil.rmtree(REPO / ".pytest_cache")

print("bad commit:", bad_hash)
print("first     :", first_hash)
print("orig head :", head_hash)
