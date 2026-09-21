#!/usr/bin/env python3
"""Apply an op script to a document and print a digest of the results.

Usage: python3 driver.py <doc.txt> <script.ops>

Op script format, one op per line:
    I <pos> <text>     insert (text = the rest of the line, letters/digits)
    D <pos> <n>        delete
    S <pos> <n>        read a slice (its content feeds the digest)

The digest folds in every S result and the final document, so ops cannot
be skipped or reordered.
"""
import hashlib
import sys


def main():
    from edbuf import Buffer
    doc_path, ops_path = sys.argv[1], sys.argv[2]
    with open(doc_path) as fh:
        buf = Buffer(fh.read())
    h = hashlib.sha256()
    with open(ops_path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            op, rest = line.split(" ", 1)
            if op == "I":
                pos, text = rest.split(" ", 1)
                buf.insert(int(pos), text)
            elif op == "D":
                pos, n = rest.split(" ")
                buf.delete(int(pos), int(n))
            elif op == "S":
                pos, n = rest.split(" ")
                h.update(buf.get_slice(int(pos), int(n)).encode())
            else:
                raise ValueError(f"bad op line: {line!r}")
    h.update(buf.get_slice(0, 1 << 62).encode())
    print(f"DIGEST {h.hexdigest()}")


if __name__ == "__main__":
    main()
