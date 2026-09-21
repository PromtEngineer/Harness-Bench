# CONFL configuration language — specification

CONFL is a line-based configuration format. This document is the complete
contract; every behavior below is graded. All parse or resolution
failures raise `confl.ConflError`.

## Lines

- `#` starts a comment running to end of line — except inside a quoted
  or raw string.
- Blank lines are ignored. Leading/trailing whitespace is ignored.
- Section header: `[a.b.c]` — a dot path of keys. Sets the current
  section for subsequent entries IN THE SAME FILE. Before any header the
  current section is the root. An invalid path raises
  `bad section header: ...`.
- Include: `include "relative/path.confl"` — processes that file inline.
  Paths are relative to the directory of the INCLUDING file. The
  included file starts at the ROOT section, and the including file's
  current section is restored afterwards. Includes may nest 8 levels
  deep; deeper raises an error. An include cycle raises an error.
- Entry: `key = value` or `key += value`. Keys match
  `[A-Za-z_][A-Za-z0-9_]*`. The full path of an entry is
  `<current section>.<key>`. Anything else is an error.

## Values (single-line)

- int: `-?[0-9]+`
- bool: exactly `true` or `false` (case-sensitive; `True` is an error)
- string: `"..."` with escapes `\n` `\t` `\"` `\\` `\xNN` (exactly two
  hex digits; anything else is a `bad escape`). Strings support
  interpolation: `${a.b.c}` (see below). A `$` not followed by `{` is a
  literal dollar sign.
- raw string: `r"..."` — no escapes, no interpolation, ends at the first
  `"`. Backslashes and `${...}` are literal.
- list: `[v, v, ...]` — values of any kind including nested lists.
  A trailing comma is allowed. `[]` is the empty list.

## Assignment semantics

- `=` on an existing path: LAST assignment wins.
- `+=`: the path must already exist (else `append to undefined key`).
  list += list concatenates. string/raw += string/raw concatenates (the
  result is a string; interpolations in either side still apply). Any
  other combination is an error (`cannot append ... to ...`).

## Interpolation

`${path}` inside a (non-raw) string is replaced by the FINAL resolved
value of that path — after all files are merged and last-wins/append are
applied. Rendering: ints in decimal, bools as `true`/`false`, strings as
their resolved content. Interpolating a list is an error
(`cannot interpolate list`). An unknown path is an error.

Resolution proceeds over keys in FILE ORDER (the order of each key's
first assignment). A reference cycle raises exactly:

    interpolation cycle: <k1> -> <k2> -> ... -> <k1>

where `<k1>` is the first key of the cycle reached during resolution and
the arrow chain follows the references until it returns to `<k1>`
(a self-reference renders as `a -> a`).

## Output shape

`confl.load(path)` returns a nested dict following the dot paths. A path
used both as a scalar and as a section prefix raises
`path conflict: <path>` (the offending path). `confl.dumps_flat(cfg)`
renders leaf values as `<dot.path>=<compact json>` lines — sorted by
path, joined with newlines, no trailing newline; json uses separators
(",", ":") so lists have no spaces; bools render as JSON true/false.

## CLI

`python3 -m confl resolve <file>` prints dumps_flat(load(file)) to
stdout (with a trailing newline from print). On ConflError it prints
`ConflError: <message>` to stderr and exits with code 2. (This CLI
wrapper already exists in confl/__main__.py — implement load/dumps_flat
and it works.)
