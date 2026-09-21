# Benchmark revisions

## 2026-08-28-checker-hardening-2

This revision preserves the prompts and intended solutions while tightening
checker determinism and packaging:

- rejects non-finite JSON in T01 and T13 and enforces stricter JSON types in
  T06;
- enforces byte-exact CSV output in T09;
- guards previously unprotected fixture inputs in T05, T06, T09, T11, and
  T12, and guards complete test-file sets in T08;
- verifies real concurrent `asyncio.gather` fan-out in T15;
- pins the exact original Git refs in T16;
- rejects direct and dynamic standard-library regex imports in T38;
- uses monotonic sub-second timing for T27's performance budgets;
- adds a common checker-startup guard, prevents `TASK_DIR` from being inherited
  by submitted processes, disables external pytest plugin autoloading, and
  prevents hidden-test cache artifacts;
- normalizes metadata ids, documents the canonical runtime/scoring/provenance
  contract, removes generated artifacts, and adds `audit_suite.py`.

Validation requirement for this revision: all 40 reference solutions and all
targeted adversarial regression probes must pass the audit suite.
