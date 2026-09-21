#!/usr/bin/env python3
"""T29 crash harness. Run from the workspace root. Exit 0 = pass."""
import base64
import os
import queue
import random
import subprocess
import sys
import threading
import time


def fail(msg):
    print(f"HARNESS FAIL: {msg}")
    sys.exit(1)


class Store:
    def __init__(self):
        self.p = subprocess.Popen([sys.executable, "kvstore.py"],
                                  stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True,
                                  bufsize=1)
        self.q = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        for line in self.p.stdout:
            self.q.put(line.rstrip("\n"))
        self.q.put(None)

    def send(self, line):
        try:
            self.p.stdin.write(line + "\n")
            self.p.stdin.flush()
        except BrokenPipeError:
            fail("store died (broken pipe while sending a command)")

    def recv(self, timeout=20):
        try:
            line = self.q.get(timeout=timeout)
        except queue.Empty:
            fail(f"store unresponsive (>{timeout}s waiting for a reply)")
        if line is None:
            fail("store closed stdout unexpectedly")
        return line

    def cmd(self, line, timeout=20):
        self.send(line)
        return self.recv(timeout)

    def kill(self):
        self.p.kill()
        self.p.wait()

    def quit(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=10)
        except Exception:
            self.p.kill()


def b64(data):
    return base64.b64encode(data).decode()


def dumpall(st):
    st.send("DUMPALL")
    rows = {}
    while True:
        line = st.recv()
        if line == "END":
            return rows
        if not line.startswith("ROW "):
            fail(f"bad DUMPALL line: {line!r}")
        _, k, v = line.split(" ", 2)
        rows[k] = v
    return rows


def check_model(st, model, where):
    rows = dumpall(st)
    want = {k: v for k, v in model.items()}
    if rows != want:
        missing = sorted(set(want) - set(rows))[:3]
        extra = sorted(set(rows) - set(want))[:3]
        diff = [k for k in set(rows) & set(want) if rows[k] != want[k]][:3]
        fail(f"{where}: state mismatch after restart "
             f"(missing={missing} extra={extra} valuediff={diff})")
    keys = sorted(rows)
    # DUMPALL must have been sorted; dumpall() preserved order implicitly?
    # re-check explicitly:
    st.send("DUMPALL")
    order = []
    while True:
        line = st.recv()
        if line == "END":
            break
        order.append(line.split(" ", 2)[1])
    if order != sorted(order):
        fail(f"{where}: DUMPALL not sorted by key")


rng = random.Random(290029)
model = {}

if os.path.exists("kvdata"):
    import shutil
    shutil.rmtree("kvdata")

# ---- phase 1: basic ops + ACK bookkeeping
st = Store()
for i in range(60):
    k = f"key{rng.randint(0, 30):02d}"
    if rng.random() < 0.8:
        v = b64(rng.randbytes(rng.randint(1, 400)))
        if st.cmd(f"SET {k} {v}") != "OK":
            fail("SET did not return OK")
        model[k] = v
    else:
        if st.cmd(f"DEL {k}") != "OK":
            fail("DEL did not return OK")
        model.pop(k, None)
g = st.cmd("GET missing_key")
if g != "NONE":
    fail(f"GET of a missing key returned {g!r}")
some = sorted(model)[0]
if st.cmd(f"GET {some}") != f"VAL {model[some]}":
    fail("GET returned wrong value")
if not st.cmd("BOGUS nonsense").startswith("ERR"):
    fail("unknown command did not return ERR")

# ---- phase 2: SIGKILL immediately after last ACK
st.kill()
st = Store()
check_model(st, model, "phase 2 (kill after ACK)")
print("phase 2 ok: state survived SIGKILL after ACK")

# ---- phase 3: kill mid-write (command sent, ACK never read)
big = b64(rng.randbytes(30000))
st.send(f"SET inflight_{0} {big}")
time.sleep(0.03)
st.kill()
st = Store()
rows = dumpall(st)
without = dict(model)
with_op = dict(model, **{"inflight_0": big})
if rows == without:
    pass
elif rows == with_op:
    model = with_op
else:
    fail("phase 3: state is neither pre-op nor post-op after mid-write kill")
print("phase 3 ok: clean recovery from mid-write kill")

# ---- phase 4: torn tail — append garbage to the newest file in kvdata/
st.kill()
newest, newest_m = None, -1
for root, _, files in os.walk("kvdata"):
    for name in files:
        pth = os.path.join(root, name)
        m = os.path.getmtime(pth)
        if m > newest_m:
            newest, newest_m = pth, m
if newest is None:
    fail("phase 4: kvdata/ contains no files after 60+ acknowledged ops")
with open(newest, "ab") as fh:
    fh.write(b"\x01GARBAGE\xff\xfe")
st = Store()
check_model(st, model, "phase 4 (torn tail)")
print("phase 4 ok: torn trailing garbage tolerated")

# ---- phase 5: more rounds of ops + kills at fixed ACK counts
for round_no, kill_after in ((5, 25), (6, 41)):
    acks = 0
    while acks < kill_after:
        k = f"r{round_no}_{rng.randint(0, 40):02d}"
        if rng.random() < 0.75:
            v = b64(rng.randbytes(rng.randint(1, 2000)))
            if st.cmd(f"SET {k} {v}") != "OK":
                fail(f"phase {round_no}: SET failed")
            model[k] = v
        else:
            if st.cmd(f"DEL {k}") != "OK":
                fail(f"phase {round_no}: DEL failed")
            model.pop(k, None)
        acks += 1
    st.kill()
    st = Store()
    check_model(st, model, f"phase {round_no} (kill after {kill_after} ACKs)")
    print(f"phase {round_no} ok")

# ---- phase 6: big value + throughput sanity
huge = b64(rng.randbytes(60000))
if st.cmd("SET bigval " + huge) != "OK":
    fail("SET of a 60KB value failed")
model["bigval"] = huge
t0 = time.monotonic()
for i in range(200):
    v = b64(rng.randbytes(50))
    if st.cmd(f"SET perf{i:03d} {v}", timeout=30) != "OK":
        fail("perf SET failed")
    model[f"perf{i:03d}"] = v
dt = time.monotonic() - t0
if dt > 60:
    fail(f"200 SETs took {dt:.0f}s (limit 60s)")
st.kill()
st = Store()
check_model(st, model, "phase 6 (final)")
if st.cmd("GET bigval") != f"VAL {huge}":
    fail("big value corrupted after restart")
st.quit()
print(f"phase 6 ok: 200 SETs in {dt:.1f}s, big value intact")
print("HARNESS PASS")
