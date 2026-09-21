# Utility unification — decisions record (2026-08-04 platform sync)

Context: billing, fulfil and notify each grew their own copies of four
utility modules (money, dates, ids, retry) under services/<name>/utils/.
The copies have drifted. We are unifying them into ONE shared package.
This document is the complete and authoritative record of what was
decided; implement it exactly.

## D1. Shared package location and import style

The canonical modules live in a new top-level package `corelib/`
(corelib/money.py, corelib/dates.py, corelib/ids.py, corelib/retry.py).
Services import them as `from corelib import money` (or
`from corelib import dates, ids, money` style). After the migration
every services/<name>/utils/ directory is DELETED — no shims, no
re-export stubs, no copies left behind.

## D2. money — MERGED decision (read carefully)

Two independent choices landed here:
- Rounding: billing's HALF-UP rounding is canonical (round_cents(0.5)
  -> 1, round_cents(-0.5) -> -1, away from zero on the .5 boundary).
  Finance signed off on billing's numbers; the bankers-rounding and
  truncation variants both misreport regulated invoices.
- Currency symbols: notify's richer SYMBOLS table is canonical (it has
  the unicode EUR/GBP signs and JPY, which customer-facing surfaces
  already rely on). billing's plain table is retired.

So corelib/money.py = billing's round_cents + notify's SYMBOLS, with
the shared format_money body. ROUND_MODE reports "half_up".

## D3. dates — fulfil is canonical

Ops standardized region-wide on day-first dates long ago; despite ISO
being the company style guide elsewhere, the DATE CONTRACT for these
three services is fulfil's: parse_date/format_date use DD/MM/YYYY.
billing's ISO variant is retired — note this CHANGES billing's
due_date() output format, and that is intended. add_business_days is
identical everywhere; keep it.

## D4. ids — billing is canonical

The checksum modulus unifies on billing's CHECK_MOD = 97 (largest
2-digit prime; best error detection). fulfil (93) and notify (89) ids
in flight will re-verify against 97 — accepted breakage, do not build
compatibility fallbacks.

## D5. retry — fulfil is canonical

Reliability chose the gentler curve: BACKOFF_BASE = 1.5 with
MAX_ATTEMPTS = 5. The 2.0 variants are retired.

## D6. Scope guardrails

- Public service APIs (services/<name>/api.py function names and
  signatures) do not change; only their behavior shifts where the
  decisions above imply it.
- tests/ is frozen (byte-checked); it only asserts variant-independent
  behavior, so it must stay green through the migration.
- No service may keep a private copy of any decided function.
