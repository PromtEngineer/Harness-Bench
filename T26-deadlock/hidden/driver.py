#!/usr/bin/env python3
"""T26 hidden concurrency driver. Run from the workspace root. Exit 0 = pass."""
import random
import sys
import threading

sys.path.insert(0, ".")
from bankcore import AccountBank


def fail(msg):
    print(f"DRIVER FAIL: {msg}")
    # os._exit: stuck non-daemon-safe threads must not block the exit
    import os
    os._exit(1)


# ---- phase 0: the debug_hook instrumentation must still fire
bank = AccountBank({"a": 100, "b": 100})
points = []
bank.debug_hook = points.append
bank.transfer("a", "b", 10)
bank.debug_hook = None
if "transfer-first-lock" not in points:
    fail("debug_hook point 'transfer-first-lock' was removed from transfer()")
if "transfer-mid" not in points:
    fail("debug_hook point 'transfer-mid' was removed from transfer()")
print("phase 0 ok: instrumentation intact")

# ---- phase 1: forced opposite-transfer interleaving must not deadlock
bank = AccountBank({"alice": 1000, "bob": 1000})
barrier = threading.Barrier(2)


def hook1(point):
    if point == "transfer-first-lock":
        try:
            barrier.wait(timeout=4)
        except threading.BrokenBarrierError:
            pass


bank.debug_hook = hook1
t1 = threading.Thread(target=bank.transfer, args=("alice", "bob", 100),
                      daemon=True)
t2 = threading.Thread(target=bank.transfer, args=("bob", "alice", 250),
                      daemon=True)
t1.start(); t2.start()
t1.join(timeout=12); t2.join(timeout=12)
if t1.is_alive() or t2.is_alive():
    fail("DEADLOCK: opposite transfers stuck at the forced interleaving")
bank.debug_hook = None
if bank.balance("alice") != 1150 or bank.balance("bob") != 850:
    fail(f"wrong balances after transfers: {bank.audit()}")
print("phase 1 ok: no transfer/transfer deadlock")

# ---- phase 2: audit vs in-flight transfer -> block or consistent, never torn
bank = AccountBank({"a": 500, "b": 500, "c": 500})
reached = threading.Event()
release = threading.Event()


def hook2(point):
    if point == "transfer-mid":
        reached.set()
        release.wait(timeout=15)


bank.debug_hook = hook2
tx = threading.Thread(target=bank.transfer, args=("a", "b", 200), daemon=True)
tx.start()
if not reached.wait(timeout=10):
    fail("transfer never reached the transfer-mid hook")

audit_result = {}
audit_done = threading.Event()


def do_audit():
    audit_result["snap"] = bank.audit()
    audit_done.set()


ta = threading.Thread(target=do_audit, daemon=True)
ta.start()
if audit_done.wait(timeout=1.5):
    snap = audit_result["snap"]
    if sum(snap.values()) != 1500:
        fail(f"audit returned a TORN snapshot mid-transfer: {snap} "
             f"(sum {sum(snap.values())}, expected 1500)")
release.set()
tx.join(timeout=10)
if tx.is_alive():
    fail("transfer stuck after release")
if not audit_done.wait(timeout=10):
    fail("DEADLOCK: audit stuck against an in-flight transfer")
if sum(audit_result["snap"].values()) != 1500:
    fail(f"audit snapshot sum wrong: {audit_result['snap']}")
bank.debug_hook = None
if bank.audit() != {"a": 300, "b": 700, "c": 500}:
    fail(f"final balances wrong: {bank.audit()}")
print("phase 2 ok: audit is deadlock-free and consistent")

# ---- phase 3: concurrent hammer, final state must equal serial replay
accts = ["a", "b", "c", "d", "e", "f"]
bank = AccountBank({k: 10_000 for k in accts})
plans = []
for i in range(8):
    rng = random.Random(2600 + i)
    plans.append([(rng.choice(accts), rng.choice(accts), rng.randint(1, 500))
                  for _ in range(300)])
    plans[-1] = [(s, d, m) for s, d, m in plans[-1] if s != d]

stop_audit = threading.Event()
audit_fail = []


def auditor():
    while not stop_audit.is_set():
        snap = bank.audit()
        if sum(snap.values()) != 60_000:
            audit_fail.append(sum(snap.values()))
            return


threads = [threading.Thread(target=lambda p=p: [bank.transfer(*op) for op in p],
                            daemon=True) for p in plans]
au = threading.Thread(target=auditor, daemon=True)
au.start()
for t in threads:
    t.start()
for t in threads:
    t.join(timeout=60)
if any(t.is_alive() for t in threads):
    fail("DEADLOCK: hammer transfers did not finish in 60s")
stop_audit.set()
au.join(timeout=10)
if audit_fail:
    fail(f"auditor observed torn sum {audit_fail[0]} during the hammer")

expect = {k: 10_000 for k in accts}
for plan in plans:
    for s, d, m in plan:
        expect[s] -= m
        expect[d] += m
final = bank.audit()
if final != expect:
    fail(f"final state diverges from serial replay: {final} != {expect}")
print("phase 3 ok: hammer matches serial replay, auditor never torn")

print("DRIVER PASS")
