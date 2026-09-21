#!/usr/bin/env bash
# Reference solution for T18-schema-migration. cwd = workspace copy.
set -euo pipefail

cat > app/migrate.py <<'PYEOF'
#!/usr/bin/env python3
"""Migrate db/app.db from schema v1 to v2 (see schema_v2.md).

Usage: python3 migrate.py db/app.db
"""
import sqlite3
import sys


def migrate(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("BEGIN")
        cur.execute(
            """
            CREATE TABLE addresses (
                id          INTEGER PRIMARY KEY,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                street      TEXT NOT NULL,
                city        TEXT NOT NULL,
                postal_code TEXT NOT NULL,
                country     TEXT NOT NULL,
                is_primary  INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        cur.execute(
            "INSERT INTO addresses (user_id, street, city, postal_code, country, is_primary)"
            " SELECT id, street, city, postal_code, country, 1 FROM users ORDER BY id"
        )
        cur.execute(
            "ALTER TABLE orders ADD COLUMN address_id INTEGER REFERENCES addresses(id)"
        )
        cur.execute(
            """
            UPDATE orders SET address_id = (
                SELECT a.id FROM addresses a
                WHERE a.user_id = orders.user_id
                  AND a.street || '|' || a.city || '|' || a.postal_code || '|' || a.country
                      = orders.address_snapshot
            )
            """
        )
        unmatched = cur.execute(
            "SELECT COUNT(*) FROM orders WHERE address_id IS NULL"
        ).fetchone()[0]
        if unmatched:
            raise RuntimeError(f"{unmatched} orders have unmatched address snapshots")
        for col in ("street", "city", "postal_code", "country"):
            cur.execute(f"ALTER TABLE users DROP COLUMN {col}")
        conn.commit()
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(f"foreign_key_check reported {len(violations)} violations")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python3 migrate.py <db-path>", file=sys.stderr)
        return 2
    try:
        migrate(sys.argv[1])
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"migration failed: {exc}", file=sys.stderr)
        return 1
    print("migration complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
PYEOF

cat > app/dao.py <<'PYEOF'
"""Data-access layer for the app database (v2 schema)."""
import sqlite3


def connect(db_path):
    """Open the database with row access by column name and FKs enforced."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_user_with_address(conn, user_id):
    """Return the user and their primary address as a flat dict, or None."""
    row = conn.execute(
        "SELECT u.id, u.name, u.email,"
        "       a.street, a.city, a.postal_code, a.country"
        " FROM users u JOIN addresses a"
        "   ON a.user_id = u.id AND a.is_primary = 1"
        " WHERE u.id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def get_order_shipping(conn, order_id):
    """Return shipping info for an order as a flat dict, or None.

    v2: the shipping address comes from the addresses row referenced by
    orders.address_id.
    """
    row = conn.execute(
        "SELECT o.id AS order_id, u.name AS user_name,"
        "       a.street, a.city, a.postal_code, a.country"
        " FROM orders o"
        " JOIN users u ON u.id = o.user_id"
        " JOIN addresses a ON a.id = o.address_id"
        " WHERE o.id = ?",
        (order_id,),
    ).fetchone()
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}
PYEOF

echo "T18 reference solution applied (app/migrate.py written, app/dao.py updated)"
