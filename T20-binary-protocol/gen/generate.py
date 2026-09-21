#!/usr/bin/env python3
"""Generator for T20-binary-protocol (seed 200020).

Writes data/records.slpk (500 records; exactly 37 with the deleted flag,
exactly 2 non-deleted records with a corrupted stored CRC) and prints the
ground-truth summary JSON (from generation-time bookkeeping, NOT from
re-decoding the file) to stdout.
"""
import json
import random
import struct
import sys
import zlib

SEED = 200020
N_RECORDS = 500
N_DELETED = 37
N_CORRUPT = 2

TAG_TABLE = [
    (3, "auth"), (7, "billing"), (11, "cache"), (14, "db"),
    (19, "export"), (23, "import"), (28, "net"), (31, "parse"),
    (37, "render"), (41, "sync"), (45, "ui"), (52, "worker"),
]
TAG_WEIGHTS = [12, 9, 8, 7, 7, 6, 5, 5, 4, 3, 3, 2]


def leb128(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def main(out_path: str) -> None:
    rng = random.Random(SEED)
    tag_ids = [t[0] for t in TAG_TABLE]
    tag_names = dict(TAG_TABLE)

    record_ids = rng.sample(range(1, 2**32), N_RECORDS)
    deleted_idx = set(rng.sample(range(N_RECORDS), N_DELETED))
    corrupt_idx = set(rng.sample(sorted(set(range(N_RECORDS)) - deleted_idx),
                                 N_CORRUPT))

    blob = bytearray()
    blob += b"SLPKv2\x00\x01"
    blob += struct.pack("<H", N_RECORDS)

    active_bytes = 0
    tag_counts = {}
    crc_failures = []
    for i in range(N_RECORDS):
        rid = record_ids[i]
        flags = 0x01 if i in deleted_idx else 0x00
        length = rng.randrange(5, 600)
        payload = rng.randbytes(length)
        crc = zlib.crc32(payload) & 0xFFFFFFFF
        stored_crc = crc
        if i in corrupt_idx:
            stored_crc = crc ^ 0x5A5A5A5A
            crc_failures.append(rid)
        tag = rng.choices(tag_ids, weights=TAG_WEIGHTS)[0]
        blob += struct.pack("<I", rid)
        blob.append(flags)
        blob += leb128(length)
        blob += payload
        blob += struct.pack("<I", stored_crc)
        blob += struct.pack("<H", tag)
        if flags == 0 and stored_crc == crc:
            active_bytes += length
            name = tag_names[tag]
            tag_counts[name] = tag_counts.get(name, 0) + 1

    footer_entries = list(TAG_TABLE)
    rng.shuffle(footer_entries)
    blob += struct.pack("<H", len(footer_entries))
    for tid, name in footer_entries:
        raw = name.encode("ascii")
        blob += struct.pack("<H", tid) + bytes([len(raw)]) + raw

    with open(out_path, "wb") as fh:
        fh.write(blob)

    top5 = sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    truth = {
        "record_count": N_RECORDS,
        "active_count": N_RECORDS - N_DELETED - N_CORRUPT,
        "deleted_count": N_DELETED,
        "crc_failures": sorted(crc_failures),
        "total_payload_bytes": active_bytes,
        "top5_tags": [[name, count] for name, count in top5],
    }
    json.dump(truth, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "records.slpk")
