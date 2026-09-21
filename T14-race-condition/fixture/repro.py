#!/usr/bin/env python3
"""Seeded stress reproducer for the jobqueue result-loss bug.

Runs 200 jobs on 8 workers with a barrier-synchronized start and verifies
that every job's result was recorded exactly right and the completion
counter agrees. Exits 0 on success, 1 on any discrepancy.

DO NOT MODIFY THIS FILE. The checker verifies its sha256.
"""
import random
import sys

# Force frequent interpreter thread switches so scheduling interleavings
# are exercised aggressively and reproducibly across machines.
sys.setswitchinterval(1e-6)

from jobqueue.queue import Job, JobQueue  # noqa: E402
from jobqueue.worker import WorkerPool  # noqa: E402

NUM_JOBS = 200
NUM_WORKERS = 8
SEED = 4242
MIN_DISTINCT_WORKERS = 3


def expected_value(seed):
    """Mirror of Job.run for verification."""
    acc = 0
    for k in range(4000):
        acc = (acc * 31 + seed * (k + 1)) % 1000003
    return acc


def main():
    rng = random.Random(SEED)
    order = list(range(NUM_JOBS))
    rng.shuffle(order)
    jobs = [Job("job-%03d" % i, i) for i in order]

    q = JobQueue(jobs)
    pool = WorkerPool(q, NUM_WORKERS, synchronized_start=True)
    pool.run()

    errors = []
    results = q.results
    if len(results) != NUM_JOBS:
        errors.append("lost results: recorded %d of %d" % (len(results), NUM_JOBS))
    if q.completed_count != NUM_JOBS:
        errors.append("lost completions: counted %d of %d"
                      % (q.completed_count, NUM_JOBS))
    for i in range(NUM_JOBS):
        jid = "job-%03d" % i
        if jid in results and results[jid][0] != expected_value(i):
            errors.append("wrong value for %s" % jid)
    distinct = {wname for (_, wname) in results.values()}
    if len(distinct) < MIN_DISTINCT_WORKERS:
        errors.append("only %d distinct workers processed jobs (need >= %d); "
                      "work must stay parallel" % (len(distinct), MIN_DISTINCT_WORKERS))

    if errors:
        for e in errors:
            print("REPRO FAIL:", e)
        return 1
    print("REPRO PASS: %d jobs, %d workers, counter=%d"
          % (NUM_JOBS, len(distinct), q.completed_count))
    return 0


if __name__ == "__main__":
    sys.exit(main())
