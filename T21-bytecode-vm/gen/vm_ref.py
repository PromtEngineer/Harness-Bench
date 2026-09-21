#!/usr/bin/env python3
"""Reference SVM-1 interpreter. Usage: python3 vm.py <program.svm>"""
import struct
import sys


def wrap(x):
    return ((x + 0x80000000) & 0xFFFFFFFF) - 0x80000000


def main():
    data = open(sys.argv[1], "rb").read()
    if data[:4] != b"SVM1":
        print("VM ERROR: bad magic")
        sys.exit(3)
    code_len = struct.unpack_from("<H", data, 4)[0]
    code = data[6:6 + code_len]
    off = 6 + code_len
    nstr = struct.unpack_from("<H", data, off)[0]
    off += 2
    strings = []
    for _ in range(nstr):
        slen = struct.unpack_from("<H", data, off)[0]
        off += 2
        strings.append(data[off:off + slen].decode("utf-8"))
        off += slen

    stack, calls, globs = [], [], [0] * 256
    pc = 0

    def err(reason):
        print(f"VM ERROR: {reason}")
        sys.exit(3)

    def pop():
        if not stack:
            err("stack underflow")
        return stack.pop()

    while True:
        if pc < 0 or pc >= len(code):
            err("pc out of range")
        op = code[pc]
        pc += 1

        def operand(fmt, size):
            nonlocal pc
            if pc + size > len(code):
                err("pc out of range")
            val = struct.unpack_from(fmt, code, pc)[0]
            pc += size
            return val

        if op == 0x01:
            stack.append(operand("<i", 4))
        elif op == 0x02:
            v = pop(); stack.append(v); stack.append(v)
        elif op == 0x03:
            b = pop(); a = pop(); stack.append(b); stack.append(a)
        elif op == 0x04:
            pop()
        elif op in (0x10, 0x11, 0x12, 0x13, 0x14):
            b = pop(); a = pop()
            if op == 0x10:
                r = a + b
            elif op == 0x11:
                r = a - b
            elif op == 0x12:
                r = a * b
            else:
                if b == 0:
                    err("division by zero")
                q = abs(a) // abs(b)
                if (a < 0) != (b < 0):
                    q = -q
                r = q if op == 0x13 else a - q * b
            stack.append(wrap(r))
        elif op in (0x20, 0x21, 0x22):
            b = pop(); a = pop()
            r = {0x20: a == b, 0x21: a < b, 0x22: a > b}[op]
            stack.append(1 if r else 0)
        elif op == 0x30:
            rel = operand("<h", 2)
            pc = pc + rel
        elif op == 0x31:
            rel = operand("<h", 2)
            if pop() == 0:
                pc = pc + rel
        elif op == 0x40:
            stack.append(globs[operand("<B", 1)])
        elif op == 0x41:
            globs[operand("<B", 1)] = pop()
        elif op == 0x50:
            rel = operand("<h", 2)
            calls.append(pc)
            pc = pc + rel
        elif op == 0x51:
            if not calls:
                err("call stack underflow")
            pc = calls.pop()
        elif op == 0x60:
            print(pop())
        elif op == 0x61:
            idx = operand("<H", 2)
            if idx >= len(strings):
                err("bad string index")
            print(strings[idx])
        elif op == 0xFF:
            sys.exit(0)
        else:
            err(f"unknown opcode 0x{op:02x}")


if __name__ == "__main__":
    main()
