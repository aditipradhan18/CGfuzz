from __future__ import annotations

import multiprocessing
import queue

from dataclasses import dataclass
from typing import Any, Callable


# =============================================================
# WORKER RESULT
# =============================================================

@dataclass
class WorkerResult:
    """
    Result returned by one distributed worker.
    """

    worker_id: int

    result: Any = None

    error: str | None = None


# =============================================================
# WORKER PROCESS
# =============================================================

def _worker_main(
    worker_id: int,
    task_queue,
    result_queue,
    function: Callable[[Any], Any]
):
    """
    Worker process entry point.

    Workers receive tasks, execute them independently and return
    the result to the coordinator.
    """

    while True:

        task = task_queue.get()

        # -----------------------------------------------------
        # STOP SIGNAL
        # -----------------------------------------------------

        if task is None:
            break

        task_id, argument = task

        # -----------------------------------------------------
        # EXECUTE TASK
        # -----------------------------------------------------

        try:

            result = function(
                argument
            )

            result_queue.put(
                (
                    task_id,
                    WorkerResult(
                        worker_id=worker_id,
                        result=result
                    )
                )
            )

        except Exception as exc:

            result_queue.put(
                (
                    task_id,
                    WorkerResult(
                        worker_id=worker_id,
                        error=(
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        )
                    )
                )
            )


# =============================================================
# DISTRIBUTED WORKER POOL
# =============================================================

class DistributedWorkerPool:
    """
    Multiprocess worker pool for distributed fuzzing.

    The pool provides:

        - multiple worker processes
        - task submission
        - result collection
        - worker identification
        - graceful shutdown

    The coordinator remains responsible for maintaining global
    corpus, coverage and scheduler state.
    """

    def __init__(
        self,
        function: Callable[[Any], Any],
        workers: int = 2
    ):

        # =====================================================
        # VALIDATION
        # =====================================================

        if not callable(function):

            raise TypeError(
                "function must be callable"
            )

        if workers < 1:

            raise ValueError(
                "workers must be greater than 0"
            )

        # =====================================================
        # CONFIGURATION
        # =====================================================

        self.function = function

        self.workers = workers

        # =====================================================
        # QUEUES
        # =====================================================

        self.task_queue = (
            multiprocessing.Queue()
        )

        self.result_queue = (
            multiprocessing.Queue()
        )

        # =====================================================
        # PROCESS STATE
        # =====================================================

        self.processes = []

        self._next_task_id = 0

        self._closed = False

        # =====================================================
        # START WORKERS
        # =====================================================

        for worker_id in range(
            workers
        ):

            process = multiprocessing.Process(
                target=_worker_main,
                args=(
                    worker_id,
                    self.task_queue,
                    self.result_queue,
                    function,
                ),
            )

            process.daemon = True

            process.start()

            self.processes.append(
                process
            )

    # =========================================================
    # SUBMIT
    # =========================================================

    def submit(
        self,
        argument: Any
    ) -> int:
        """
        Submit one task.

        Returns:
            unique task ID
        """

        if self._closed:

            raise RuntimeError(
                "Worker pool is closed"
            )

        task_id = (
            self._next_task_id
        )

        self._next_task_id += 1

        self.task_queue.put(
            (
                task_id,
                argument
            )
        )

        return task_id

    # =========================================================
    # GET RESULT
    # =========================================================

    def get_result(
        self,
        timeout: float | None = None
    ):
        """
        Wait for one worker result.

        Returns:

            (task_id, WorkerResult)
        """

        try:

            return self.result_queue.get(
                timeout=timeout
            )

        except queue.Empty:

            raise TimeoutError(
                "Timed out waiting for worker result"
            )

    # =========================================================
    # MAP
    # =========================================================

    def map(
        self,
        arguments,
        timeout: float | None = None
    ):
        """
        Execute a collection of tasks and return results in
        submission order.
        """

        task_ids = []

        # -----------------------------------------------------
        # SUBMIT
        # -----------------------------------------------------

        for argument in arguments:

            task_ids.append(
                self.submit(
                    argument
                )
            )

        # -----------------------------------------------------
        # COLLECT
        # -----------------------------------------------------

        results = {}

        while len(results) < len(task_ids):

            task_id, worker_result = (
                self.get_result(
                    timeout=timeout
                )
            )

            results[task_id] = (
                worker_result
            )

        # -----------------------------------------------------
        # RESTORE ORDER
        # -----------------------------------------------------

        return [
            results[task_id]
            for task_id in task_ids
        ]

    # =========================================================
    # ALIVE WORKERS
    # =========================================================

    @property
    def alive_workers(
        self
    ) -> int:
        """
        Return the number of currently alive workers.
        """

        return sum(
            process.is_alive()
            for process in self.processes
        )

    # =========================================================
    # WORKER IDS
    # =========================================================

    @property
    def worker_ids(
        self
    ) -> list[int]:

        """
        Return worker IDs represented by the pool.
        """

        return list(
            range(
                len(self.processes)
            )
        )

    # =========================================================
    # CLOSE
    # =========================================================

    def close(
        self
    ):
        """
        Stop all worker processes and release resources.
        """

        if self._closed:
            return

        self._closed = True

        # -----------------------------------------------------
        # STOP SIGNALS
        # -----------------------------------------------------

        for _ in self.processes:

            self.task_queue.put(
                None
            )

        # -----------------------------------------------------
        # WAIT
        # -----------------------------------------------------

        for process in self.processes:

            process.join(
                timeout=2.0
            )

        # -----------------------------------------------------
        # FORCE TERMINATION
        # -----------------------------------------------------

        for process in self.processes:

            if process.is_alive():

                process.terminate()

                process.join(
                    timeout=1.0
                )

    # =========================================================
    # CONTEXT MANAGER
    # =========================================================

    def __enter__(
        self
    ):

        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback
    ):

        self.close()

    # =========================================================
    # DESTRUCTOR
    # =========================================================

    def __del__(
        self
    ):

        try:

            self.close()

        except Exception:

            pass