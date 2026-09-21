#!/usr/bin/env python3
"""Independent reference decoder for SLPK v2 (written against format.md,
deliberately NOT sharing code with generate.py). Prints the summary JSON
for a given .slpk file to stdout.
"""
import json
import struct
import sys
import zlib


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def take(self, n: int) -> bytes:
        if self.pos + n > len(self.data):
            raise ValueError(f"truncated file at offset {self.pos} (need {n} bytes)")
        chunk = self.data[self.pos:self.pos + n]
        self.pos += n
        return chunk

    def u8(self) -> int:
        return self.take(1)[0]

    def u16(self) -> int:
        return struct.unpack("<H", self.take(2))[0]

    def u32(self) -> int:
        return struct.unpack("<I", self.take(4))[0]

    def varint(self) -> int:
        result = 0
        shift = 0
        while True:
            byte = self.u8()
            result |= (byte & 0x7F) << shift
            if not byte & 0x80:
                return result
            shift += 7


def decode(data: bytes) -> dict:
    r = Reader(data)
    if r.take(8) != b"SLPKv2\x00\x01":
        raise ValueError("bad magic")
    record_count = r.u16()

    records = []
    for _ in range(record_count):
        rid = r.u32()
        flags = r.u8()
        if flags & 0x02:
            raise ValueError(f"record {rid}: compressed bit set (invalid in v2)")
        length = r.varint()
        payload = r.take(length)
        stored_crc = r.u32()
        tag_id = r.u16()
        crc_ok = (zlib.crc32(payload) & 0xFFFFFFFF) == stored_crc
        records.append((rid, flags, length, crc_ok, tag_id))

    entry_count = r.u16()
    names = {}
    for _ in range(entry_count):
        tid = r.u16()
        name_len = r.u8()
        names[tid] = r.take(name_len).decode("ascii")
    if r.pos != len(data):
        raise ValueError(f"{len(data) - r.pos} trailing bytes after the string table")

    deleted = [rec for rec in records if rec[1] & 0x01]
    crc_failures = sorted(rec[0] for rec in records if not rec[3])
    active = [rec for rec in records if not rec[1] & 0x01 and rec[3]]
    tag_counts = {}
    for rec in active:
        name = names[rec[4]]
        tag_counts[name] = tag_counts.get(name, 0) + 1
    top5 = sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    return {
        "record_count": record_count,
        "active_count": len(active),
        "deleted_count": len(deleted),
        "crc_failures": crc_failures,
        "total_payload_bytes": sum(rec[2] for rec in active),
        "top5_tags": [[name, count] for name, count in top5],
    }


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "records.slpk"
    with open(path, "rb") as fh:
        summary = decode(fh.read())
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
