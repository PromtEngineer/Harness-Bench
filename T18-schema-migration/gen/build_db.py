#!/usr/bin/env python3
"""Build the v1 database + expected artifacts for T18-schema-migration.

Deterministic (seed 180018). Writes:
  fixture/app/db/app.db        the workspace database (v1)
  expected/pristine-v1.db      identical copy the checker migrates fresh
  expected/spotchecks.json     10 order -> joined-address expectations
  expected/dao_expected.json   expected dao return values (hidden tests)
  expected/schema_v2.sha256    guard hash for fixture/app/schema_v2.md
"""
import hashlib
import json
import os
import random
import shutil
import sqlite3
import sys

SEED = 180018
N_USERS = 300
N_ORDERS = 900

FIRST = ["ada", "bruno", "carla", "dmitri", "elena", "farid", "greta", "hugo",
         "ines", "jonas", "kira", "liam", "mona", "nils", "olga", "pavel",
         "quinn", "rosa", "sven", "tara"]
LAST = ["adler", "bishop", "castro", "duval", "eriksen", "fontaine", "garza",
        "holt", "ivanov", "jensen", "kovacs", "lindt", "moreau", "novak",
        "ortiz"]
STREETS = ["Alder", "Birch", "Cedar", "Dogwood", "Elm", "Fir", "Hazel",
           "Juniper", "Maple", "Oak", "Pine", "Rowan", "Spruce", "Willow"]
SUFFIX = ["Ave", "Blvd", "Ct", "Ln", "Rd", "St", "Way"]
CITIES = ["Arlington", "Brookfield", "Clearwater", "Dunmore", "Eastvale",
          "Fairhaven", "Glenridge", "Harborview", "Ironwood", "Juneberry"]
COUNTRIES = ["DE", "FR", "NL", "SE", "US"]


def build(db_path: str, rng: random.Random):
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE users (
            id          INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            email       TEXT NOT NULL UNIQUE,
            street      TEXT NOT NULL,
            city        TEXT NOT NULL,
            postal_code TEXT NOT NULL,
            country     TEXT NOT NULL
        );
        CREATE TABLE orders (
            id               INTEGER PRIMARY KEY,
            user_id          INTEGER NOT NULL REFERENCES users(id),
            total_cents      INTEGER NOT NULL,
            address_snapshot TEXT NOT NULL
        );
        """
    )
    users = []
    for uid in range(1, N_USERS + 1):
        first = rng.choice(FIRST)
        last = rng.choice(LAST)
        name = f"{first.capitalize()} {last.capitalize()}"
        email = f"{first}.{last}.{uid}@example.com"
        street = f"{rng.randrange(1, 9900)} {rng.choice(STREETS)} {rng.choice(SUFFIX)}"
        city = rng.choice(CITIES)
        postal = f"{rng.randrange(10000, 100000)}"
        country = rng.choice(COUNTRIES)
        users.append((uid, name, email, street, city, postal, country))
    cur.executemany("INSERT INTO users VALUES (?,?,?,?,?,?,?)", users)

    orders = []
    for oid in range(1, N_ORDERS + 1):
        u = users[rng.randrange(N_USERS)]
        snapshot = f"{u[3]}|{u[4]}|{u[5]}|{u[6]}"
        total = rng.randrange(199, 99999)
        orders.append((oid, u[0], total, snapshot))
    cur.executemany("INSERT INTO orders VALUES (?,?,?,?)", orders)
    conn.commit()
    conn.close()
    return users, orders


def main():
    task = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    rng = random.Random(SEED)
    db_path = os.path.join(task, "fixture", "app", "db", "app.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    users, orders = build(db_path, rng)
    shutil.copyfile(db_path, os.path.join(task, "expected", "pristine-v1.db"))

    by_uid = {u[0]: u for u in users}

    # Spot-check joins: 10 deterministic orders spread over the id space.
    spot_ids = [17, 88, 154, 260, 333, 401, 555, 672, 789, 900]
    spot = []
    for oid in spot_ids:
        o = orders[oid - 1]
        assert o[0] == oid
        u = by_uid[o[1]]
        spot.append({
            "order_id": oid,
            "user_id": u[0],
            "user_name": u[1],
            "street": u[3],
            "city": u[4],
            "postal_code": u[5],
            "country": u[6],
        })
    with open(os.path.join(task, "expected", "spotchecks.json"), "w") as fh:
        json.dump(spot, fh, indent=2)
        fh.write("\n")

    # Expected dao outputs for the hidden test suite.
    user_ids = [3, 42, 77, 120, 150, 199, 234, 267, 288, 300]
    dao_users = {}
    for uid in user_ids:
        u = by_uid[uid]
        dao_users[str(uid)] = {
            "id": u[0], "name": u[1], "email": u[2], "street": u[3],
            "city": u[4], "postal_code": u[5], "country": u[6],
        }
    order_ids = [1, 55, 133, 289, 350, 477, 512, 640, 731, 899]
    dao_orders = {}
    for oid in order_ids:
        o = orders[oid - 1]
        u = by_uid[o[1]]
        dao_orders[str(oid)] = {
            "order_id": oid, "user_name": u[1], "street": u[3],
            "city": u[4], "postal_code": u[5], "country": u[6],
        }
    with open(os.path.join(task, "expected", "dao_expected.json"), "w") as fh:
        json.dump({"users": dao_users, "orders": dao_orders}, fh, indent=2)
        fh.write("\n")

    # Guard hash for the spec document.
    spec = os.path.join(task, "fixture", "app", "schema_v2.md")
    h = hashlib.sha256(open(spec, "rb").read()).hexdigest()
    with open(os.path.join(task, "expected", "schema_v2.sha256"), "w") as fh:
        fh.write(h + "  app/schema_v2.md\n")

    # Sanity: every snapshot matches its user's v1 address.
    for o in orders:
        u = by_uid[o[1]]
        assert o[3] == f"{u[3]}|{u[4]}|{u[5]}|{u[6]}"
    print(f"built db: {N_USERS} users, {N_ORDERS} orders; spec sha256 {h}")


if __name__ == "__main__":
    sys.exit(main())
