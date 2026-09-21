# SVM-1 virtual machine specification

SVM-1 is a little-endian stack virtual machine operating on signed 32-bit
integers. This document is the complete and authoritative contract.

## Program file format

| offset | size | field |
|---|---|---|
| 0 | 4 | magic, the ASCII bytes `SVM1` |
| 4 | 2 | `code_len`, u16 LE, length of the code segment in bytes |
| 6 | code_len | code segment |
| 6+code_len | 2 | `nstrings`, u16 LE, number of string table entries |
| ... | | per entry: u16 LE byte length, then that many UTF-8 bytes |

There are no trailing bytes after the string table. A file whose first four
bytes are not `SVM1` is invalid (error `bad magic`).

## Machine state

- **Operand stack** of signed 32-bit integers (empty at start).
- **Call stack** of return addresses (empty at start).
- **Globals**: 256 slots, indexed 0-255, all initialized to 0.
- **pc**: byte offset into the code segment, starts at 0.

## Integer semantics (read carefully)

- Every arithmetic result is wrapped to signed 32-bit two's complement:
  `wrap(x) = ((x + 2^31) mod 2^32) - 2^31`. Example: 2147483647 + 1 =
  -2147483648. Note that -2147483648 * -1 wraps to -2147483648.
- `DIV` truncates toward zero: -7 DIV 2 = -3 (NOT -4).
- `MOD` is defined as `a - trunc(a/b)*b`; its sign follows the dividend:
  -7 MOD 2 = -1 (NOT 1).
- `DIV` or `MOD` with divisor 0 is the runtime error `division by zero`.

## Opcodes

Operands are encoded immediately after the opcode byte. `rel16` is a signed
16-bit LE offset relative to the address of the instruction that FOLLOWS the
operand (i.e. new_pc = address_after_operand + rel).

| byte | name | operand | effect |
|---|---|---|---|
| 0x01 | PUSH | i32 LE | push immediate |
| 0x02 | DUP | | duplicate top |
| 0x03 | SWAP | | swap top two |
| 0x04 | POP | | discard top |
| 0x10 | ADD | | pop b, pop a, push wrap(a+b) |
| 0x11 | SUB | | pop b, pop a, push wrap(a-b) |
| 0x12 | MUL | | pop b, pop a, push wrap(a*b) |
| 0x13 | DIV | | pop b, pop a, push wrap(trunc(a/b)) |
| 0x14 | MOD | | pop b, pop a, push wrap(a - trunc(a/b)*b) |
| 0x20 | EQ | | pop b, pop a, push 1 if a==b else 0 |
| 0x21 | LT | | pop b, pop a, push 1 if a<b else 0 (signed) |
| 0x22 | GT | | pop b, pop a, push 1 if a>b else 0 (signed) |
| 0x30 | JMP | rel16 | jump |
| 0x31 | JZ | rel16 | pop v, jump if v == 0 |
| 0x40 | LOAD | u8 | push globals[slot] |
| 0x41 | STORE | u8 | pop into globals[slot] |
| 0x50 | CALL | rel16 | push address_after_operand onto call stack, jump |
| 0x51 | RET | | pop call stack into pc |
| 0x60 | PRINTI | | pop v, print v in decimal followed by a newline |
| 0x61 | PRINTS | u16 LE | print string table entry followed by a newline |
| 0xFF | HALT | | stop, exit code 0 |

## Errors

When a runtime error occurs the VM prints exactly one line to stdout:

    VM ERROR: <reason>

and exits with code 3. Output printed before the error line is kept. The
exact reason strings are:

- `bad magic`
- `stack underflow`         (POP/DUP/SWAP/arith/PRINTI on an empty stack)
- `call stack underflow`    (RET with an empty call stack)
- `division by zero`
- `pc out of range`         (pc outside [0, code_len) at fetch time, or an
                             operand that runs past the end of code)
- `unknown opcode 0xNN`     (NN = two lowercase hex digits)
- `bad string index`        (PRINTS index >= nstrings)

Error checks happen in instruction order: operands are fetched before values
are popped (a truncated operand reports `pc out of range` even if the stack
is also empty). For binary ops, b is popped before a.

## Execution

Fetch the byte at pc; if pc is outside the code segment, error
`pc out of range`. Decode, advance pc past opcode and operand, execute.
The only clean exit is HALT (exit code 0).
