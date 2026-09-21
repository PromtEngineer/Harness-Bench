# Spreadsheet evaluator — specification

Input: a TSV file, each line `<CELL>\t<content>`. CELL is a column of
uppercase letters (A..Z, AA, AB, ... — bijective base 26) plus a row
number >= 1. Content is either an integer literal (possibly negative)
or a formula starting with `=`. Cells not present in the file are
EMPTY. Inputs are well-formed; you do not need to handle syntax errors.

## Formula grammar

    cmp    := add (( = | <> | < | > | <= | >= ) add)*   -> 1 or 0
    add    := mul (( + | - ) mul)*
    mul    := unary (( * | / | % ) unary)*
    unary  := - unary | atom
    atom   := INT | CELL | FN | ( cmp )
    FN     := SUM(range) | MIN(range) | MAX(range) | COUNT(range)
            | IF(cmp, cmp, cmp)
    range  := CELL : CELL      (opposite corners of a rectangle,
                                in any corner order)

Whitespace between tokens is allowed. All values are integers.
`/` TRUNCATES TOWARD ZERO (-7/2 = -3) and `%` takes the dividend's
sign (-7%2 = -1) — C semantics, not Python's.

## Errors

Values can be errors: #DIV/0! (division or modulo by zero), #REF!
(a DIRECT cell reference to an empty cell), #CYCLE! (see below).
Operators and SUM/MIN/MAX propagate errors; when several are present
the SEVERITY order #CYCLE! > #REF! > #DIV/0! picks the result.
Unary minus propagates. Comparisons propagate the same way.

## Ranges

- SUM/MIN/MAX evaluate the PRESENT (non-empty) cells in the rectangle;
  empty positions are skipped, NOT errors. If any evaluated cell is an
  error, the worst error propagates. SUM of zero present cells = 0;
  MIN/MAX of zero present cells = #REF!.
- COUNT returns the number of present cells in the rectangle WITHOUT
  evaluating them (error cells still count; COUNT never propagates).

## IF is lazy (this is where the design earns its keep)

IF(cond, a, b): evaluate cond. If cond is an error, the result is that
error. If cond != 0, evaluate and return ONLY a; otherwise ONLY b. The
untaken branch is NEVER evaluated — a reference to an empty cell or
even a reference CYCLE in the untaken branch does not affect the
result.

## Cycles

Evaluation of a cell that (dynamically, through the references it
actually evaluates) reaches itself yields #CYCLE! at the point of
re-entry; anything that consumes it propagates it (multiplying by zero
does NOT rescue an error). Cache evaluated cells; every cell involved
in a cycle reports #CYCLE!.

## Depth

Reference chains can be THOUSANDS of cells deep (the grader includes a
5000-cell chain). Mind Python's default recursion limit: raise it or
evaluate iteratively.

## Output

    python3 calc.py <sheet.tsv> <out.tsv>

out.tsv: one line per PRESENT cell — `<CELL>\t<value-or-error>` —
sorted by row number, then column index (A before B before ... before
AA). End with a single trailing newline. Compared byte-for-byte.
