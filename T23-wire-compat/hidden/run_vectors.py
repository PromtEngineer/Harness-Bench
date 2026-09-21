#!/usr/bin/env python3
"""T23 hidden vector runner. argv: <workspace> <task_dir>. Exit 0 = pass."""
import importlib.util
import json
import os
import sys

ws, task_dir = sys.argv[1], sys.argv[2]
sys.path.insert(0, ws)
import tlvp  # noqa: E402

def fail(msg):
    print(f"VECTOR FAIL: {msg}")
    sys.exit(1)

# 1. v1 goldens: byte-exact both directions, from the TASK_DIR copies.
gdir = os.path.join(task_dir, "hidden", "golden")
names = sorted(n[:-4] for n in os.listdir(gdir) if n.endswith(".hex"))
for name in names:
    frame = bytes.fromhex(open(os.path.join(gdir, name + ".hex")).read().strip())
    msg = json.load(open(os.path.join(gdir, name + ".json")))
    try:
        enc = tlvp.encode(msg, version=1)
    except TypeError:
        fail(f"{name}: encode() does not accept version=1")
    if enc != frame:
        fail(f"{name}: encode(msg, version=1) is not byte-identical to the golden")
    if tlvp.encode(msg) != frame:
        fail(f"{name}: encode(msg) default no longer matches TLVP/1 golden")
    dec, consumed = tlvp.decode(frame)
    if dec != msg or consumed != len(frame):
        fail(f"{name}: decode mismatch: {dec!r}")

vec = json.load(open(os.path.join(task_dir, "hidden", "v2_vectors.json")))

# 2. v2 roundtrips: byte-exact encode and exact decode.
for i, entry in enumerate(vec["roundtrip"]):
    msg, frame = entry["msg"], bytes.fromhex(entry["hex"])
    enc = tlvp.encode(msg, version=2)
    if enc != frame:
        fail(f"v2 roundtrip {i}: encode not byte-identical "
             f"(type {msg['type']}, got {enc.hex()[:60]}...)")
    dec, consumed = tlvp.decode(frame)
    if dec != msg or consumed != len(frame):
        fail(f"v2 roundtrip {i}: decode mismatch: {dec!r}")

# 3. special behaviors.
sp = vec["special"]
dec, _ = tlvp.decode(bytes.fromhex(sp["skip_unknown_v2"]["hex"]))
if dec != sp["skip_unknown_v2"]["want"]:
    fail(f"v2 unknown TLV must be skipped silently, got {dec!r}")
for key in ("error_unknown_v1", "error_bad_crc", "error_truncated",
            "error_reserved_flags"):
    try:
        tlvp.decode(bytes.fromhex(sp[key]["hex"]))
        fail(f"{key}: decode should raise tlvp.FrameError")
    except tlvp.FrameError:
        pass
    except Exception as exc:
        fail(f"{key}: raised {type(exc).__name__} instead of tlvp.FrameError")

# 4. batch requires v2 at encode time.
try:
    tlvp.encode({"type": "batch", "stream_id": 1, "items": []}, version=1)
    fail("encoding a batch with version=1 must raise FrameError")
except tlvp.FrameError:
    pass

# 5. concatenated stream: v1 and v2 frames interleaved, consumed exactly.
stream = b"".join([
    bytes.fromhex(open(os.path.join(gdir, names[0] + ".hex")).read().strip()),
    bytes.fromhex(vec["roundtrip"][1]["hex"]),
    bytes.fromhex(open(os.path.join(gdir, names[2] + ".hex")).read().strip()),
    bytes.fromhex(vec["roundtrip"][6]["hex"]),
])
count = 0
while stream:
    msg, consumed = tlvp.decode(stream)
    if consumed <= 0:
        fail("decode returned non-positive consumed")
    stream = stream[consumed:]
    count += 1
if count != 4:
    fail(f"interleaved stream decoded {count} frames, expected 4")

print("ALL VECTORS PASS")
