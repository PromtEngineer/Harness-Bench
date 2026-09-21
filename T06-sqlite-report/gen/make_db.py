#!/usr/bin/env python3
"""Deterministic generator for fixture/db/sales.db (fixed seed).

All prices are exact multiples of 0.25 so every revenue sum is exactly
representable in binary floating point (no summation-order hazards).
"""

import pathlib
import random
import sqlite3
from datetime import date, timedelta

SEED = 20260801
random.seed(SEED)

TASK = pathlib.Path(__file__).resolve().parent.parent
DB = TASK / "fixture" / "db" / "sales.db"
DB.parent.mkdir(parents=True, exist_ok=True)
if DB.exists():
    DB.unlink()

CATEGORIES = ["electronics", "office", "kitchen", "outdoors", "toys", "grocery"]
REGIONS = ["east", "north", "south", "west"]
STATUSES = ["completed", "shipped", "pending", "refunded"]
STATUS_W = [0.74, 0.12, 0.06, 0.08]
N_CUSTOMERS = 200
N_PRODUCTS = 50
N_ORDERS = 2000
BOOST_PAIR = (7, 21)   # frequently co-purchased pair (unique q4 winner)
BOOST_P = 0.036

FIRST_DAY = date(2024, 7, 1)
N_DAYS = 730  # through 2026-06-29

con = sqlite3.connect(DB)
cur = con.cursor()
cur.executescript(
    """
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        name        TEXT NOT NULL,
        email       TEXT NOT NULL,
        signup_date TEXT NOT NULL
    );
    CREATE TABLE products (
        product_id INTEGER PRIMARY KEY,
        name       TEXT NOT NULL,
        category   TEXT NOT NULL,
        base_price REAL NOT NULL
    );
    CREATE TABLE orders (
        order_id    INTEGER PRIMARY KEY,
        customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
        region      TEXT NOT NULL,
        status      TEXT NOT NULL,
        order_date  TEXT NOT NULL
    );
    CREATE TABLE order_items (
        item_id    INTEGER PRIMARY KEY,
        order_id   INTEGER NOT NULL REFERENCES orders(order_id),
        product_id INTEGER NOT NULL REFERENCES products(product_id),
        quantity   INTEGER NOT NULL,
        unit_price REAL NOT NULL
    );
    """
)

# --- customers -------------------------------------------------------------
FIRST = ["ada", "ben", "cara", "dev", "eli", "fay", "gus", "hana", "ivo", "june"]
LAST = ["stone", "reyes", "kim", "patel", "novak", "diaz", "moss", "chen", "wolf", "ray"]
for cid in range(1, N_CUSTOMERS + 1):
    fn = random.choice(FIRST)
    ln = random.choice(LAST)
    signup = FIRST_DAY - timedelta(days=random.randrange(30, 700))
    cur.execute(
        "INSERT INTO customers VALUES (?,?,?,?)",
        (cid, f"{fn.title()} {ln.title()}", f"{fn}.{ln}{cid}@example.com", signup.isoformat()),
    )

# --- products --------------------------------------------------------------
ADJ = ["compact", "deluxe", "eco", "pro", "mini", "ultra", "classic", "smart"]
NOUN = ["kettle", "lamp", "router", "tent", "puzzle", "notebook", "blender", "speaker",
        "chair", "backpack"]
prod_quarters = {}
for pid in range(1, N_PRODUCTS + 1):
    quarters = random.randrange(4, 481)  # 1.00 .. 120.00 in 0.25 steps
    prod_quarters[pid] = quarters
    cur.execute(
        "INSERT INTO products VALUES (?,?,?,?)",
        (pid, f"{random.choice(ADJ)}-{random.choice(NOUN)}-{pid:03d}",
         random.choice(CATEGORIES), quarters * 0.25),
    )

# --- orders + items --------------------------------------------------------
item_id = 0
for oid in range(1, N_ORDERS + 1):
    cid = random.randrange(1, N_CUSTOMERS + 1)
    region = random.choice(REGIONS)
    status = random.choices(STATUSES, STATUS_W)[0]
    d = FIRST_DAY + timedelta(days=random.randrange(N_DAYS))
    cur.execute("INSERT INTO orders VALUES (?,?,?,?,?)", (oid, cid, region, status, d.isoformat()))

    n_lines = random.choices([1, 2, 3, 4, 5], [0.20, 0.30, 0.25, 0.15, 0.10])[0]
    pids = [random.randrange(1, N_PRODUCTS + 1) for _ in range(n_lines)]
    if random.random() < BOOST_P:
        pids += list(BOOST_PAIR)
    for pid in pids:
        item_id += 1
        jitter = random.randrange(-2, 3)  # +/- 0.50 in 0.25 steps
        quarters = max(1, prod_quarters[pid] + jitter)
        qty = random.randrange(1, 9)
        cur.execute(
            "INSERT INTO order_items VALUES (?,?,?,?,?)",
            (item_id, oid, pid, qty, quarters * 0.25),
        )

con.commit()

# --- sanity assertions -----------------------------------------------------
months = {r[0] for r in cur.execute(
    "SELECT DISTINCT strftime('%Y-%m', order_date) FROM orders WHERE status != 'refunded'")}
needed = ["2024-12"] + [f"2025-{m:02d}" for m in range(1, 13)]
assert all(m in months for m in needed), sorted(months)
for region in REGIONS:
    n = cur.execute(
        "SELECT COUNT(*) FROM orders WHERE region=? AND status!='refunded'", (region,)
    ).fetchone()[0]
    assert n > 50, (region, n)
n_ref = cur.execute("SELECT COUNT(*) FROM orders WHERE status='refunded'").fetchone()[0]
assert 50 < n_ref < 400, n_ref
n_items = cur.execute("SELECT COUNT(*) FROM order_items").fetchone()[0]
assert 4500 <= n_items <= 6000, n_items
con.close()
print(f"wrote {DB} ({n_items} items, {n_ref} refunded orders)")
