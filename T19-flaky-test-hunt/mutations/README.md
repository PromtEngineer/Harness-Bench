# Mutation guard for T19-flaky-test-hunt

Each `m{1,2,3}.py` re-introduces ONE of the original fixture bugs into a
scratch copy of the (fixed) workspace, and the checker then requires the
unchanged, hash-guarded test suite to FAIL. This proves the tests still
bite, i.e. the agent fixed the library rather than papering over the
symptoms (and did not neutralize the tests indirectly, e.g. via a
conftest.py that monkey-patches the library).

- m1.py: reverts `statlib/labels.py` to the original buggy file
  (unique_labels returns set-iteration order instead of sorted).
- m2.py: reverts `statlib/cache.py` to the original buggy file
  (fixed /tmp/statlib_cache.tmp path, open(..., "x"), no cleanup).
  The checker pre-creates /tmp/statlib_cache.tmp so a single suite run
  exposes the bug deterministically.
- m3.py: reverts `statlib/stats.py` to the original buggy file
  (float accumulation in set-iteration order).

The pristine buggy files live in `originals/` (byte-identical copies of
the shipped fixture modules).

The mutations target the REFERENCE solution's file layout: the same
modules and public function names as the fixture (`statlib/labels.py:
unique_labels`, `statlib/cache.py:cached_summary`, `statlib/stats.py:
pooled_mean`/`pooled_variance`). Each script verifies that layout before
mutating and FAILS LOUDLY (nonzero exit, clear message) if the agent's
solution diverged structurally -- in that case the checker fails the run,
which is the documented, intended strictness.

m1/m3 are exercised under several PYTHONHASHSEED values (a set-order bug
is not guaranteed to change observable order under one specific seed on
every CPython version); the suite must fail under at least one of them.
