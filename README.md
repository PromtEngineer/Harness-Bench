# Harness-Bench

Harness-Bench is a 40-task coding-agent benchmark designed to measure the
impact of the agent harness itself. In a valid comparison, the model and model
configuration, task revision, runtime, network policy, resource limits, and
time budget stay fixed; only the harness changes.

This is a harness benchmark, not a model leaderboard. Results should only be
compared as harness results when every model-side and execution-side variable
listed above is identical across runs.

## Task layout

Each `TNN-slug/` directory is independently gradeable and contains:

- `prompt.txt`: the exact task prompt supplied to the agent.
- `fixture/`: the only workspace content supplied to the agent.
- `check.sh`: the deterministic external checker, run after the agent exits.
- `checker_guard.sh`: the shared grader-startup hardening copied into each
  independently gradeable task.
- `expected/` and/or `hidden/`: private checker inputs and expected results.
- `solution/`: a reference implementation used for benchmark validation.
- `meta.yaml`: task id, tier, time budget, and design notes.
- `gen/`: optional deterministic build tooling. It is present only where the
  original generator was retained; see `PROVENANCE.md`.

Git cannot represent another repository's `.git/` directory as ordinary
tracked files. T07, T16, and T31 therefore store their clean nested repository
metadata as `fixture.git.tar.gz` beside `fixture/`. Always create an agent
workspace with:

```bash
python3 prepare_fixture.py T07 /path/to/new-workspace
```

For every other task this is equivalent to copying `fixture/`; for those three
tasks it also restores the required Git history. The destination must not
already exist.

The agent must never receive the task directory itself. A run lane receives a
fresh copy of `fixture/` and the contents of `prompt.txt`; `check.sh`,
`expected/`, `hidden/`, `solution/`, sibling tasks, and `TASK_DIR` are grader
state and must not be visible during the agent phase.

Invoke a checker from a disposable fixture copy as
`TASK_DIR=/absolute/path/to/TNN-slug bash /absolute/path/to/TNN-slug/check.sh`.
Each checker captures its own directory and removes `TASK_DIR` before running
submitted code. The startup guard also clears Python/pytest injection variables
and rejects unguarded root-level standard-library shadows or pytest-control
files. The canonical grader `PATH` must not contain the submitted workspace or
`.`.

## Runtime contract

The canonical grader runtime is:

- Ubuntu 24.04 x86-64
- Python 3.12 with pytest 9.x
- Bash 5.x, GNU coreutils, Git 2.43+, curl, and SQLite 3.35+
- no network access for the agent
- UTF-8 locale and `PYTHONDONTWRITEBYTECODE=1`

All harnesses in a comparison must use the same immutable container image,
CPU/memory limits, concurrency, model endpoint, model parameters, and task
timeout. Performance-task results are not comparable across dissimilar hosts.

## Scoring and reporting

Tasks are binary pass/fail. Report all of the following rather than only one
aggregate number:

1. pass count within each tier;
2. macro-average of the four tier pass rates;
3. overall pass count;
4. timeouts and infrastructure failures separately from functional failures;
5. per-task wall time and model/tool usage when available.

The suite is intentionally expert-heavy, so a raw 40-task total gives the
expert band half of the weight. The tier macro-average is the preferred single
summary when comparing harnesses.

## Validation

Run the static audit before every benchmark revision:

```bash
python3 audit_suite.py
```

Run every reference solution through its checker in disposable workspaces:

```bash
python3 audit_suite.py --references
```

Run the targeted checker-regression probes as well:

```bash
python3 audit_suite.py --regressions
```

Freeze the task tree and container image only after all three commands pass.
The machine-readable `--json-out PATH` option is suitable for storing a release
audit alongside the immutable benchmark revision.

## Leakage and revisions

This package contains answers and is suitable for private review, not as the
source delivered to agents. Once a task's solution or expected output has been
published, that exact fixture should be considered contaminated for future
leaderboard claims. New public benchmark rounds should use private regenerated
variants and a new revision id while retaining old variants for reproducibility.
