#!/usr/bin/env python3
"""Build script for T19-flaky-test-hunt.

- Generates tests/test_stats.py with exact expected literals computed by the
  REFERENCE (sorted-order) semantics. Seed 190019 for the sample values.
- Copies the buggy fixture modules to mutations/originals/.
- Writes expected/tests.manifest (sha256 guard over tests/).
- Verifies flake exposure: under which PYTHONHASHSEED values the buggy
  library fails the labels test and the exact-variance test, and that the
  seeds hardcoded in check.sh's mutation guard expose them; verifies the
  cache bug fails deterministically when the scratch file pre-exists.
"""
import hashlib
import os
import random
import shutil
import subprocess
import sys
import tempfile

TASK = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SEED = 190019
SEEDS = [0, 1, 2, 42, 99, 7, 13, 21, 34, 55]
M1_SEEDS = [0, 1, 42]   # must match check.sh
M3_SEEDS = [0, 1, 42]   # must match check.sh
CACHE_FILE = "/tmp/statlib_cache.tmp"


def make_samples():
    rng = random.Random(SEED)
    mags = [1e-6, 1e-4, 1e-2, 1.0, 1e2, 1e4, 1e6, 1e3, 10.0, 0.1, 1e5, 1e-3]
    samples = []
    for i in range(24):
        name = f"s{i + 1:02d}"
        value = rng.uniform(1.0, 9.999) * mags[i % len(mags)]
        samples.append((name, value))
    return samples


def reference_stats(samples):
    pool = sorted(set((n, float(v)) for n, v in samples))
    total = 0.0
    for _n, v in pool:
        total += v
    mean = total / len(pool)
    acc = 0.0
    for _n, v in pool:
        acc += (v - mean) ** 2
    return mean, acc / len(pool)


def write_test_stats(samples, mean, var):
    lines = ["import math", "", "from statlib import stats", "", "SAMPLES = ["]
    for name, value in samples:
        lines.append(f"    ({name!r}, {value!r}),")
    lines += [
        "]",
        "",
        "",
        "def test_pooled_variance_exact():",
        "    # The library promises deterministic sorted-order accumulation,",
        "    # so this exact float is the contractually correct answer.",
        f"    assert stats.pooled_variance(SAMPLES) == {var!r}",
        "",
        "",
        "def test_pooled_mean_close():",
        f"    assert math.isclose(stats.pooled_mean(SAMPLES), {mean!r}, rel_tol=1e-9)",
        "",
        "",
        "def test_dedup_pairs():",
        "    assert stats.dedup_pairs([('a', 1), ('a', 1.0), ('b', 2)]) == {",
        "        ('a', 1.0), ('b', 2.0)}",
        "",
        "",
        "def test_variance_simple():",
        "    assert stats.pooled_variance(",
        "        [('a', 1.0), ('b', 2.0), ('c', 3.0)]) == 2.0 / 3.0",
        "",
        "",
        "def test_variance_constant():",
        "    assert stats.pooled_variance(",
        "        [('a', 5.0), ('b', 5.0), ('c', 5.0)]) == 0.0",
        "",
    ]
    path = os.path.join(TASK, "fixture", "tests", "test_stats.py")
    with open(path, "w") as fh:
        fh.write("\n".join(lines))
    return path


def write_manifest():
    tests_dir = os.path.join(TASK, "fixture", "tests")
    entries = []
    for root, dirs, files in os.walk(tests_dir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in sorted(files):
            if name.endswith(".pyc"):
                continue
            path = os.path.join(root, name)
            rel = "tests/" + os.path.relpath(path, tests_dir).replace(os.sep, "/")
            h = hashlib.sha256(open(path, "rb").read()).hexdigest()
            entries.append(f"{h}  {rel}")
    entries.sort(key=lambda line: line.split("  ", 1)[1])
    with open(os.path.join(TASK, "expected", "tests.manifest"), "w") as fh:
        fh.write("\n".join(entries) + "\n")
    return entries


def run_pytest(ws, seed, target="tests/"):
    env = dict(os.environ, PYTHONHASHSEED=str(seed))
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", target],
        cwd=ws, env=env, capture_output=True, text=True)
    return proc.returncode


def main():
    samples = make_samples()
    mean, var = reference_stats(samples)
    write_test_stats(samples, mean, var)
    print(f"reference mean={mean!r} variance={var!r}")

    # copies for the mutation guard
    for mod in ("labels.py", "cache.py", "stats.py"):
        shutil.copyfile(os.path.join(TASK, "fixture", "statlib", mod),
                        os.path.join(TASK, "mutations", "originals", mod))
    entries = write_manifest()
    print(f"tests.manifest: {len(entries)} files")

    # --- exposure verification against the BUGGY fixture ---
    tmp = tempfile.mkdtemp()
    ws = os.path.join(tmp, "ws")
    shutil.copytree(os.path.join(TASK, "fixture"), ws)

    labels_fail, stats_fail = [], []
    for seed in SEEDS:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
        if run_pytest(ws, seed, "tests/test_labels.py::test_unique_labels_sorted"):
            labels_fail.append(seed)
        if run_pytest(ws, seed, "tests/test_stats.py::test_pooled_variance_exact"):
            stats_fail.append(seed)
    print(f"buggy labels test fails under seeds: {labels_fail}")
    print(f"buggy exact-variance test fails under seeds: {stats_fail}")
    assert labels_fail, "labels bug never exposed by the seed set"
    assert stats_fail, "stats bug never exposed by the seed set"
    assert any(s in labels_fail for s in M1_SEEDS), \
        f"none of the m1 guard seeds {M1_SEEDS} expose the labels bug"
    assert any(s in stats_fail for s in M3_SEEDS), \
        f"none of the m3 guard seeds {M3_SEEDS} expose the stats bug"

    # cache bug: deterministic failure when the scratch file pre-exists
    with open(CACHE_FILE, "w") as fh:
        fh.write("")
    rc = run_pytest(ws, 0, "tests/test_cache.py::test_cached_summary")
    os.remove(CACHE_FILE)
    assert rc != 0, "cache bug not exposed by a pre-existing scratch file"
    print("cache bug exposed by pre-existing scratch file: OK")

    # cache bug: leftover-file flakiness across two consecutive plain runs
    rc1 = run_pytest(ws, 0, "tests/test_cache.py::test_cached_summary")
    rc2 = run_pytest(ws, 0, "tests/test_cache.py::test_cached_summary")
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    assert rc1 == 0 and rc2 != 0, \
        f"expected pass-then-fail across consecutive runs, got {rc1} then {rc2}"
    print("cache bug flakes across consecutive runs (pass then fail): OK")

    shutil.rmtree(tmp)
    print("T19 build OK")


if __name__ == "__main__":
    main()
