# Build scheduler — specification

Input file: {"resources": {"cpu": C, "mem": M}, "makespan_budget": B,
"jobs": [{"id", "duration", "cpu", "mem", "deps": [ids...]}, ...]}

Produce a schedule {"start": {job_id: start_tick}} such that:

1. Every job gets exactly one integer start tick >= 0.
2. A job starts only after ALL its deps have finished
   (start[j] >= start[d] + duration[d]).
3. At every tick, the sum of cpu (and mem) of RUNNING jobs — a job runs
   in the half-open interval [start, start+duration) — never exceeds
   the caps.
4. The makespan (max over jobs of start+duration) is <= makespan_budget.

The budget is set ~25% above what a decent critical-path list scheduler
achieves, so scheduling everything serially fails by a wide margin, and
a greedy scheduler that ignores job priorities may or may not squeak in
— the recommended approach is classic list scheduling with a
longest-path-to-sink priority:

- priority(j) = duration(j) + max over dependents of priority
  (critical path length through j)
- event-driven loop: at each time point, start ready jobs in priority
  order while they fit in the remaining cpu/mem; advance time to the
  next job completion.

## CLI

    python3 scheduler.py <jobs.json> <schedule.json>

Your scheduler must be a general algorithm: the grader runs it on this
workspace's jobs.json AND on hidden job sets from the same generator
(same caps, different DAGs), each within a 60s timeout.
