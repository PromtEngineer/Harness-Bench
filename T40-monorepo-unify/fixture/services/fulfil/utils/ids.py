"""Reference-id helpers."""

CHECK_MOD = 93


def checksum(payload):
    """Digit checksum over an ASCII payload."""
    total = 0
    for i, ch in enumerate(payload):
        total += (i + 1) * ord(ch)
    return total % CHECK_MOD


def make_id(prefix, n):
    body = f"{prefix}{n:06d}"
    return f"{body}-{checksum(body):02d}"


def verify_id(ref):
    body, _, check = ref.rpartition("-")
    return bool(body) and check == f"{checksum(body):02d}"
