# Schema v2 migration specification

This document is the authoritative spec for migrating `db/app.db` from the
v1 schema to the v2 schema, and for the v2 behavior of `dao.py`.

## v1 schema (current)

```sql
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
```

`address_snapshot` is the string `street|city|postal_code|country`
(pipe-separated, no extra whitespace) captured at order time. In this
dataset every order's snapshot exactly matches its user's current v1
address columns.

## v2 target schema

### 1. New table `addresses`

```sql
CREATE TABLE addresses (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    street      TEXT NOT NULL,
    city        TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    country     TEXT NOT NULL,
    is_primary  INTEGER NOT NULL DEFAULT 1
);
```

Populate it with exactly one row per user, carrying that user's v1
address columns verbatim, with `is_primary = 1`.

### 2. `users` loses its address columns

After migration `users` must contain the columns `id`, `name`, `email`
and NOT contain `street`, `city`, `postal_code` or `country`. All id,
name and email values are preserved unchanged.

### 3. `orders` gains `address_id`

Add a column `address_id INTEGER REFERENCES addresses(id)` to `orders`.

Backfill rule: for each order, `address_id` must be set to the id of the
`addresses` row that (a) belongs to `orders.user_id` and (b) whose
`street || '|' || city || '|' || postal_code || '|' || country` equals
`orders.address_snapshot`. Every snapshot matches by construction; if
any order cannot be matched this way, the migration must exit with a
nonzero status. After migration no order may have a NULL `address_id`.

The `address_snapshot` column is kept, unchanged, for auditing.

### 4. Invariants after migration

- Row counts preserved: `users` and `orders` keep their original counts;
  `addresses` has exactly one row per user.
- `PRAGMA foreign_key_check` reports no violations.
- No data values are altered other than as described above.

## migrate.py contract

- Invoked as `python3 migrate.py db/app.db` with the `app/` directory as
  the working directory (the database path is argv[1]).
- Transforms the database in place, v1 -> v2, in a single run.
- Exit code 0 on success, nonzero on any failure.

## dao.py v2 contract

- `connect(db_path)` keeps working as before.
- `get_user_with_address(conn, user_id)` returns a dict with keys
  `id`, `name`, `email`, `street`, `city`, `postal_code`, `country`,
  where the address now comes from the user's `addresses` row with
  `is_primary = 1` (joined, not read from `users`). Returns `None` when
  no such user exists.
- `get_order_shipping(conn, order_id)` returns a dict with keys
  `order_id`, `user_name`, `street`, `city`, `postal_code`, `country`,
  where the address comes from the `addresses` row referenced by
  `orders.address_id` (NOT parsed from the snapshot string, NOT read via
  the user). Returns `None` when no such order exists.
