#!/usr/bin/env python3
"""Deadlock reproducer. Currently HANGS; after the fix it must print OK.

Forces the interleaving: two threads run opposite transfers and both pause
at "transfer-first-lock" (via debug_hook) before taking their second lock.
"""
import threading
import sys

from bankcore import AccountBank

bank = AccountBank({"alice": 1000, "bob": 1000})
barrier = threading.Barrier(2)


def hook(point):
    if point == "transfer-first-lock":
        try:
            barrier.wait(timeout=5)
        except threading.BrokenBarrierError:
            pass


bank.debug_hook = hook
t1 = threading.Thread(target=bank.transfer, args=("alice", "bob", 100), daemon=True)
t2 = threading.Thread(target=bank.transfer, args=("bob", "alice", 250), daemon=True)
t1.start(); t2.start()
t1.join(timeout=10); t2.join(timeout=10)
if t1.is_alive() or t2.is_alive():
    print("DEADLOCK: transfers stuck")
    sys.exit(1)
assert bank.balance("alice") == 1150 and bank.balance("bob") == 850
print("OK")
