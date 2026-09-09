import atexit
import time

from .executor import Executor, ExecutionStatus
from .mutator import Mutator
from .corpus import Corpus
from .coverage_guided import CoverageGuidedScheduler
from .crash_minimizer import CrashMinimizer
from .crash_classifier import CrashClassifier
from .crash_database import CrashDatabase
from .crash_reproducer import CrashReproducer
from .sanitizer import Sanitizer
from .distributed import DistributedWorkerPool


# =============================================================
# PROCESS-LOCAL DISTRIBUTED EXECUTOR CACHE
# =============================================================

_worker_executors = {}


def _close_worker_executors():
    """
    Close all Executor instances owned by the current worker
    process.
    """

    for executor in list(
        _worker_executors.values()
    ):
        try:
            executor.close()
        except Exception:
            pass

    _worker_executors.clear()


atexit.register(
    _close_worker_executors
)


# =============================================================
# DISTRIBUTED WORKER FUNCTION
# =============================================================

def _distributed_execute(task):
    """
    Execute one fuzzing input inside a worker process.

    Each worker process owns its own Executor instance and
    reuses it for subsequent tasks.

    task:
        (
            target,
            timeout,
            sanitizers,
            input_data
        )
    """

    target, timeout, sanitizers, input_data = task

    sanitizer_key = tuple(
        sanitizers or ()
    )

    key = (
        str(target),
        float(timeout),
        sanitizer_key
    )

    executor = _worker_executors.get(
        key
    )

    if executor is None:

        executor = Executor(
            target=target,
            timeout=timeout,
            sanitizers=sanitizer_key
        )

        _worker_executors[key] = executor

    return executor.run(
        input_data
    )


