# rx — regex engine specification

Implement rx.py in the workspace root exposing exactly:

    class PatternError(Exception)
    def fullmatch(pattern: str, text: str) -> bool
    def search(pattern: str, text: str) -> tuple[int, int] | None

## Syntax (the complete supported set)

- literal characters
- `.`     any single character
- `[...]` character class: chars, ranges `a-z` (inclusive, error if
          reversed like `z-a`), leading `^` negates. `]` as the FIRST
          member is a literal. `-` first or last is a literal. Class
          escapes: `\\` `\]` `\d` `\w` `\s`. `[]` (empty) is an error.
- `\d` digits 0-9, `\w` [A-Za-z0-9_], `\s` whitespace
  (space, \t, \n, \r, \f, \v), and `\X` where X is any of . * + ? | (
  ) [ ] \ for a literal X. Any other escape is an error.
- quantifiers `*` `+` `?` on the PRECEDING atom (a quantifier directly
  following a quantifier, e.g. `a**`, is an error; a quantifier with
  nothing to repeat, e.g. `*a` or `(|*)`, is an error)
- concatenation; alternation `|` (lowest precedence); grouping `(...)`
  (non-capturing). Empty branches are allowed: `(a|)` matches "a" or "".

No anchors, no capture semantics, no backreferences.

## Semantics

- fullmatch: the ENTIRE text must match.
- search: the LEFTMOST match wins; among matches at the leftmost start,
  the LONGEST extent wins. Empty matches count: search("a*", "bbb") ->
  (0, 0); search("x|xy", "axyz") -> (1, 3) — note LONGEST, which is NOT
  what a backtracking engine like Python's `re` returns for that
  pattern. Return None only if no start position matches.
- Malformed patterns raise PatternError (unbalanced parens, dangling or
  doubled quantifiers, bad/trailing escapes, unterminated or empty
  classes, reversed ranges).

## Restrictions

Python 3 stdlib only, and the `re`/`regex` modules are BANNED — the
grader AST-scans every .py file in the workspace for those imports.
Build a real engine (Thompson NFA + simulation is the classic route;
naive exponential backtracking will also time out on the grader's
pathological inputs like (a?){25}-style nesting... which you can't
write in this syntax, but a{n} equivalents via repetition exist).

## Worked examples

    fullmatch("ab*c", "abbbc")            -> True
    fullmatch("ab*c", "ac")               -> True
    fullmatch("a(b|cd)+e", "acdbcde")     -> True
    fullmatch("[a-f0-9]+", "deadbeef99")  -> True
    fullmatch("[^aeiou]+", "xyz")         -> True
    fullmatch("a.c", "a\nc")              -> True   (. matches newline)
    search("x|xy", "axyz")                -> (1, 3)
    search("a*", "bbb")                   -> (0, 0)
    search("\d+", "order 6502 shipped")  -> (6, 10)
    search("z+", "aaa")                   -> None
    PatternError: "(ab", "a**", "*a", "[z-a]", "[]", "a\", "\q"
