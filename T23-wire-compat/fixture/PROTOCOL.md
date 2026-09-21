# TLVP/1 wire protocol

Frame layout (little-endian):

    u8  type      1=HELLO 2=DATA 3=ACK
    u8  flags     always 0 in TLVP/1
    u16 body_len
    ..  body      a sequence of TLVs: u8 tag, u8 len, len bytes
    u16 checksum  sum of body bytes mod 65521

TLV tags: HELLO: 0x01 node (utf-8 string), 0x02 ver (u32 LE).
DATA: 0x10 seq (u32 LE), 0x11 payload (raw bytes).
ACK: 0x10 seq (u32 LE).

An unknown TLV tag, a truncated frame, or a checksum mismatch raises
FrameError. decode() consumes exactly one frame from the head of the
buffer and returns (message_dict, bytes_consumed).

Message dict forms (these exact keys):
  {"type": "hello", "node": str, "ver": int}
  {"type": "data", "seq": int, "payload_hex": str}
  {"type": "ack", "seq": int}
