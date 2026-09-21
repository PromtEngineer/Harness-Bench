"""In-memory account store with per-account locking.

debug_hook is REQUIRED test instrumentation: when set to a callable, it is
invoked with a point name at the two marked sync points. The grader uses it
to force specific thread interleavings — keep both call sites in place.
"""
import threading


class AccountBank:
    def __init__(self, balances):
        self._balances = dict(balances)
        self._locks = {acct: threading.Lock() for acct in self._balances}
        self.debug_hook = None

    def _hook(self, point):
        hook = self.debug_hook
        if hook is not None:
            hook(point)

    def accounts(self):
        return sorted(self._balances)

    def balance(self, acct):
        with self._locks[acct]:
            return self._balances[acct]

    def transfer(self, src, dst, amount):
        """Move amount from src to dst. Negative balances are allowed.

        Locks are always taken in sorted account order to prevent
        deadlock between opposite transfers.
        """
        first, second = sorted((src, dst))
        self._locks[first].acquire()
        self._hook("transfer-first-lock")
        self._locks[second].acquire()
        try:
            self._balances[src] -= amount
            self._hook("transfer-mid")
            self._balances[dst] += amount
        finally:
            self._locks[second].release()
            self._locks[first].release()

    def audit(self):
        """Return a CONSISTENT snapshot of all balances."""
        held = []
        try:
            for acct in sorted(self._balances):
                self._locks[acct].acquire()
                held.append(acct)
            return dict(self._balances)
        finally:
            for acct in reversed(held):
                self._locks[acct].release()
