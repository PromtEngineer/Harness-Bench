"""Data-access layer for the app database (v1 schema)."""
import sqlite3


def connect(db_path):
    """Open the database with row access by column name and FKs enforced."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_user_with_address(conn, user_id):
    """Return the user and their address as a flat dict, or None."""
    row = conn.execute(
        "SELECT id, name, email, street, city, postal_code, country"
        " FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def get_order_shipping(conn, order_id):
    """Return shipping info for an order as a flat dict, or None.

    v1: the shipping address is read straight off the user row (the
    address_snapshot column is only kept for auditing).
    """
    row = conn.execute(
        "SELECT o.id AS order_id, u.name AS user_name,"
        "       u.street, u.city, u.postal_code, u.country"
        " FROM orders o JOIN users u ON u.id = o.user_id"
        " WHERE o.id = ?",
        (order_id,),
    ).fetchone()
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}
