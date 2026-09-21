# TLVP/2 protocol changes (to implement)

TLVP/2 extends TLVP/1. The wire is version-negotiated per frame via the
flags byte; both versions coexist on one connection.

## Framing

- flags bit 0 (0x01) set = the frame is TLVP/2. All other flag bits stay
  reserved-zero in both versions.
- A TLVP/2 frame carries an extra u32 LE `stream_id` between `body_len`
  and the body:

      u8 type | u8 flags | u16 body_len | u32 stream_id | body | u32 crc

- The TLVP/2 trailer is the CRC-32 (zlib polynomial, i.e. Python
  `zlib.crc32`) of the body, stored as u32 LE. TLVP/1 frames keep the
  u16 mod-65521 sum. body_len still counts ONLY the body bytes.

## Extended TLV lengths

In TLVP/2 bodies only: a TLV length byte of 0xFF means the real length
follows as a u16 LE (use it for any value 255 bytes or longer; values
up to 254 bytes keep the single-byte form). TLVP/1 bodies never use
extended lengths.

## New message type: BATCH (type 4, TLVP/2 only)

A BATCH body is a sequence of TLVs with tag 0x20, each value holding one
complete serialized TLVP/2 DATA frame (nested full frame, including its
own header, stream_id, and CRC). Message dict form:

    {"type": "batch", "stream_id": int,
     "items": [<data message dict with "stream_id">, ...]}

Decoding a BATCH decodes every nested DATA frame (validating each nested
CRC); a nested frame that is not a TLVP/2 DATA frame raises FrameError.

## Forward compatibility

Decoding a TLVP/2 frame: unknown TLV tags are SKIPPED silently (forward
compat). TLVP/1 decoding keeps its strict unknown-tag FrameError.

## API contract

- encode(msg, version=1) -> bytes. version=1 must produce byte-identical
  output to the current codec for hello/data/ack (the golden transcripts
  in golden/ pin this). version=2 produces TLVP/2 frames; every v2
  message dict carries "stream_id"; encoding a batch requires version=2
  (encoding it with version=1 raises FrameError).
- decode(buf) -> (msg, consumed). Auto-detects the version from flags
  bit 0. Decoded v2 messages include "stream_id". Any non-zero reserved
  flag bit raises FrameError.
- Exception type and module layout stay as-is (tlvp.FrameError,
  tlvp.encode, tlvp.decode).
