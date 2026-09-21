# Version resolver — specification

Input: an index (index.json) mapping package -> version -> {"deps":
{package: range}}, and a requirements file mapping package -> range
(the roots). Output: a lockfile selecting EXACTLY ONE version per
needed package satisfying every constraint, computed by the EXACT
algorithm below (the output is compared verbatim).

## Versions and ranges

Versions are x.y.z with integer components, compared componentwise.
A range is a SPACE-SEPARATED CONJUNCTION of comparators applied to a
version: >=x.y.z  <=x.y.z  >x.y.z  <x.y.z  =x.y.z, or `*` (anything).
Example: ">=1.2.0 <2.0.0".

## Resolution algorithm (normative — implement exactly this)

State: a partial assignment {pkg: version} plus a constraint set
{pkg: [ranges]} seeded from the requirements.

1. Let unresolved = constrained packages with no assigned version.
   If empty, resolution succeeded.
2. Pick the ALPHABETICALLY FIRST unresolved package P.
3. Candidates(P) = versions of P in the index that satisfy ALL current
   ranges on P and are not forbidden at this decision point, sorted
   HIGHEST FIRST.
4. Assign the first candidate v and add every dep range of P@v to the
   constraint set. If any ALREADY-ASSIGNED package's version now
   violates one of its ranges, this choice is a DEAD END: undo it,
   forbid it at this decision point, and try P's next candidate.
   Otherwise recurse. (Constraints added by an assignment are removed
   again whenever that assignment is undone.)
5. If a package has no candidates, BACKTRACK: undo the most recent
   assignment, forbid that (package, version) at its decision point,
   and continue with its next candidate.
6. If the root decision runs out of candidates: unsolvable.

This is plain chronological (DFS) backtracking; forbidden sets are
per-decision-point, not global. Highest-first + alphabetical-first make
the answer unique.

## Lockfile format

Solvable:   {"solvable": true, "resolved": {pkg: version, ...}}  (keys sorted)
Unsolvable: {"solvable": false}

## CLI

    python3 resolver.py <index.json> <requirements.json> <out-lockfile.json>

Writes the lockfile as JSON (any whitespace/indent, content compared
semantically) and prints "solvable" or "unsolvable".
