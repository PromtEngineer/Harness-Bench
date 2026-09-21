#!/usr/bin/env bash
# Checker for T18-schema-migration. cwd = copy of the workspace after the agent
# ran. env: TASK_DIR = absolute path of the task directory.
set -u
CHECKER_DIR=${TASK_DIR:-}
source "$CHECKER_DIR/checker_guard.sh" || exit 1
unset TASK_DIR

fail() { echo "CHECK FAIL: $*" >&2; exit 1; }

[ -n "${CHECKER_DIR:-}" ] || fail "TASK_DIR is not set"
[ -f app/schema_v2.md ] || fail "app/schema_v2.md is missing"
[ -f app/dao.py ] || fail "app/dao.py is missing"
[ -f app/migrate.py ] || fail "app/migrate.py is missing"

# 1. Spec document must be unmodified.
python3 - "$CHECKER_DIR/expected/schema_v2.sha256" app/schema_v2.md <<'PYEOF' || exit 1
import hashlib, sys
want = open(sys.argv[1]).read().split()[0]
have = hashlib.sha256(open(sys.argv[2], "rb").read()).hexdigest()
if have != want:
    print(f"CHECK FAIL: app/schema_v2.md was modified (sha256 {have} != {want})", file=sys.stderr)
    sys.exit(1)
PYEOF
[ $? -eq 0 ] || exit 1

# 2. Always migrate a pristine v1 database (the agent's own db state is ignored).
cp "$CHECKER_DIR/expected/pristine-v1.db" app/db/app.db || fail "could not restore pristine v1 db"
( cd app && python3 migrate.py db/app.db ) || fail "migrate.py exited nonzero on a pristine v1 database"

# 3. Structural checks + spot-check joins.
python3 - "$CHECKER_DIR" <<'PYEOF' || exit 1
import json, sqlite3, sys

task = sys.argv[1]
conn = sqlite3.connect("app/db/app.db")

def die(msg):
    print(f"CHECK FAIL: {msg}", file=sys.stderr)
    sys.exit(1)

violations = conn.execute("PRAGMA foreign_key_check").fetchall()
if violations:
    die(f"foreign_key_check reported violations: {violations[:5]}")

counts = {}
for table in ("users", "orders", "addresses"):
    try:
        counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except sqlite3.OperationalError as exc:
        die(f"table {table} not queryable: {exc}")
if counts["users"] != 300:
    die(f"users row count {counts['users']} != 300")
if counts["orders"] != 900:
    die(f"orders row count {counts['orders']} != 900")
if counts["addresses"] != 300:
    die(f"addresses row count {counts['addresses']} != users count 300")

user_cols = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
for col in ("street", "city", "postal_code", "country"):
    if col in user_cols:
        die(f"users still has column {col}")
for col in ("id", "name", "email"):
    if col not in user_cols:
        die(f"users lost column {col}")

addr_cols = {r[1] for r in conn.execute("PRAGMA table_info(addresses)")}
for col in ("id", "user_id", "street", "city", "postal_code", "country", "is_primary"):
    if col not in addr_cols:
        die(f"addresses is missing column {col}")

order_cols = {r[1] for r in conn.execute("PRAGMA table_info(orders)")}
for col in ("address_id", "address_snapshot"):
    if col not in order_cols:
        die(f"orders is missing column {col}")

n = conn.execute("SELECT COUNT(*) FROM orders WHERE address_id IS NULL").fetchone()[0]
if n:
    die(f"{n} orders have NULL address_id")

n = conn.execute(
    "SELECT COUNT(*) FROM orders o JOIN addresses a ON a.id = o.address_id"
    " WHERE a.user_id = o.user_id"
    "   AND a.street || '|' || a.city || '|' || a.postal_code || '|' || a.country"
    "       = o.address_snapshot"
).fetchone()[0]
if n != 900:
    die(f"only {n}/900 orders join to an address matching their snapshot and user")

n = conn.execute(
    "SELECT COUNT(*) FROM users u WHERE"
    " (SELECT COUNT(*) FROM addresses a WHERE a.user_id = u.id AND a.is_primary = 1) != 1"
).fetchone()[0]
if n:
    die(f"{n} users do not have exactly one primary address")

spot = json.load(open(f"{task}/expected/spotchecks.json"))
for want in spot:
    row = conn.execute(
        "SELECT a.user_id, u.name, a.street, a.city, a.postal_code, a.country"
        " FROM orders o JOIN addresses a ON a.id = o.address_id"
        " JOIN users u ON u.id = o.user_id WHERE o.id = ?",
        (want["order_id"],),
    ).fetchone()
    if row is None:
        die(f"spot-check order {want['order_id']}: join returned no row")
    got = dict(zip(("user_id", "user_name", "street", "city", "postal_code", "country"), row))
    for key, val in got.items():
        if want[key] != val:
            die(f"spot-check order {want['order_id']}: {key} = {val!r}, expected {want[key]!r}")

print("structural checks + 10 spot-check joins OK")
PYEOF
[ $? -eq 0 ] || exit 1

# 4. Hidden dao tests against the migrated workspace db.
APP_DB="$PWD/app/db/app.db" PYTHONPATH="$PWD/app" \
    python3 -m pytest -q -p no:cacheprovider "$CHECKER_DIR/hidden" \
    || fail "hidden dao test-suite failed"

echo "CHECK PASS"
exit 0
