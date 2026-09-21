"""Hidden dao tests for T18-schema-migration.

Run by check.sh with APP_DB set and PYTHONPATH containing the workspace app/.
The checker directory is derived from this test file instead of being exposed to
the submitted program through its environment.
"""
import json
import os
from pathlib import Path

import pytest

import dao

TASK_DIR = Path(__file__).resolve().parents[1]
APP_DB = os.environ["APP_DB"]

with (TASK_DIR / "expected" / "dao_expected.json").open() as _fh:
    EXPECTED = json.load(_fh)


@pytest.fixture()
def conn():
    c = dao.connect(APP_DB)
    yield c
    c.close()


@pytest.mark.parametrize("uid", sorted(EXPECTED["users"], key=int))
def test_get_user_with_address(conn, uid):
    assert dao.get_user_with_address(conn, int(uid)) == EXPECTED["users"][uid]


@pytest.mark.parametrize("oid", sorted(EXPECTED["orders"], key=int))
def test_get_order_shipping(conn, oid):
    assert dao.get_order_shipping(conn, int(oid)) == EXPECTED["orders"][oid]


def test_missing_user_returns_none(conn):
    assert dao.get_user_with_address(conn, 999999) is None


def test_missing_order_returns_none(conn):
    assert dao.get_order_shipping(conn, 999999) is None


def test_user_address_comes_from_addresses_table(conn):
    # users must no longer carry address columns; dao must join addresses.
    cols = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    assert "street" not in cols and "city" not in cols
    got = dao.get_user_with_address(conn, 42)
    row = conn.execute(
        "SELECT street, city, postal_code, country FROM addresses"
        " WHERE user_id = 42 AND is_primary = 1"
    ).fetchone()
    assert got["street"] == row[0]
    assert got["city"] == row[1]
    assert got["postal_code"] == row[2]
    assert got["country"] == row[3]
