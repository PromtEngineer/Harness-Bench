#!/usr/bin/env bash
# Reference solution for T20-binary-protocol. cwd = workspace copy.
# Writes a decoder into the workspace and runs it to produce summary.json.
set -euo pipefail

cat > decode_slpk.py <<'PYEOF'
#!/usr/bin/env python3
"""Decode data/records.slpk per format.md and write summary.json."""
import json
import struct
import zlib


class Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def take(self, n):
        if self.pos + n > len(self.data):
            raise ValueError(f"truncated file at offset {self.pos}")
        chunk = self.data[self.pos:self.pos + n]
        self.pos += n
        return chunk

    def u8(self):
        return self.take(1)[0]

    def u16(self):
        return struct.unpack("<H", self.take(2))[0]

    def u32(self):
        return struct.unpack("<I", self.take(4))[0]

    def varint(self):
        result = 0
        shift = 0
        while True:
            byte = self.u8()
            result |= (byte & 0x7F) << shift
            if not byte & 0x80:
                return result
            shift += 7


def main():
    with open("data/records.slpk", "rb") as fh:
        r = Reader(fh.read())
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
    if r.pos != len(r.data):
        raise ValueError("trailing bytes after the string table")

    active = [rec for rec in records if not rec[1] & 0x01 and rec[3]]
    tag_counts = {}
    for rec in active:
        name = names[rec[4]]
        tag_counts[name] = tag_counts.get(name, 0) + 1
    top5 = sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    summary = {
        "record_count": record_count,
        "active_count": len(active),
        "deleted_count": sum(1 for rec in records if rec[1] & 0x01),
        "crc_failures": sorted(rec[0] for rec in records if not rec[3]),
        "total_payload_bytes": sum(rec[2] for rec in active),
        "top5_tags": [[name, count] for name, count in top5],
    }
    with open("summary.json", "w") as fh:
        json.dump(summary, fh, indent=2)
        fh.write("\n")


if __name__ == "__main__":
    main()
PYEOF

python3 decode_slpk.py
echo "T20 reference solution applied (decode_slpk.py written, summary.json produced)"
