# bankcore

Thread-safe account store. Known production issues to fix:

1. Opposite concurrent transfers (A->B and B->A) can deadlock.
   `python3 stress.py` reproduces it deterministically (it hangs / prints
   DEADLOCK). After the fix it must print OK.
2. `audit()` runs concurrently with transfers. It must never deadlock
   against them and must never return an inconsistent snapshot (a
   snapshot in which a debit has been applied but its matching credit
   has not: the total sum must always equal the true total).

Constraints:
- Public API is frozen: AccountBank(balances), accounts(), balance(),
  transfer(src, dst, amount), audit(), debug_hook.
- The debug_hook instrumentation and both call points
  ("transfer-first-lock", "transfer-mid") must remain: the grader uses
  them to force interleavings. "transfer-first-lock" fires after the
  first lock acquisition in transfer, "transfer-mid" between the debit
  and the credit.
- Real locking is required; keep the code correct under true concurrency.
