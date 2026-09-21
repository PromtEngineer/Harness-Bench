# Fixture provenance

The benchmark currently contains two provenance classes.

## Retained deterministic generators

The following tasks retain build or generator code in `gen/`:

`T01`, `T04`, `T06`, `T07`, `T08`, `T09`, `T10`, `T12`, `T13`, `T16`,
`T17`, `T18`, `T19`, `T20`, and `T21`.

Their generator code and reference solutions should be treated as the source
of truth and must be exercised when changing those fixtures.

## Original generator not retained

The following tasks are fully gradeable but their original construction code
was not retained in this package:

`T02`, `T03`, `T05`, `T11`, `T14`, `T15`, and `T22` through `T40`.

For these tasks, the frozen fixture, specification, hidden vectors/tests,
expected artifacts, checker, and passing reference solution are the available
provenance record. Claims in `meta.yaml` about build-time cross-checks describe
the original authoring process but cannot be independently regenerated from
this package.

No placeholder generators have been added: a script that merely copies the
current fixture would create false reproducibility. Before producing rotated
private variants of these tasks, add a real deterministic builder that:

1. accepts an explicit seed;
2. creates the fixture and hidden cases from scratch;
3. derives expected results independently from the reference solution where
   practical;
4. asserts that the pristine fixture fails;
5. asserts that the reference solution passes;
6. asserts that documented naive or sabotaged implementations fail.

Until then, these tasks should be versioned as frozen fixtures rather than
described as regenerable variants.
