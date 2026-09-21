"""TLVP/1 wire codec. See PROTOCOL.md for the frame layout."""
import struct


class FrameError(Exception):
    pass


TYPE_NAMES = {1: "hello", 2: "data", 3: "ack"}
TYPE_IDS = {v: k for k, v in TYPE_NAMES.items()}


def _checksum_v1(body):
    """Sum of body bytes mod 65521."""
    return sum(body) % 65521


def _tlv(tag, value):
    if len(value) > 255:
        raise FrameError(f"TLV value too long for tag 0x{tag:02x}")
    return bytes([tag, len(value)]) + value


def _parse_tlvs(body):
    out = []
    pos = 0
    while pos < len(body):
        if pos + 2 > len(body):
            raise FrameError("truncated TLV header")
        tag, length = body[pos], body[pos + 1]
        pos += 2
        if pos + length > len(body):
            raise FrameError("truncated TLV value")
        out.append((tag, body[pos:pos + length]))
        pos += length
    return out


def _encode_body(msg):
    t = msg["type"]
    if t == "hello":
        return (_tlv(0x01, msg["node"].encode("utf-8"))
                + _tlv(0x02, struct.pack("<I", msg["ver"])))
    if t == "data":
        return (_tlv(0x10, struct.pack("<I", msg["seq"]))
                + _tlv(0x11, bytes.fromhex(msg["payload_hex"])))
    if t == "ack":
        return _tlv(0x10, struct.pack("<I", msg["seq"]))
    raise FrameError(f"unknown message type {t!r}")


def _decode_body(type_id, body):
    fields = _parse_tlvs(body)
    name = TYPE_NAMES.get(type_id)
    if name is None:
        raise FrameError(f"unknown frame type {type_id}")
    msg = {"type": name}
    for tag, value in fields:
        if name == "hello" and tag == 0x01:
            msg["node"] = value.decode("utf-8")
        elif name == "hello" and tag == 0x02:
            msg["ver"] = struct.unpack("<I", value)[0]
        elif name in ("data", "ack") and tag == 0x10:
            msg["seq"] = struct.unpack("<I", value)[0]
        elif name == "data" and tag == 0x11:
            msg["payload_hex"] = value.hex()
        else:
            raise FrameError(f"unknown TLV tag 0x{tag:02x} for {name}")
    return msg


def encode(msg):
    """Encode a message dict into a TLVP/1 frame."""
    body = _encode_body(msg)
    header = struct.pack("<BBH", TYPE_IDS[msg["type"]], 0, len(body))
    return header + body + struct.pack("<H", _checksum_v1(body))


def decode(buf):
    """Decode one frame from the head of buf -> (msg, bytes_consumed)."""
    if len(buf) < 4:
        raise FrameError("truncated header")
    type_id, flags, body_len = struct.unpack_from("<BBH", buf, 0)
    if len(buf) < 4 + body_len + 2:
        raise FrameError("truncated frame")
    body = buf[4:4 + body_len]
    stored = struct.unpack_from("<H", buf, 4 + body_len)[0]
    if stored != _checksum_v1(body):
        raise FrameError("checksum mismatch")
    return _decode_body(type_id, body), 4 + body_len + 2
