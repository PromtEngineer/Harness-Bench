#!/usr/bin/env python3
"""Crash-safe KV store: append-only WAL with framed, checksummed records."""
import base64
import os
import re
import struct
import sys
import zlib

DATA_DIR = "kvdata"
WAL = os.path.join(DATA_DIR, "wal.log")
MAGIC = 0xA5
KEY_RE = re.compile(r"[A-Za-z0-9_.-]{1,128}$")


def replay():
    """Rebuild state; returns (state, valid_prefix_len)."""
    state = {}
    if not os.path.exists(WAL):
        return state, 0
    with open(WAL, "rb") as fh:
        data = fh.read()
    pos = 0
    while pos < len(data):
        # frame: magic u8 | len u32 | crc32 u32 | payload
        if pos + 9 > len(data) or data[pos] != MAGIC:
            break  # torn/garbage tail: stop replay here
        length, crc = struct.unpack_from("<II", data, pos + 1)
        start = pos + 9
        if start + length > len(data):
            break
        payload = data[start:start + length]
        if (zlib.crc32(payload) & 0xFFFFFFFF) != crc:
            break
        parts = payload.split(b" ", 2)
        if parts[0] == b"S":
            state[parts[1].decode()] = parts[2]
        elif parts[0] == b"D":
            state.pop(parts[1].decode(), None)
        pos = start + length
    return state, pos


def append(fh, payload):
    rec = struct.pack("<BII", MAGIC, len(payload),
                      zlib.crc32(payload) & 0xFFFFFFFF) + payload
    fh.write(rec)
    fh.flush()
    os.fsync(fh.fileno())


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    state, valid = replay()
    # discard any torn/garbage tail so future appends stay recoverable
    if os.path.exists(WAL) and os.path.getsize(WAL) > valid:
        with open(WAL, "r+b") as fh:
            fh.truncate(valid)
            fh.flush()
            os.fsync(fh.fileno())
    wal = open(WAL, "ab")
    out = sys.stdout

    for line in sys.stdin:
        line = line.rstrip("\n")
        if not line:
            continue
        parts = line.split(" ")
        cmd = parts[0]
        try:
            if cmd == "SET" and len(parts) == 3 and KEY_RE.match(parts[1]):
                raw = base64.b64decode(parts[2], validate=True)
                if len(raw) > 65536:
                    print("ERR value too large", file=out, flush=True)
                    continue
                append(wal, b"S " + parts[1].encode() + b" " + parts[2].encode())
                state[parts[1]] = parts[2].encode()
                print("OK", file=out, flush=True)
            elif cmd == "DEL" and len(parts) == 2 and KEY_RE.match(parts[1]):
                append(wal, b"D " + parts[1].encode())
                state.pop(parts[1], None)
                print("OK", file=out, flush=True)
            elif cmd == "GET" and len(parts) == 2:
                v = state.get(parts[1])
                print(f"VAL {v.decode()}" if v is not None else "NONE",
                      file=out, flush=True)
            elif cmd == "DUMPALL" and len(parts) == 1:
                for k in sorted(state):
                    print(f"ROW {k} {state[k].decode()}", file=out, flush=True)
                print("END", file=out, flush=True)
            else:
                print("ERR bad command", file=out, flush=True)
        except Exception as exc:  # malformed b64 etc. must not kill the store
            print(f"ERR {type(exc).__name__}", file=out, flush=True)


if __name__ == "__main__":
    main()
