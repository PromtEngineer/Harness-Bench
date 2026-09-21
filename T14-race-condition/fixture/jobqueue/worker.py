"""Worker threads and the WorkerPool that drives them."""
import threading


class Worker(threading.Thread):
    """Pulls jobs off the shared queue until it is drained."""

    def __init__(self, queue, barrier=None, name=None):
        super().__init__(name=name, daemon=True)
        self._queue = queue
        self._barrier = barrier

    def run(self):
        if self._barrier is not None:
            # All workers begin consuming at the same instant.
            self._barrier.wait()
        while True:
            job = self._queue.get_next_job()
            if job is None:
                return
            value = job.run()
            self._queue.record_result(job.job_id, value, self.name)
            self._queue.mark_complete(job.job_id)


class WorkerPool:
    """Runs a fixed number of Worker threads over one JobQueue."""

    def __init__(self, queue, num_workers, synchronized_start=True):
        if num_workers < 1:
            raise ValueError("num_workers must be >= 1")
        self._queue = queue
        self._num_workers = num_workers
        self._synchronized_start = synchronized_start

    def run(self):
        """Start all workers, wait for the queue to drain, and return stats."""
        barrier = None
        if self._synchronized_start:
            barrier = threading.Barrier(self._num_workers)
        workers = [
            Worker(self._queue, barrier=barrier, name="worker-%d" % i)
            for i in range(self._num_workers)
        ]
        for w in workers:
            w.start()
        for w in workers:
            w.join()
        return self._queue.stats()
