"""Job and JobQueue: shared state for the worker pool.

JobQueue hands out pending jobs to workers and collects their results.
Multiple Worker threads call get_next_job / record_result / mark_complete
concurrently.
"""
import threading


class Job:
    """A unit of work. `run()` derives a deterministic value from the seed."""

    __slots__ = ("job_id", "seed")

    def __init__(self, job_id, seed):
        self.job_id = job_id
        self.seed = seed

    def run(self):
        acc = 0
        for k in range(4000):
            acc = (acc * 31 + self.seed * (k + 1)) % 1000003
        return acc


class JobQueue:
    """Dispatches jobs and aggregates results from many worker threads."""

    def __init__(self, jobs):
        self._pending = list(jobs)
        self._total = len(self._pending)
        self._dispatch_lock = threading.Lock()
        self._results = {}
        self._completed_count = 0
        self._completion_log = []

    def get_next_job(self):
        """Pop the next pending job, or None when the queue is drained."""
        with self._dispatch_lock:
            if not self._pending:
                return None
            return self._pending.pop(0)

    def record_result(self, job_id, value, worker_name):
        """Publish a finished job's value into the shared results map.

        Builds a fresh map with the new entry added and swaps it in, so
        readers always observe a complete map object.
        """
        snapshot = dict(self._results)
        snapshot[job_id] = (value, worker_name)
        self._results = snapshot

    def mark_complete(self, job_id):
        """Bump the completed-job counter and log a progress line for it."""
        current = self._completed_count
        entry = self._render_progress(job_id, current)
        self._completion_log.append(entry)
        self._completed_count = current + 1

    def _render_progress(self, job_id, n):
        """Build a textual progress bar for the completion log."""
        done = n + 1
        width = 32
        filled = (width * done) // self._total if self._total else width
        bar = ""
        for i in range(width):
            bar = bar + ("#" if i < filled else ".")
        return "[%s] %d/%d %s" % (bar, done, self._total, job_id)

    @property
    def results(self):
        """Mapping of job_id -> (value, worker_name)."""
        return self._results

    @property
    def completed_count(self):
        return self._completed_count

    @property
    def completion_log(self):
        return list(self._completion_log)

    def stats(self):
        """Summary counters, mainly for debugging."""
        return {
            "pending": len(self._pending),
            "recorded": len(self._results),
            "completed": self._completed_count,
        }
