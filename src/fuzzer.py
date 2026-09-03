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


class Fuzzer:
    """
    Coverage-guided mutation fuzzer.

    Pipeline:

        Seed
          ↓
        Sanitizer
          ↓
        Executor
          ↓
        Coverage / Crash
          ↓
        Crash Classification
          ↓
        Crash Minimization
          ↓
        Crash Reproduction
          ↓
        Crash Database
          ↓
        Coverage-Guided Scheduler
          ↓
        Corpus
          ↓
        Mutation
          ↓
        Next Execution
    """

    def __init__(
        self,
        executor: Executor,
        iterations: int = 1000,
        max_input_size: int = 4096,
        reproduction_attempts: int = 3
    ):
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
        # COVERAGE-GUIDED SCHEDULER
        # =====================================================

        self.scheduler = CoverageGuidedScheduler()

        # =====================================================
        # FUZZING CONFIGURATION
        # =====================================================

        self.iterations = iterations

        # =====================================================
        # CORPUS
        # =====================================================

        self.corpus = Corpus()

        # =====================================================
        # COVERAGE STATE
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
    # CORPUS + SCHEDULER
    # =========================================================

    def add_to_corpus(
        self,
        data: bytes,
        coverage: set
    ) -> bool:
        """
        Add an input to the corpus and coverage-guided
        scheduler when it discovers previously unseen coverage.
        """

        coverage = set(coverage)

        new_coverage = (
            coverage -
            self.total_coverage
        )

        if not new_coverage:
            return False

        # -----------------------------------------------------
        # GLOBAL COVERAGE
        # -----------------------------------------------------

        self.total_coverage.update(
            new_coverage
        )

        # -----------------------------------------------------
        # COVERAGE DISCOVERY COUNTER
        # -----------------------------------------------------

        self.coverage_discoveries += 1

        # -----------------------------------------------------
        # TRADITIONAL CORPUS
        # -----------------------------------------------------

        self.corpus.add(
            data,
            coverage
        )

        # -----------------------------------------------------
        # COVERAGE-GUIDED SCHEDULER
        # -----------------------------------------------------

        self.scheduler.add(
            data,
            coverage
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
            "original_size": len(crashing_input),
            "minimized_size": len(minimized),
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
    # EXECUTE ONE INPUT
    # =========================================================

    def execute_input(
        self,
        data: bytes,
        iteration: int | str
    ) -> bool:
        """
        Sanitize and execute one fuzzing input.

        Returns True if the target crashes.
        """

        # =====================================================
        # SANITIZATION
        # =====================================================

        sanitization = (
            self.sanitizer.sanitize(data)
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

        execution_start = time.perf_counter()

        self.executions += 1

        result = self.executor.run(
            data
        )

        execution_duration = (
            time.perf_counter()
            - execution_start
        )

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

        coverage = set(coverage)

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
            # CRASHING INPUTS CAN STILL ADD COVERAGE
            # -------------------------------------------------

            if self.add_to_corpus(
                data,
                coverage
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
        # NEW COVERAGE
        # =====================================================

        if self.add_to_corpus(
            data,
            coverage
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
    # STATISTICS
    # =========================================================

    def get_statistics(self) -> dict:
        """
        Return campaign statistics.

        The execution-related metrics are based on fuzzing
        executions performed through execute_input().
        """

        duration = self.campaign_duration

        if (
            self.campaign_start_time is not None
            and self.campaign_end_time is None
        ):
            duration = (
                time.perf_counter()
                - self.campaign_start_time
            )

        # -----------------------------------------------------
        # EXECUTION RATE
        # -----------------------------------------------------

        if duration > 0:

            executions_per_second = (
                self.executions / duration
            )

        else:

            executions_per_second = 0.0

        # -----------------------------------------------------
        # AVERAGE EXECUTION TIME
        # -----------------------------------------------------

        if self.executions > 0:

            average_execution_time = (
                self.total_execution_time
                / self.executions
            )

        else:

            average_execution_time = 0.0

        # -----------------------------------------------------
        # CRASH RATE
        # -----------------------------------------------------

        if self.executions > 0:

            crash_rate = (
                self.crashes
                / self.executions
            ) * 100

        else:

            crash_rate = 0.0

        # -----------------------------------------------------
        # UNIQUE CRASH COUNT
        # -----------------------------------------------------

        unique_crashes = (
            self.crash_database.count()
        )

        if self.executions > 0:

            unique_crash_rate = (
                unique_crashes
                / self.executions
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
            "unique_crash_rate": unique_crash_rate,
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
            f"Previous crashes  : "
            f"{self.crash_database.count()}"
        )

        print("=" * 60)

        # =====================================================
        # STEP 1
        # EXECUTE INITIAL SEED
        # =====================================================

        print()
        print("[*] Executing initial seed...")

        self.execute_input(
            seed,
            "SEED"
        )

        # =====================================================
        # STEP 2
        # FALLBACK CORPUS
        # =====================================================

        if self.corpus.size() == 0:

            self.corpus.add(
                seed,
                set()
            )

        # =====================================================
        # STEP 3
        # MUTATION LOOP
        # =====================================================

        for iteration in range(
            1,
            self.iterations + 1
        ):

            # -------------------------------------------------
            # COVERAGE-GUIDED INPUT SELECTION
            # -------------------------------------------------

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

            # -------------------------------------------------
            # MUTATE
            # -------------------------------------------------

            mutated_input = (
                self.mutator.mutate(
                    current_input
                )
            )

            # -------------------------------------------------
            # EXECUTE
            # -------------------------------------------------

            self.execute_input(
                mutated_input,
                iteration
            )

        # =====================================================
        # STOP CAMPAIGN TIMER
        # =====================================================

        self.campaign_end_time = (
            time.perf_counter()
        )

        self.campaign_duration = (
            self.campaign_end_time
            - self.campaign_start_time
        )

        # =====================================================
        # FINAL STATISTICS
        # =====================================================

        self.print_statistics()


# =============================================================
# ENTRY POINT
# =============================================================

if __name__ == "__main__":

    from .cli import main

    main()