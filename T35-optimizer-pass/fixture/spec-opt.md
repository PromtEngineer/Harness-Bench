# Optimization pass — requirements

Implement minic/optimize.py: optimize(ir) -> ir. The IR op set is
documented in minic/codegen.py; execution semantics (INCLUDING
truncating division) live in minic/interp.py — read both.

Only optimize.py may be modified (everything else is sha256-guarded;
you may add helper modules under minic/ if you like).

## Required transforms (applied to a fixpoint)

1. CONSTANT FOLDING: PUSH a, PUSH b, <ADD|SUB|MUL|DIV|MOD|comparison>
   -> PUSH result. Arithmetic is exact integer math; DIV/MOD must fold
   EXACTLY like interp.py's trunc_div/trunc_mod (truncation toward
   zero — Python's // is NOT that for negatives). NEVER fold a division
   or modulo by literal zero — leave those ops in place so the runtime
   error is preserved. Also fold PUSH a, NEG -> PUSH -a.
2. ALGEBRAIC IDENTITIES (after folding): the sequences
   PUSH 0, ADD    PUSH 0, SUB    PUSH 1, MUL    PUSH 1, DIV
   are dropped entirely.
3. CONSTANT BRANCHES: PUSH c, JZ L  ->  JMP L when c == 0, deleted
   entirely when c != 0.
4. UNREACHABLE CODE: after an unconditional JMP, every op up to (not
   including) the next LABEL is removed.
5. DEAD STORES: a STORE to a variable that is never LOADed anywhere in
   the program becomes POP (the operand must still be discarded!).
   Then PUSH c, POP pairs are removed.

## Grading

For each grading program:
- SEMANTICS: run.py output with --opt must equal the output without.
- SIZE: the optimized instruction count must be <= a per-program
  budget (reference optimizer count + 10% + 2). Budgets for the three
  shipped examples are listed in examples/BUDGETS.txt; check yours with
  `python3 compile.py examples/ex1.me --opt | wc -l`.

The hidden grading programs exercise every transform above, including
negative-operand division folding and division-by-zero preservation.
