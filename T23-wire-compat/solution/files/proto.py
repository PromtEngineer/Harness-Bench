"""TLVP/1 + TLVP/2 wire codec. See PROTOCOL.md and CHANGES.md."""
import struct
import zlib


class FrameError(Exception):
    pass


TYPE_NAMES = {1: "hello", 2: "data", 3: "ack", 4: "batch"}
TYPE_IDS = {v: k for k, v in TYPE_NAMES.items()}


def _checksum_v1(body):
    return sum(body) % 65521


def _tlv(tag, value, v2=False):
    if len(value) <= 254:
        return bytes([tag, len(value)]) + value
    if not v2:
        raise FrameError(f"TLV value too long for tag 0x{tag:02x}")
    if len(value) > 65535:
        raise FrameError(f"TLV value too long for tag 0x{tag:02x}")
    return bytes([tag, 0xFF]) + struct.pack("<H", len(value)) + value


def _parse_tlvs(body, v2=False):
    out = []
    pos = 0
    while pos < len(body):
        if pos + 2 > len(body):
            raise FrameError("truncated TLV header")
        tag, length = body[pos], body[pos + 1]
        pos += 2
        if v2 and length == 0xFF:
            if pos + 2 > len(body):
                raise FrameError("truncated TLV extended length")
            length = struct.unpack_from("<H", body, pos)[0]
            pos += 2
        if pos + length > len(body):
            raise FrameError("truncated TLV value")
        out.append((tag, body[pos:pos + length]))
        pos += length
    return out


def _encode_body(msg, version):
    t = msg["type"]
    v2 = version == 2
    if t == "hello":
        return (_tlv(0x01, msg["node"].encode("utf-8"), v2)
                + _tlv(0x02, struct.pack("<I", msg["ver"]), v2))
    if t == "data":
        return (_tlv(0x10, struct.pack("<I", msg["seq"]), v2)
                + _tlv(0x11, bytes.fromhex(msg["payload_hex"]), v2))
    if t == "ack":
        return _tlv(0x10, struct.pack("<I", msg["seq"]), v2)
    if t == "batch":
        if not v2:
            raise FrameError("batch requires version 2")
        body = b""
        for item in msg["items"]:
            frame = encode(dict(item, type="data"), version=2)
            body += _tlv(0x20, frame, v2=True)
        return body
    raise FrameError(f"unknown message type {t!r}")


def _decode_body(type_id, body, v2, stream_id=None):
    name = TYPE_NAMES.get(type_id)
    if name is None or (name == "batch" and not v2):
        raise FrameError(f"unknown frame type {type_id}")
    msg = {"type": name}
    if v2:
        msg["stream_id"] = stream_id
    for tag, value in _parse_tlvs(body, v2):
        if name == "hello" and tag == 0x01:
            msg["node"] = value.decode("utf-8")
        elif name == "hello" and tag == 0x02:
            msg["ver"] = struct.unpack("<I", value)[0]
        elif name in ("data", "ack") and tag == 0x10:
            msg["seq"] = struct.unpack("<I", value)[0]
        elif name == "data" and tag == 0x11:
            msg["payload_hex"] = value.hex()
        elif name == "batch" and tag == 0x20:
            nested, consumed = decode(value)
            if consumed != len(value) or nested.get("type") != "data":
                raise FrameError("bad nested frame in batch")
            msg.setdefault("items", []).append(nested)
        elif v2:
            continue  # forward compat: skip unknown tags
        else:
            raise FrameError(f"unknown TLV tag 0x{tag:02x} for {name}")
    if name == "batch":
        msg.setdefault("items", [])
    return msg


def encode(msg, version=1):
    """Encode a message dict into a TLVP/1 or TLVP/2 frame."""
    if version not in (1, 2):
        raise FrameError(f"unsupported version {version}")
    body = _encode_body(msg, version)
    if version == 1:
        header = struct.pack("<BBH", TYPE_IDS[msg["type"]], 0, len(body))
        return header + body + struct.pack("<H", _checksum_v1(body))
    header = struct.pack("<BBHI", TYPE_IDS[msg["type"]], 0x01, len(body),
                         msg["stream_id"])
    return header + body + struct.pack("<I", zlib.crc32(body) & 0xFFFFFFFF)


def decode(buf):
    """Decode one frame from the head of buf -> (msg, bytes_consumed)."""
    if len(buf) < 4:
        raise FrameError("truncated header")
    type_id, flags, body_len = struct.unpack_from("<BBH", buf, 0)
    if flags & ~0x01:
        raise FrameError(f"reserved flag bits set: 0x{flags:02x}")
    v2 = bool(flags & 0x01)
    if not v2:
        if len(buf) < 4 + body_len + 2:
            raise FrameError("truncated frame")
        body = buf[4:4 + body_len]
        stored = struct.unpack_from("<H", buf, 4 + body_len)[0]
        if stored != _checksum_v1(body):
            raise FrameError("checksum mismatch")
        return _decode_body(type_id, body, False), 4 + body_len + 2
    if len(buf) < 8 + body_len + 4:
        raise FrameError("truncated frame")
    stream_id = struct.unpack_from("<I", buf, 4)[0]
    body = buf[8:8 + body_len]
    stored = struct.unpack_from("<I", buf, 8 + body_len)[0]
    if stored != (zlib.crc32(body) & 0xFFFFFFFF):
        raise FrameError("checksum mismatch")
    return _decode_body(type_id, body, True, stream_id), 8 + body_len + 4
