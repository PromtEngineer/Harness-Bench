#!/usr/bin/env python3
"""Deterministic backtracking version resolver. See SPEC.md.

Usage: python3 resolver.py <index.json> <requirements.json> <lockfile.json>
"""
import json
import sys


def parse_ver(s):
    return tuple(int(x) for x in s.split("."))


def satisfies(ver, rng):
    """ver: tuple. rng: range string like '>=1.2.0 <2.0.0' or '*'."""
    for part in rng.split():
        if part == "*":
            continue
        for op in (">=", "<=", ">", "<", "="):
            if part.startswith(op):
                bound = parse_ver(part[len(op):])
                ok = {">=": ver >= bound, "<=": ver <= bound,
                      ">": ver > bound, "<": ver < bound,
                      "=": ver == bound}[op]
                if not ok:
                    return False
                break
        else:
            raise ValueError(f"bad range part: {part}")
    return True


def solve(index, requirements):
    # constraints: pkg -> list of (source, range); assignment: pkg -> version str
    root_constraints = {}
    for pkg, rng in requirements.items():
        root_constraints.setdefault(pkg, []).append(("<root>", rng))

    def candidates(pkg, constraints, forbidden):
        vers = sorted(index.get(pkg, {}), key=parse_ver, reverse=True)
        out = []
        for v in vers:
            if (pkg, v) in forbidden:
                continue
            if all(satisfies(parse_ver(v), rng)
                   for _, rng in constraints.get(pkg, [])):
                out.append(v)
        return out

    def backtrack(assignment, constraints, decisions):
        unresolved = sorted(p for p in constraints if p not in assignment)
        if not unresolved:
            return dict(assignment)
        pkg = unresolved[0]
        forbidden = set()
        while True:
            cands = candidates(pkg, constraints, forbidden)
            if not cands:
                return None
            v = cands[0]
            new_constraints = {p: list(c) for p, c in constraints.items()}
            deps = index[pkg][v].get("deps", {})
            for dpkg, drng in sorted(deps.items()):
                new_constraints.setdefault(dpkg, []).append((f"{pkg}@{v}", drng))
            assignment[pkg] = v
            # dead end if any ALREADY-ASSIGNED package violates a range
            conflict = any(
                not satisfies(parse_ver(assignment[q]), rng)
                for q, cons in new_constraints.items() if q in assignment
                for _, rng in cons)
            result = None if conflict else backtrack(
                assignment, new_constraints, decisions + [(pkg, v)])
            if result is not None:
                return result
            del assignment[pkg]
            forbidden.add((pkg, v))

    result = backtrack({}, root_constraints, [])
    if result is None:
        return {"solvable": False}
    return {"solvable": True,
            "resolved": {p: result[p] for p in sorted(result)}}


def main():
    index = json.load(open(sys.argv[1]))
    reqs = json.load(open(sys.argv[2]))
    lock = solve(index, reqs)
    with open(sys.argv[3], "w") as fh:
        json.dump(lock, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("solvable" if lock["solvable"] else "unsolvable")


if __name__ == "__main__":
    main()