class Fuzzer:
    """
    Coverage-guided mutation fuzzer.

    The coordinator owns the global corpus, scheduler and
    coverage state.

    Distributed workers only execute inputs. Worker feedback is
    returned to the coordinator, which merges it into the shared
    corpus/scheduler before generating future mutations.
    """

    def __init__(
        self,
        executor: Executor,
        iterations: int = 1000,
        max_input_size: int = 4096,
        reproduction_attempts: int = 3,
        workers: int = 1
    ):
        # =====================================================
        # VALIDATION
        # =====================================================

        if workers < 1:
            raise ValueError(
                "workers must be greater than 0"
            )

        if iterations < 1:
            raise ValueError(
                "iterations must be at least 1"
            )

        # =====================================================
        # CORE COMPONENTS
        # =====================================================

        self.executor = executor

        self.mutator = Mutator()

        self.minimizer = CrashMinimizer(
            executor
        )

        self.crash_classifier = CrashClassifier()

        self.reproducer = CrashReproducer(
            executor,
            attempts=reproduction_attempts
        )

        self.sanitizer = Sanitizer(
            max_input_size=max_input_size
        )

        self.crash_database = CrashDatabase(
            "crashes"
        )

        # =====================================================
        # GLOBAL SCHEDULER
        # =====================================================

        self.scheduler = CoverageGuidedScheduler()

        # =====================================================
        # FUZZING CONFIGURATION
        # =====================================================

        self.iterations = iterations
        self.workers = workers

        # =====================================================
        # DISTRIBUTED EXECUTION CONFIGURATION
        # =====================================================

        self.worker_pool = None

        if self.workers > 1:

            target = getattr(
                self.executor,
                "target",
                None
            )

            timeout = getattr(
                self.executor,
                "timeout",
                1.0
            )

            sanitizers = getattr(
                self.executor,
                "sanitizers",
                ()
            )

            self.worker_target = target
            self.worker_timeout = timeout
            self.worker_sanitizers = tuple(
                sanitizers
            )

            self.worker_pool = (
                DistributedWorkerPool(
                    _distributed_execute,
                    workers=self.workers
                )
            )

        else:

            self.worker_target = None
            self.worker_timeout = None
            self.worker_sanitizers = ()

        # =====================================================
        # SHARED / GLOBAL CORPUS
        # =====================================================
        #
        # The coordinator owns this corpus.
        #
        # Every interesting result returned by any worker is
        # merged here. Future mutations are selected from this
        # same corpus and scheduler state.
        # =====================================================

        self.corpus = Corpus()

        # =====================================================
        # GLOBAL COVERAGE STATE
        # =====================================================

        self.total_coverage = set()

        self.coverage_discoveries = 0

        # =====================================================
        # EXECUTION STATISTICS
        # =====================================================

        self.executions = 0

        self.total_execution_time = 0.0

        # =====================================================
        # RESULT STATISTICS
        # =====================================================

        self.crashes = 0

        self.reproduced_crashes = 0

        self.timeouts = 0

        self.rejected_inputs = 0

        # =====================================================
        # CAMPAIGN CRASH STATISTICS
        # =====================================================

        self.campaign_unique_crashes = 0

        # =====================================================
        # CAMPAIGN TIMING
        # =====================================================

        self.campaign_start_time = None

        self.campaign_end_time = None

        self.campaign_duration = 0.0

        # =====================================================
        # BACKWARD-COMPATIBILITY REFERENCES
        # =====================================================

        self.saved_crashes = (
            self.crash_database.crash_hashes
        )

        self.crash_directory = (
            self.crash_database.directory
        )

        self.hash_file = (
            self.crash_database.hashes_file
        )

    # =========================================================
    # CLOSE
    # =========================================================

    def close(self):
        """
        Close the distributed worker pool.
        """

        if self.worker_pool is not None:

            self.worker_pool.close()

            self.worker_pool = None

    def __del__(self):
        """
        Best-effort worker cleanup.
        """

        try:
            self.close()
        except Exception:
            pass

    # =========================================================
    # EXECUTE THROUGH WORKER
    # =========================================================

    def _execute_worker(
        self,
        data: bytes
    ):
        """
        Execute one target input through the distributed pool.
        """

        if self.worker_pool is None:

            return self.executor.run(
                data
            )

        task = (
            self.worker_target,
            self.worker_timeout,
            self.worker_sanitizers,
            data
        )

        self.worker_pool.submit(
            task
        )

        _, worker_result = (
            self.worker_pool.get_result(
                timeout=max(
                    self.worker_timeout + 5.0,
                    10.0
                )
            )
        )

        if worker_result.error is not None:

            raise RuntimeError(
                "Distributed worker failed: "
                f"{worker_result.error}"
            )

        return worker_result.result

    # =========================================================
    # SHARED CORPUS SYNCHRONIZATION
    # =========================================================

    def synchronize_worker_result(
        self,
        data: bytes,
        result
    ) -> bool:
        """
        Merge feedback from a worker into the coordinator-owned
        shared corpus and scheduler.

        This is the synchronization boundary:

            Worker
              ↓
            ExecutionResult
              ↓
            Coordinator
              ↓
            Shared Corpus
              ↓
            Shared Scheduler
              ↓
            Future Mutations
        """

        coverage = getattr(
            result,
            "coverage",
            set()
        )

        if coverage is None:
            coverage = set()

        coverage = set(
            coverage
        )

        bitmap = getattr(
            result,
            "bitmap",
            None
        )

        return self.add_to_corpus(
            data,
            coverage,
            bitmap=bitmap
        )

    # =========================================================
    # CORPUS + SCHEDULER
    # =========================================================

    def add_to_corpus(
        self,
        data: bytes,
        coverage: set,
        bitmap=None
    ) -> bool:
        """
        Add an input to the global/shared corpus and scheduler
        when it discovers previously unseen line/edge or bitmap
        coverage.
        """

        coverage = set(
            coverage
        )

        # -----------------------------------------------------
        # NEW LINE / EDGE COVERAGE
        # -----------------------------------------------------

        new_coverage = (
            coverage
            -
            self.total_coverage
        )

        # -----------------------------------------------------
        # NEW BITMAP COVERAGE
        # -----------------------------------------------------

        bitmap_has_new_coverage = False

        if bitmap is not None:

            try:

                for index in range(
                    bitmap.size
                ):

                    if (
                        bitmap.bitmap[index] != 0
                        and
                        self.scheduler.total_bitmap.bitmap[index] == 0
                    ):

                        bitmap_has_new_coverage = True

                        break

            except AttributeError:

                bitmap_has_new_coverage = False

        # -----------------------------------------------------
        # NOTHING NEW
        # -----------------------------------------------------

        if (
            not new_coverage
            and
            not bitmap_has_new_coverage
        ):

            return False

        # -----------------------------------------------------
        # UPDATE GLOBAL LINE / EDGE COVERAGE
        # -----------------------------------------------------

        self.total_coverage.update(
            new_coverage
        )

        # -----------------------------------------------------
        # COUNT DISCOVERY
        # -----------------------------------------------------

        self.coverage_discoveries += 1

        # -----------------------------------------------------
        # ADD TO SHARED CORPUS
        # -----------------------------------------------------

        self.corpus.add(
            data,
            coverage
        )

        # -----------------------------------------------------
        # ADD TO SHARED SCHEDULER
        # -----------------------------------------------------

        self.scheduler.add(
            data,
            coverage,
            bitmap=bitmap
        )

        return True

    # =========================================================
    # SAVE CRASH
    # =========================================================

    def save_crash(
        self,
        crashing_input: bytes,
        classification=None
    ) -> bool:
        """
        Minimize, reproduce, classify and persist a crash.
        """

        print()
        print("=" * 60)
        print("CRASH DETECTED")
        print("=" * 60)

        print(
            f"Original input : {crashing_input!r}"
        )

        print(
            f"Original size  : "
            f"{len(crashing_input)} bytes"
        )

        # =====================================================
        # STEP 1
        # MINIMIZE
        # =====================================================

        print()
        print("[*] Minimizing crash...")

        minimized = self.minimizer.minimize(
            crashing_input
        )

        print(
            f"Minimized input: {minimized!r}"
        )

        print(
            f"Minimized size : "
            f"{len(minimized)} bytes"
        )

        # =====================================================
        # STEP 2
        # REPRODUCE
        # =====================================================

        print()
        print("[*] Reproducing crash...")

        reproduction = self.reproducer.reproduce(
            minimized
        )

        print(
            f"Attempts       : "
            f"{reproduction.attempts}"
        )

        print(
            f"Crashes        : "
            f"{reproduction.crashes}"
        )

        print(
            f"Normal         : "
            f"{reproduction.normal}"
        )

        print(
            f"Timeouts       : "
            f"{reproduction.timeouts}"
        )

        if reproduction.reproduced:

            self.reproduced_crashes += 1

            print(
                "[+] Crash reproduced successfully."
            )

        else:

            print(
                "[!] Crash could not be reproduced."
            )

        # =====================================================
        # STEP 3
        # CLASSIFICATION
        # =====================================================

        if classification is None:

            result = self.executor.run(
                minimized
            )

            classification = (
                self.crash_classifier.classify(
                    result
                )
            )

        print()

        print(
            f"Crash type     : "
            f"{classification.name}"
        )

        print(
            f"Crash message  : "
            f"{classification.message!r}"
        )

        # =====================================================
        # STEP 4
        # DATABASE SIGNATURE
        # =====================================================

        signature = (
            f"{classification.name}:"
            f"{classification.message}"
        )

        metadata = {
            "crash_type": classification.name,
            "message": classification.message,
            "original_size": len(
                crashing_input
            ),
            "minimized_size": len(
                minimized
            ),
            "reproduction_attempts": (
                reproduction.attempts
            ),
            "reproduction_crashes": (
                reproduction.crashes
            ),
            "reproduction_normal": (
                reproduction.normal
            ),
            "reproduction_timeouts": (
                reproduction.timeouts
            ),
            "reproduced": (
                reproduction.reproduced
            ),
        }

        # =====================================================
        # STEP 5
        # STORE IN CRASH DATABASE
        # =====================================================

        stored = self.crash_database.add_crash(
            signature=signature,
            input_data=minimized,
            metadata=metadata
        )

        if stored:

            self.campaign_unique_crashes += 1

            crash_hash = (
                self.crash_database.get_hash(
                    signature
                )
            )

            print()
            print("UNIQUE CRASH SAVED")

            print(
                f"Crash ID       : {crash_hash}"
            )

            print(
                f"Binary         : "
                f"{self.crash_directory / f'crash_{crash_hash}.bin'}"
            )

            print(
                f"Metadata       : "
                f"{self.crash_directory / f'crash_{crash_hash}.txt'}"
            )

        else:

            print()

            print(
                "Duplicate crash - "
                "already present in database."
            )

        print("=" * 60)

        return stored

    # =========================================================
    # PROCESS EXECUTION RESULT
    # =========================================================

    def _process_execution_result(
        self,
        data: bytes,
        iteration: int | str,
        result,
        execution_duration: float
    ) -> bool:
        """
        Process an ExecutionResult produced by either the local
        executor or a distributed worker.

        Worker coverage and bitmap feedback are synchronized into
        the coordinator-owned shared corpus.
        """

        self.executions += 1

        self.total_execution_time += (
            execution_duration
        )

        # =====================================================
        # COVERAGE
        # =====================================================

        coverage = getattr(
            result,
            "coverage",
            set()
        )

        if coverage is None:
            coverage = set()

        coverage = set(
            coverage
        )

        # =====================================================
        # BITMAP
        # =====================================================

        bitmap = getattr(
            result,
            "bitmap",
            None
        )

        # =====================================================
        # TIMEOUT
        # =====================================================

        if (
            result.status
            == ExecutionStatus.TIMEOUT
        ):

            self.timeouts += 1

            print(
                f"[{iteration}] "
                f"Input={data!r} "
                f"Status=TIMEOUT "
                f"Coverage={len(coverage)}"
            )

            return False

        # =====================================================
        # CRASH
        # =====================================================

        if (
            result.status
            == ExecutionStatus.CRASH
        ):

            self.crashes += 1

            classification = (
                self.crash_classifier.classify(
                    result
                )
            )

            print(
                f"[{iteration}] "
                f"Input={data!r} "
                f"Status=CRASH "
                f"Type={classification.name} "
                f"Message={classification.message!r} "
                f"Coverage={len(coverage)}"
            )

            # -------------------------------------------------
            # SAVE CRASH
            # -------------------------------------------------

            self.save_crash(
                data,
                classification
            )

            # -------------------------------------------------
            # SYNCHRONIZE CRASH COVERAGE
            # -------------------------------------------------

            if self.synchronize_worker_result(
                data,
                result
            ):

                print(
                    "[+] NEW COVERAGE DISCOVERED"
                )

                print(
                    f"[+] Total coverage: "
                    f"{len(self.total_coverage)}"
                )

            return True

        # =====================================================
        # NORMAL EXECUTION
        # =====================================================

        print(
            f"[{iteration}] "
            f"Input={data!r} "
            f"Status=NORMAL "
            f"Coverage={len(coverage)}"
        )

        # =====================================================
        # SYNCHRONIZE WORKER FEEDBACK
        # =====================================================

        if self.synchronize_worker_result(
            data,
            result
        ):

            print(
                "[+] NEW COVERAGE DISCOVERED"
            )

            print(
                f"[+] Total coverage: "
                f"{len(self.total_coverage)}"
            )

        return False

    # =========================================================
    # EXECUTE ONE INPUT
    # =========================================================

    def execute_input(
        self,
        data: bytes,
        iteration: int | str
    ) -> bool:
        """
        Sanitize and execute one fuzzing input.

        In workers=1 mode, execution happens through the normal
        Executor.

        In workers>1 mode, execution is dispatched to the worker
        pool and the result is synchronized into the shared
        coordinator state.
        """

        # =====================================================
        # SANITIZATION
        # =====================================================

        sanitization = (
            self.sanitizer.sanitize(
                data
            )
        )

        if not sanitization.accepted:

            self.rejected_inputs += 1

            print(
                f"[{iteration}] "
                f"Input rejected: "
                f"{sanitization.reason}"
            )

            return False

        data = sanitization.data

        # =====================================================
        # EXECUTION
        # =====================================================

        execution_start = (
            time.perf_counter()
        )

        if self.worker_pool is None:

            result = self.executor.run(
                data
            )

        else:

            result = self._execute_worker(
                data
            )

        execution_duration = (
            time.perf_counter()
            -
            execution_start
        )

        return self._process_execution_result(
            data,
            iteration,
            result,
            execution_duration
        )

    # =========================================================
    # DISTRIBUTED BATCH EXECUTION
    # =========================================================

    def execute_distributed_batch(
        self,
        inputs
    ):
        """
        Execute a batch of already-sanitized inputs through
        the distributed worker pool.

        Each worker result is matched to its original task ID.
        """

        if self.worker_pool is None:

            results = []

            for iteration, data in inputs:

                start = time.perf_counter()

                result = self.executor.run(
                    data
                )

                duration = (
                    time.perf_counter()
                    -
                    start
                )

                results.append(
                    (
                        iteration,
                        data,
                        result,
                        duration
                    )
                )

            return results

        # -----------------------------------------------------
        # SUBMIT ALL TASKS
        # -----------------------------------------------------

        submitted = {}

        for iteration, data in inputs:

            task = (
                self.worker_target,
                self.worker_timeout,
                self.worker_sanitizers,
                data
            )

            task_id = (
                self.worker_pool.submit(
                    task
                )
            )

            submitted[task_id] = (
                iteration,
                data
            )

        # -----------------------------------------------------
        # COLLECT RESULTS
        # -----------------------------------------------------

        completed = []

        while submitted:

            task_id, worker_result = (
                self.worker_pool.get_result(
                    timeout=max(
                        self.worker_timeout + 5.0,
                        10.0
                    )
                )
            )

            if worker_result.error is not None:

                raise RuntimeError(
                    "Distributed worker failed: "
                    f"{worker_result.error}"
                )

            if task_id not in submitted:

                raise RuntimeError(
                    "Distributed worker returned "
                    f"unknown task ID: {task_id}"
                )

            iteration, data = (
                submitted.pop(task_id)
            )

            result = worker_result.result

            duration = getattr(
                result,
                "duration",
                0.0
            )

            completed.append(
                (
                    iteration,
                    data,
                    result,
                    duration
                )
            )

        # -----------------------------------------------------
        # RESTORE SUBMISSION ORDER
        # -----------------------------------------------------

        completed.sort(
            key=lambda item: item[0]
        )

        return completed

    # =========================================================
    # STATISTICS
    # =========================================================

    def get_statistics(self) -> dict:
        """
        Return campaign statistics.
        """

        duration = (
            self.campaign_duration
        )

        if (
            self.campaign_start_time is not None
            and self.campaign_end_time is None
        ):

            duration = (
                time.perf_counter()
                -
                self.campaign_start_time
            )

        # -----------------------------------------------------
        # EXECUTION RATE
        # -----------------------------------------------------

        if duration > 0:

            executions_per_second = (
                self.executions
                /
                duration
            )

        else:

            executions_per_second = 0.0

        # -----------------------------------------------------
        # AVERAGE EXECUTION TIME
        # -----------------------------------------------------

        if self.executions > 0:

            average_execution_time = (
                self.total_execution_time
                /
                self.executions
            )

        else:

            average_execution_time = 0.0

        # -----------------------------------------------------
        # CRASH RATE
        # -----------------------------------------------------

        if self.executions > 0:

            crash_rate = (
                self.crashes
                /
                self.executions
            ) * 100

        else:

            crash_rate = 0.0

        # -----------------------------------------------------
        # UNIQUE CRASH RATE
        # -----------------------------------------------------

        unique_crashes = (
            self.campaign_unique_crashes
        )

        if self.executions > 0:

            unique_crash_rate = (
                unique_crashes
                /
                self.executions
            ) * 100

        else:

            unique_crash_rate = 0.0

        # -----------------------------------------------------
        # RETURN METRICS
        # -----------------------------------------------------

        return {
            "campaign_duration": duration,
            "executions": self.executions,
            "executions_per_second": (
                executions_per_second
            ),
            "average_execution_time": (
                average_execution_time
            ),
            "crashes": self.crashes,
            "crash_rate": crash_rate,
            "unique_crashes": unique_crashes,
            "unique_crash_rate": (
                unique_crash_rate
            ),
            "reproduced_crashes": (
                self.reproduced_crashes
            ),
            "timeouts": self.timeouts,
            "rejected_inputs": (
                self.rejected_inputs
            ),
            "coverage_lines": (
                len(self.total_coverage)
            ),
            "coverage_discoveries": (
                self.coverage_discoveries
            ),
            "corpus_size": (
                self.corpus.size()
            ),
            "scheduler_entries": (
                self.scheduler.size()
            ),
            "bitmap_coverage": (
                self.scheduler.bitmap_coverage_size()
            ),
            "workers": self.workers,
        }

    # =========================================================
    # PRINT STATISTICS
    # =========================================================

    def print_statistics(self):
        """
        Print a detailed campaign statistics report.
        """

        stats = self.get_statistics()

        print()
        print("=" * 60)
        print("FUZZING CAMPAIGN STATISTICS")
        print("=" * 60)

        print(
            f"Campaign duration : "
            f"{stats['campaign_duration']:.2f} seconds"
        )

        print(
            f"Executions        : "
            f"{stats['executions']}"
        )

        print(
            f"Execution rate    : "
            f"{stats['executions_per_second']:.2f} exec/sec"
        )

        print(
            f"Avg exec time     : "
            f"{stats['average_execution_time'] * 1000:.2f} ms"
        )

        print(
            f"Workers           : "
            f"{stats['workers']}"
        )

        print()

        print(
            f"Crashes found     : "
            f"{stats['crashes']}"
        )

        print(
            f"Crash rate        : "
            f"{stats['crash_rate']:.2f}%"
        )

        print(
            f"Unique crashes    : "
            f"{stats['unique_crashes']}"
        )

        print(
            f"Unique crash rate : "
            f"{stats['unique_crash_rate']:.2f}%"
        )

        print(
            f"Reproduced        : "
            f"{stats['reproduced_crashes']}"
        )

        print()

        print(
            f"Timeouts          : "
            f"{stats['timeouts']}"
        )

        print(
            f"Rejected inputs   : "
            f"{stats['rejected_inputs']}"
        )

        print()

        print(
            f"Coverage lines    : "
            f"{stats['coverage_lines']}"
        )

        print(
            f"Coverage finds    : "
            f"{stats['coverage_discoveries']}"
        )

        print(
            f"Bitmap coverage   : "
            f"{stats['bitmap_coverage']}"
        )

        print(
            f"Corpus size       : "
            f"{stats['corpus_size']}"
        )

        print(
            f"Scheduler entries : "
            f"{stats['scheduler_entries']}"
        )

        print("=" * 60)

    # =========================================================
    # MAIN FUZZING LOOP
    # =========================================================

    def run(
        self,
        seed: bytes
    ):
        """
        Run the complete coverage-guided fuzzing campaign.
        """

        # =====================================================
        # START CAMPAIGN TIMER
        # =====================================================

        self.campaign_start_time = (
            time.perf_counter()
        )

        self.campaign_end_time = None

        print()
        print("=" * 60)
        print("STARTING COVERAGE-GUIDED FUZZER")
        print("=" * 60)

        print(
            f"Seed              : {seed!r}"
        )

        print(
            f"Iterations        : {self.iterations}"
        )

        print(
            f"Max input size    : "
            f"{self.sanitizer.max_input_size}"
        )

        print(
            f"Reproduction runs : "
            f"{self.reproducer.attempts}"
        )

        print(
            f"Workers           : "
            f"{self.workers}"
        )

        print(
            f"Previous crashes  : "
            f"{self.crash_database.count()}"
        )

        print("=" * 60)

        try:

            # =================================================
            # STEP 1
            # EXECUTE INITIAL SEED
            # =================================================

            print()
            print(
                "[*] Executing initial seed..."
            )

            self.execute_input(
                seed,
                "SEED"
            )

            # =================================================
            # STEP 2
            # FALLBACK CORPUS
            # =================================================

            if self.corpus.size() == 0:

                self.corpus.add(
                    seed,
                    set()
                )

            # =================================================
            # STEP 3
            # MUTATION LOOP
            # =================================================

            if self.workers == 1:

                for iteration in range(
                    1,
                    self.iterations + 1
                ):

                    # -----------------------------------------
                    # SELECT FROM SHARED CORPUS / SCHEDULER
                    # -----------------------------------------

                    if not self.scheduler.is_empty():

                        current_input = (
                            self.scheduler.select()
                        )

                    else:

                        try:

                            current_input = (
                                self.corpus.random()
                            )

                        except IndexError:

                            current_input = seed

                    # -----------------------------------------
                    # MUTATE
                    # -----------------------------------------

                    mutated_input = (
                        self.mutator.mutate(
                            current_input
                        )
                    )

                    # -----------------------------------------
                    # EXECUTE
                    # -----------------------------------------

                    self.execute_input(
                        mutated_input,
                        iteration
                    )

            else:

                # =================================================
                # DISTRIBUTED MODE
                # =================================================
                #
                # The coordinator maintains one shared corpus.
                # Workers execute inputs in parallel.
                #
                # Worker result:
                #
                #     worker
                #       ↓
                #     result
                #       ↓
                #     shared corpus
                #       ↓
                #     shared scheduler
                #       ↓
                #     next mutation
                #
                # At most `self.workers` executions are in flight.
                # =================================================

                pending = []

                next_iteration = 1

                # -------------------------------------------------
                # PRIME WORKERS
                # -------------------------------------------------

                while (
                    next_iteration <= self.iterations
                    and len(pending) < self.workers
                ):

                    # ---------------------------------------------
                    # SELECT FROM SHARED STATE
                    # ---------------------------------------------

                    if not self.scheduler.is_empty():

                        current_input = (
                            self.scheduler.select()
                        )

                    else:

                        try:

                            current_input = (
                                self.corpus.random()
                            )

                        except IndexError:

                            current_input = seed

                    # ---------------------------------------------
                    # MUTATE
                    # ---------------------------------------------

                    mutated_input = (
                        self.mutator.mutate(
                            current_input
                        )
                    )

                    # ---------------------------------------------
                    # SANITIZE
                    # ---------------------------------------------

                    sanitization = (
                        self.sanitizer.sanitize(
                            mutated_input
                        )
                    )

                    if not sanitization.accepted:

                        self.rejected_inputs += 1

                        print(
                            f"[{next_iteration}] "
                            f"Input rejected: "
                            f"{sanitization.reason}"
                        )

                        next_iteration += 1

                        continue

                    # ---------------------------------------------
                    # SUBMIT TO WORKER
                    # ---------------------------------------------

                    task = (
                        self.worker_target,
                        self.worker_timeout,
                        self.worker_sanitizers,
                        sanitization.data
                    )

                    task_id = (
                        self.worker_pool.submit(
                            task
                        )
                    )

                    pending.append(
                        {
                            "task_id": task_id,
                            "iteration": next_iteration,
                            "data": sanitization.data,
                        }
                    )

                    next_iteration += 1

                # -------------------------------------------------
                # DRAIN + REFILL
                # -------------------------------------------------

                while pending:

                    # ---------------------------------------------
                    # WAIT FOR ANY COMPLETED WORKER
                    # ---------------------------------------------

                    task_id, worker_result = (
                        self.worker_pool.get_result(
                            timeout=max(
                                self.worker_timeout + 5.0,
                                10.0
                            )
                        )
                    )

                    # ---------------------------------------------
                    # FIND TASK
                    # ---------------------------------------------

                    task_info = None

                    for candidate in pending:

                        if candidate["task_id"] == task_id:

                            task_info = candidate

                            break

                    if task_info is None:

                        raise RuntimeError(
                            "Distributed worker returned "
                            f"unknown task ID: {task_id}"
                        )

                    pending.remove(
                        task_info
                    )

                    # ---------------------------------------------
                    # WORKER ERROR
                    # ---------------------------------------------

                    if worker_result.error is not None:

                        raise RuntimeError(
                            "Distributed worker failed: "
                            f"{worker_result.error}"
                        )

                    # ---------------------------------------------
                    # GET RESULT
                    # ---------------------------------------------

                    result = worker_result.result

                    execution_duration = getattr(
                        result,
                        "duration",
                        0.0
                    )

                    # ---------------------------------------------
                    # SYNCHRONIZE RESULT
                    #
                    # This immediately merges coverage and bitmap
                    # information into the shared coordinator state.
                    # ---------------------------------------------

                    self._process_execution_result(
                        task_info["data"],
                        task_info["iteration"],
                        result,
                        execution_duration
                    )

                    # ---------------------------------------------
                    # REFILL WORKER
                    # ---------------------------------------------

                    if (
                        next_iteration
                        <= self.iterations
                    ):

                        # -----------------------------------------
                        # SELECT FROM UPDATED SHARED STATE
                        # -----------------------------------------

                        if not self.scheduler.is_empty():

                            current_input = (
                                self.scheduler.select()
                            )

                        else:

                            try:

                                current_input = (
                                    self.corpus.random()
                                )

                            except IndexError:

                                current_input = seed

                        # -----------------------------------------
                        # MUTATE
                        # -----------------------------------------

                        mutated_input = (
                            self.mutator.mutate(
                                current_input
                            )
                        )

                        # -----------------------------------------
                        # SANITIZE
                        # -----------------------------------------

                        sanitization = (
                            self.sanitizer.sanitize(
                                mutated_input
                            )
                        )

                        if not sanitization.accepted:

                            self.rejected_inputs += 1

                            print(
                                f"[{next_iteration}] "
                                f"Input rejected: "
                                f"{sanitization.reason}"
                            )

                            next_iteration += 1

                            continue

                        # -----------------------------------------
                        # SUBMIT
                        # -----------------------------------------

                        task = (
                            self.worker_target,
                            self.worker_timeout,
                            self.worker_sanitizers,
                            sanitization.data
                        )

                        task_id = (
                            self.worker_pool.submit(
                                task
                            )
                        )

                        pending.append(
                            {
                                "task_id": task_id,
                                "iteration": next_iteration,
                                "data": sanitization.data,
                            }
                        )

                        next_iteration += 1

        finally:

            # =====================================================
            # STOP CAMPAIGN TIMER
            # =====================================================

            self.campaign_end_time = (
                time.perf_counter()
            )

            self.campaign_duration = (
                self.campaign_end_time
                -
                self.campaign_start_time
            )

            self.print_statistics()

            # -----------------------------------------------------
            # WORKER CLEANUP
            # -----------------------------------------------------

            self.close()

        # =====================================================
        # RETURN STATISTICS
        # =====================================================

        return self.get_statistics()


# =============================================================
# ENTRY POINT
# =============================================================

if __name__ == "__main__":

    from .cli import main

    main()