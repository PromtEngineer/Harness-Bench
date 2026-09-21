# SLPK v2 binary log format -- specification

This document fully specifies the fictional "SLPK v2" binary log format.
All multi-byte integers are LITTLE-ENDIAN and unsigned unless stated
otherwise. There is no padding or alignment anywhere: every structure
immediately follows the previous one.

## 1. Header (10 bytes)

| offset | size | field        | contents                                   |
|-------:|-----:|--------------|--------------------------------------------|
| 0      | 8    | magic        | ASCII `SLPKv2` followed by bytes 0x00 0x01 |
| 8      | 2    | record_count | u16 LE: number of records in the file      |

A decoder MUST reject a file whose first 8 bytes are not exactly
`53 4C 50 4B 76 32 00 01`.

## 2. Records

Exactly `record_count` records follow the header, back to back. Each
record is laid out as:

| field       | size     | contents                                        |
|-------------|----------|-------------------------------------------------|
| record_id   | 4        | u32 LE. Unique per file.                        |
| flags       | 1        | u8 bit field, see below.                        |
| payload_len | varint   | unsigned LEB128 (see section 4)                 |
| payload     | variable | exactly `payload_len` raw bytes                 |
| payload_crc | 4        | u32 LE: CRC-32 of the payload bytes             |
| tag_id      | 2        | u16 LE: references the footer string table      |

### flags

| bit | mask | meaning                                                     |
|----:|-----:|-------------------------------------------------------------|
| 0   | 0x01 | deleted: the record is logically deleted                    |
| 1   | 0x02 | compressed: NOT USED in v2. Always 0. A decoder MUST reject |
|     |      | any record with this bit set.                               |
| 2-7 |      | reserved, always 0 in v2                                    |

Deleted records still carry a full payload, CRC and tag_id.

### payload_crc

CRC-32 as defined by IEEE 802.3 (the polynomial used by zip/PNG; identical
to Python's `zlib.crc32(payload) & 0xFFFFFFFF`), computed over the payload
bytes only. A record whose stored `payload_crc` does not equal the CRC-32
computed from its payload is CORRUPT. Corruption affects only that record's
validity; the record's framing (lengths/offsets) is always intact, so
decoding continues normally with the next record.

## 3. Footer: tag string table

Immediately after the last record:

| field       | size | contents                          |
|-------------|-----:|-----------------------------------|
| entry_count | 2    | u16 LE: number of entries         |

Then `entry_count` entries, back to back, each:

| field   | size     | contents                         |
|---------|----------|----------------------------------|
| tag_id  | 2        | u16 LE                           |
| name_len| 1        | u8: length of the name in bytes  |
| name    | name_len | ASCII tag name                   |

Entries are NOT sorted. Every `tag_id` used by a record appears exactly
once in the table. The file ends immediately after the last entry; a
decoder MUST treat trailing bytes as an error.

## 4. Unsigned LEB128 varint

An unsigned integer is encoded 7 bits at a time, least-significant group
first. Each output byte carries 7 value bits in its low bits; the high bit
(0x80) is the continuation flag: 1 means "more bytes follow", 0 marks the
final byte.

Decoding algorithm:

    result = 0; shift = 0
    loop:
        byte = next_byte()
        result |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0: stop
        shift += 7

Examples: 0 -> `00`; 127 -> `7F`; 128 -> `80 01`; 300 -> `AC 02`;
16384 -> `80 80 01`. Encoders emit the minimal number of bytes.
